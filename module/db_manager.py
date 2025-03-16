import itertools
import logging
import multiprocessing
import os
import shutil
import tempfile
from abc import abstractmethod
from pathlib import Path
import dask
import pandas as pd
from dask.dataframe import dd
from tqdm import tqdm
from tqdm.dask import TqdmCallback
from .graph import DistanceBasedGraph
from module.graph_similarity_functions import GraphSimilarityContext
from util.batch import batch as batch
from util.statistics import get_stats


class ParquetManager:
    def __init__(self, path_file: Path):
        try:
            data = dd.read_parquet(
                path=path_file,
                ignore_metadata_file=True
            )

            if data.compute().empty:
                self._path_file, self._empty = path_file, True
            else:
                self._path_file, self._empty = path_file, False
        except Exception:
            self._path_file, self._empty = path_file, True

    @property
    def empty(self):
        return self._empty

    @property
    def path_file(self):
        return self._path_file

    def read(self, columns=None, filters=None):
        if self._empty:
            return None

        data = dd.read_parquet(
            path=self._path_file,
            columns=columns,
            filters=filters,
            ignore_metadata_file=True
        )

        return data

    def write(self, df: dd.DataFrame, overwrite=False):
        dd.to_parquet(
            df=df,
            path=self._path_file,
            overwrite=overwrite,
            write_metadata_file=False
        )

        self._empty = False

    def remove(self):
        try:
            shutil.rmtree(self._path_file, ignore_errors=True)
            self._empty = True
        except Exception as e:
            logging.error(f"Error removing parquet data at {self._path_file}: {e}")

    def add(self, data: dd.DataFrame, partition_size=None, persist=False):
        if not self._empty:
            existing_data = self.read()
            data = dd.concat([existing_data, data])

        if partition_size:
            data = data_repartition(data, partition_size=partition_size)

        if persist:
            data = data.persist()

        self.write(data, overwrite=True)

        self._empty = False


# Repository Pattern
class BaseRepository:
    def __init__(self, manager: ParquetManager):
        self._manager = manager

    @property
    def manager(self):
        return self._manager

    def read(self, columns=None, filters=None, partition_size=None, persist=False):
        data = self._manager.read(columns=columns, filters=filters)

        if partition_size:
            data = data_repartition(data, partition_size=partition_size)

        if persist:
            data = data.persist()

        return data

    def remove(self):
        self._manager.remove()

    def add(self):
        pass


class SequenceRepository(BaseRepository):
    def __init__(self, path_file: Path):
        manager = ParquetManager(path_file)
        super().__init__(manager)

        if not self._manager.empty:
            self._next_sequence_id = int(
                self._manager.read(
                    columns=['sequence_id']
                ).max().compute().iloc[0] + 1)
        else:
            self._next_sequence_id = 1

    def add(self, df):
        df = dd.from_pandas(df)

        df["sequence_id"] = range(
            self._next_sequence_id,
            self._next_sequence_id + len(df)
        )

        self._manager.add(
            data=df[["sequence_id", "sequence", "length", "esm2_perplexity"]],
            partition_size=200,
            persist=True
        )

        return df.compute()

    def get_all(self, partition_size=None, persist=False, attr=None):
        return self.read(columns=attr, partition_size=partition_size, persist=persist)

    def get_by_ids(self, sequence_ids, attr=None):
        return self.read(
            columns=attr,
            filters=[
                ('sequence_id', 'in', sequence_ids)
            ]
        )

    def get_by_value(self, sequence_values, attr=None):
        return self.read(
            columns=attr,
            filters=[
                ('sequence', 'in', sequence_values)
            ]
        )

    def get_missing_sequences(self, sequences_to_find) -> dd.DataFrame:
        sequences_to_find = dd.from_pandas(sequences_to_find)
        sequences_to_find = data_repartition(sequences_to_find, partition_size=100)
        sequences_to_find = sequences_to_find.persist()

        if not self._manager.empty:
            existing_sequences = self.read(columns=["sequence"], partition_size=100, persist=True)

            missing_sequences = sequences_to_find[~sequences_to_find['sequence'].isin(existing_sequences['sequence'])]

            return missing_sequences.compute()

        return sequences_to_find.compute()

    def get_sequence_lengths(self) -> dd.DataFrame:
        if self._manager.empty:
            return None

        data = self.read(columns=["sequence"], partition_size=100, persist=True)
        data["length"] = data["sequence"].str.len()
        return data.compute()

    def get_sequence_perplexities(self) -> dd.DataFrame:
        if self._manager.empty:
            return None

        data = self.read(columns=["sequence", "esm2_perplexity"], partition_size=100)
        data["length"] = data["sequence"].str.len()
        return data.compute()


class DistanceRepository(BaseRepository):
    def __init__(self, path_file: Path):
        manager = ParquetManager(path_file)
        super().__init__(manager)

    def add(self, df):
        df = dd.from_pandas(df)

        self._manager.add(
            data=df,
            partition_size=200,
            persist=True
        )

    def get_by_ids_function_interval(self, sequence_ids, distance_function, interval, attr=None):
        return self.read(
            columns=attr,
            filters=[
                (distance_function, '>', interval[0]),
                (distance_function, '<=', interval[1]),
                ('sequence_id', 'in', sequence_ids)
            ]
        )

    def get_by_ids(self, sequence_ids, attr=None):
        return self.read(
            columns=attr,
            filters=[
                ('sequence_id', 'in', sequence_ids)
            ]
        )

    def get_stats(self, distance_functions):
        if not self._manager.empty:
            statistics = {}
            for distance_function in tqdm(distance_functions,
                                          desc="Computing inter-amino acid distance statistics"):
                values = self.read(
                    columns=[distance_function],
                    partition_size=100
                ).compute()

                statistics[distance_function] = get_stats(values.iloc[:, 0])

            statistics = pd.DataFrame(statistics).T
            statistics.index.name = "distance_function"
            statistics.reset_index(inplace=True)
            statistics["count"] = statistics["count"].astype(int)

            return statistics

        return None

    def get_max_distance(self, distance_function):
        if self._manager.empty:
            return None

        df = self.read().compute()

        max_value = df[distance_function].max()

        return df[df[distance_function] == max_value]

    def get_all(self, attr):
        return self.read(
            columns=attr,
        )


# Unit of Work
class DBManager:
    def __init__(
            self,
            sequence_repository: SequenceRepository,
            distance_repository: DistanceRepository,
            **kwargs
    ):
        self._sequence_repository = sequence_repository
        self._distance_repository = distance_repository
        self._kwargs = kwargs

    @property
    def sequence_repository(self):
        return self._sequence_repository

    @property
    def distance_repository(self):
        return self._distance_repository

    @property
    def kwargs(self):
        return self._kwargs

    @sequence_repository.setter
    def sequence_repository(self, value):
        self._sequence_repository = value

    @distance_repository.setter
    def distance_repository(self, value):
        self._distance_repository = value


class DBService:
    def __init__(self, **kwargs):
        db_path = _get_db_path()

        self._db_manager = DBManager(
            sequence_repository=SequenceRepository(db_path.joinpath("sequences")),
            distance_repository=DistanceRepository(db_path.joinpath("distances")),
            **kwargs
        )

    @abstractmethod
    def prepare_data(self, sequences_to_process):
        pass


class IngestionService(DBService):
    def __init__(self, **kwargs):
        super(IngestionService, self).__init__(**kwargs)

    def prepare_data(self, sequences_to_process):
        missing_sequences = self._db_manager.sequence_repository.get_missing_sequences(
            sequences_to_find=sequences_to_process
        )

        if missing_sequences.empty:
            logging.getLogger('logger').info(f"All sequences have already been processed.")
            quit()

        return missing_sequences

    def add_data_to_db(self, sequences, distances):
        data_new = self._db_manager.sequence_repository.add(df=sequences)

        data_new = data_new[["sequence_id", "sequence"]]

        # Merge DataFrames based on the 'sequence' column
        merged_data = distances.merge(data_new, on="sequence", how="inner")

        # Remove the 'sequence' column after merging
        merged_data.drop(columns=['sequence'], inplace=True)

        self._db_manager.distance_repository.add(df=merged_data)


class AnalysisService(DBService):
    def __init__(self, **kwargs):
        super(AnalysisService, self).__init__(**kwargs)

    def prepare_data(self, sequences_to_process):
        sequence_values = self._validate(sequences_to_process)

        temp_dir = Path(tempfile.mkdtemp()).resolve()
        sequence_ids = self._init_temp_sequence_repository(sequence_values, temp_dir)
        self._init_temp_distance_repository(sequence_ids, temp_dir)

        return sequences_to_process

    def _validate(self, sequences_to_process):
        sequence_values = sequences_to_process['sequence'].tolist()

        existing_sequences = self._db_manager.sequence_repository.get_by_value(
            sequence_values
        )

        if len(sequences_to_process) != len(existing_sequences):
            logging.getLogger('logger').critical(
                f"There are sequences for which data ingestion has not been performed.")
            raise Exception("There are sequences for which data ingestion has not been performed.")

        return existing_sequences

    def _init_temp_sequence_repository(self, filtered_sequences, path_file):
        self._db_manager.sequence_repository = SequenceRepository(path_file.joinpath("sequence"))

        self._db_manager.sequence_repository.manager.write(
            df=filtered_sequences,
            overwrite=True
        )

        return filtered_sequences['sequence_id'].compute().tolist()

    def _init_temp_distance_repository(self, sequence_ids, path_file):
        filtered_distances = self._db_manager.distance_repository.get_by_ids(
            sequence_ids=sequence_ids
        )

        self._db_manager.distance_repository = DistanceRepository(path_file.joinpath("distance"))
        self._db_manager.distance_repository.manager.write(
            df=filtered_distances,
            overwrite=True
        )


class SequenceAnalysisService(AnalysisService):
    def __init__(self, **kwargs):
        super(SequenceAnalysisService, self).__init__(**kwargs)

    def get_sequence_lengths(self):
        return self._db_manager.sequence_repository.get_sequence_lengths()

    def get_sequence_perplexities(self):
        return self._db_manager.sequence_repository.get_sequence_perplexities()

    def get_distance_stats(self, distance_functions):
        return self._db_manager.distance_repository.get_stats(distance_functions)


class GraphAnalysisService(AnalysisService):
    def __init__(self, **kwargs):
        super(GraphAnalysisService, self).__init__(**kwargs)

    def compute_graph_metrics(self):
        sequences = self._db_manager.sequence_repository.get_all(
            partition_size=100,
            persist=True,
            attr=["sequence_id", "sequence"]
        ).compute()

        sequence_batches = list(batch(sequences, batch_size=self._db_manager.kwargs.get('batch_size')))
        sequence_distance_pairs = itertools.product(sequence_batches, self._db_manager.kwargs.get('distance_intervals'))

        total_tasks = len(sequences) * len(self._db_manager.kwargs.get('distance_intervals'))

        with tqdm(total=total_tasks, desc="Creating graph metrics computation tasks") as progress:
            tasks = []
            for sequence_batch, distance_interval in sequence_distance_pairs:
                distance_function = distance_interval['distance_function']
                interval = distance_interval['interval']

                distances = self._db_manager.distance_repository.get_by_ids_function_interval(
                    sequence_ids=sequence_batch['sequence_id'].tolist(),
                    distance_function=distance_function,
                    interval=interval,
                    attr=['sequence_id', 'aa_src', 'aa_dst']
                )

                task = distances.groupby('sequence_id', group_keys=True).apply(
                    lambda distances_group, df=distance_function, iv=interval, sb=sequence_batch:
                    DistanceBasedGraph(
                        sequence_value=sb.loc[sb['sequence_id'] == distances_group.name, 'sequence'].iloc[0],
                        distances=distances_group,
                        distance_function=df,
                        interval=iv
                    ).compute_metrics(),
                    meta=('data', 'object')
                )

                tasks.append(task)
                progress.update(len(sequence_batch))

        # Executing task
        with dask.config.set(scheduler='processes', num_workers=multiprocessing.cpu_count()):
            with TqdmCallback(desc="Executing non-empty graph metrics computation tasks"):
                computed_metrics = dask.compute(*tasks)

        # not empty graph metrics
        computed_metrics = list(itertools.chain(*computed_metrics))
        not_empty_graph_metrics = pd.DataFrame(computed_metrics)

        # computed empty graph metrics
        empty_graph_metrics = pd.DataFrame()
        if len(not_empty_graph_metrics) != total_tasks:
            empty_graph_metrics = self._compute_empty_graph_metrics(sequences, computed_metrics)

        return pd.concat([not_empty_graph_metrics, empty_graph_metrics])

    def compute_graph_similarity(self):
        sequences = self._db_manager.sequence_repository.get_all(
            partition_size=100,
            persist=True,
            attr=["sequence_id", "sequence"]
        ).compute()

        sequence_batches = list(batch(sequences, batch_size=self._db_manager.kwargs.get('batch_size')))

        total_tasks = len(sequences)

        with tqdm(total=total_tasks, desc="Creating graph similarity computation tasks") as progress:
            tasks = []
            for sequence_batch in sequence_batches:
                distances = self._db_manager.distance_repository.get_by_ids(
                    sequence_ids=sequence_batch['sequence_id'].tolist(),
                )

                task = distances.groupby('sequence_id', group_keys=True).apply(
                    lambda distances_group, sb=sequence_batch:
                    self._compute_similarity(
                        distances_group,
                        sb.loc[sb['sequence_id'] == distances_group.name, 'sequence'].iloc[0]
                    ),
                    meta=('data', 'object')
                )

                tasks.append(task)
                progress.update(len(sequence_batch))

        with dask.config.set(scheduler='processes', num_workers=multiprocessing.cpu_count()):
            with TqdmCallback(desc="Executing graph similarity computation tasks"):
                results = dask.compute(*tasks)

        results = list(itertools.chain(*results))
        results = [item for sublist in results for item in sublist]
        return pd.DataFrame(results)

    def compare_with_random_graphs(self):
        sequences = self._db_manager.sequence_repository.get_all(
            partition_size=100,
            persist=True,
            attr=["sequence_id", "sequence"]
        ).compute()

        sequence_batches = list(batch(sequences, batch_size=self._db_manager.kwargs.get('batch_size')))
        sequence_distance_pairs = itertools.product(sequence_batches, self._db_manager.kwargs.get('distance_intervals'))

        total_tasks = len(sequences) * len(self._db_manager.kwargs.get('distance_intervals'))

        with tqdm(total=total_tasks, desc="Creating comparison with random graph tasks") as progress:
            tasks = []
            for sequence_batch, distance_interval in sequence_distance_pairs:
                distance_function = distance_interval['distance_function']
                interval = distance_interval['interval']

                distances = self._db_manager.distance_repository.get_by_ids_function_interval(
                    sequence_ids=sequence_batch['sequence_id'].tolist(),
                    distance_function=distance_function,
                    interval=interval,
                    attr=['sequence_id', 'aa_src', 'aa_dst']
                )

                task = distances.groupby('sequence_id', group_keys=True).apply(
                    lambda distances_group, df=distance_function, iv=interval, sb=sequence_batch:
                    self._compare(
                        sequence_value=sb.loc[sb['sequence_id'] == distances_group.name, 'sequence'].iloc[0],
                        distances=distances_group,
                        distance_function=df,
                        interval=iv
                    ),
                    meta=('data', 'object')
                )

                tasks.append(task)
                progress.update(len(sequence_batch))

        with dask.config.set(scheduler='processes', num_workers=multiprocessing.cpu_count()):
            with TqdmCallback(desc="Executing comparison with random graph tasks"):
                results = dask.compute(*tasks)

        results = list(itertools.chain(*results))
        results = [item for sublist in results for item in sublist]
        return pd.DataFrame(results)

    def _compute_empty_graph_metrics(self, sequences, computed_metrics):
        all_combinations = set(
            (sequence, interval["distance_function"], interval["interval"])
            for sequence, interval in itertools.product(sequences["sequence"].tolist(), self._db_manager.kwargs.get('distance_intervals'))
        )

        existing_combinations = set(
            (metric["sequence"], metric["distance_function"], metric["interval"])
            for metric in computed_metrics
        )

        unmatched_sequences = all_combinations - existing_combinations

        empty_graph_metrics = []
        for sequence_value, distance_function, interval in tqdm(unmatched_sequences, total=len(unmatched_sequences),
                                                                desc="Executing empty graph metrics computation tasks"):
            empty_graph_metrics.append(
                DistanceBasedGraph(
                    sequence_value=sequence_value,
                    distances=pd.DataFrame(),
                    distance_function=distance_function,
                    interval=interval
                ).compute_metrics()
            )

        return pd.DataFrame(empty_graph_metrics)

    def _compute_similarity(self, distances, sequence_value):
        graphs = []

        for distance_interval in self._db_manager.kwargs.get('distance_intervals'):
            distance_function = distance_interval['distance_function']
            interval = distance_interval['interval']

            filtered_distances = distances[
                (distances[distance_function] >= interval[0]) &
                (distances[distance_function] < interval[1])
                ]
            filtered_distances = filtered_distances[['sequence_id', 'aa_src', 'aa_dst']]

            graphs.append(
                DistanceBasedGraph(
                    sequence_value=sequence_value,
                    distances=filtered_distances,
                    distance_function=distance_function,
                    interval=interval
                )
            )

        return [
            GraphSimilarityContext().compute(
                graph1=g1,
                graph2=g2,
                **self._db_manager.kwargs
            )
            for g1, g2 in itertools.combinations(graphs, 2)
        ]

    def _compare(self, sequence_value, distances, distance_function, interval):
        graph = DistanceBasedGraph(
                sequence_value=sequence_value,
                distances=distances,
                distance_function=distance_function,
                interval=interval
        )
        erdos_renyi_graphs = graph.get_erdos_renyi_graph()

        updated_kwargs = {**self._db_manager.kwargs, "graph_similarity_functions": self._db_manager.kwargs.get('random_graph_sim_funcs')}

        return [
            GraphSimilarityContext().compute(
                graph1=graph,
                graph2=g2,
                **updated_kwargs
            )
            for g2 in erdos_renyi_graphs
        ]


class NotebookDBService(AnalysisService):
    def __init__(self, **kwargs):
        super(NotebookDBService, self).__init__(**kwargs)

    def get_sequences_with_max_distance(self, distance_function):
        max_distance = self._db_manager.distance_repository.get_max_distance(distance_function)

        if max_distance is None or max_distance.empty:
            return None

        sequence_with_max_distance = self._db_manager.sequence_repository.get_by_ids(
            max_distance["sequence_id"].tolist()
        ).compute()

        return max_distance.merge(sequence_with_max_distance, on="sequence_id", how="left")

    def get_distance_values(self, distance_functions):
        self._db_manager.distance_repository.get_all(attr=distance_functions).compute()

    def get_distance_values_and_pivot(self, distance_functions):
        data = self._db_manager.distance_repository.get_all(attr=distance_functions).compute()
        data = data.melt(var_name="distance_function", value_name="value")

        chunks = [chunk.compute() for chunk in data.to_delayed()]
        return pd.concat(chunks, ignore_index=True)

        return result


class DBServiceContext:
    def __init__(self, db_service: DBService) -> None:
        self._db_service = db_service

    @property
    def db_service(self):
        return self._db_service


def data_repartition(data, partition_size):
    # validate partition size
    if partition_size <= 0:
        raise ValueError("Partition size must be greater than zero.")
    total_size = data.memory_usage(deep=True).sum().compute()
    desired_partition_size = partition_size * 1e6  # size in bytes
    optimal_partitions = max(1, int(total_size / desired_partition_size))

    return data.repartition(npartitions=optimal_partitions)


def _get_db_path():
    config_path = os.getenv("DB_PARQUET_PATH")

    if not config_path:
        raise ValueError("Missing 'PARQUET_PATH' environment variable in the .env file.")

    return Path(config_path).resolve()
