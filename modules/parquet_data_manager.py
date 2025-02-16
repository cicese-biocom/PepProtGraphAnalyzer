import logging
import os
import shutil
import yaml
from dask.array import stats
import dask.dataframe as dd
from pathlib import Path
import pandas as pd
import pyarrow as pa
from tqdm import tqdm
from typing import List


class ParquetManager:
    def __init__(self, path: Path, schema):
        self._path, self._empty = self._init_collection(path)
        self._schema = schema

    @property
    def empty(self):
        return self._empty

    @empty.setter
    def empty(self, empty):
        self._empty = empty

    @property
    def path(self):
        return self._path

    @property
    def schema(self):
        return self._schema

    @staticmethod
    def _init_collection(path: Path):
        try:
            data = dd.read_parquet(path)
            if data.compute().empty:
                return path, True
            else:
                return path, False
        except Exception:
            return path, True

    def read_parquet(self, columns=None, filters=None, partition_size=None):
        if self.empty:
            return None
        
        data = dd.read_parquet(
            path=self._path,
            columns=columns,
            filters=filters
        )

        if partition_size:
            data = self._repartition_data(data, partition_size)
        return data

    def write_parquet(self, new_data: dd.DataFrame, write_index=False, overwrite=False):
        """Writes a Dask DataFrame to a Parquet file."""
        new_data = self._repartition_data(new_data, 300)

        new_data.to_parquet(
            self._path,
            schema=self._schema,
            write_index=write_index,
            overwrite=overwrite
        )

        self.empty = False

    def remove_parquet(self):
        shutil.rmtree(self._path, ignore_errors=True)
        self.empty = True

    def append_parquet(self, new_data: dd.DataFrame):
        """Appends data to an existing Parquet file."""
        if not self.empty:
            existing_data = self.read_parquet(partition_size=100)
            new_data = dd.concat([existing_data, new_data])

        self.write_parquet(
            new_data, 
            write_index=False, 
            overwrite=True
        )

        self.empty = False

    @staticmethod
    def _repartition_data(data, partition_size):
        # calculate optimal partitions
        total_size = data.memory_usage(deep=True).sum().compute()
        desired_partition_size = partition_size * 1e6
        optimal_partitions = max(1, int(total_size / desired_partition_size))

        # repartition data
        data = data.repartition(npartitions=optimal_partitions)
        data = data.persist()

        return data


class DataManager:
    def __init__(self):
        """Initialize the data manager with the given database path."""
        with open(os.getcwd() + os.sep + "settings" + os.sep + "db_config.yml", "r") as file:
            config = yaml.safe_load(file)

        self._db_path = Path(config.get("PARQUET_PATH")).resolve()

        if self._db_path is None:
            logging.getLogger('logger').critical(
                f"The variable 'PARQUET_PATH' is not defined in the YAML file.")
            quit()

        # Set collection sequence         
        self._sequences_manager = ParquetManager(
            path=self._db_path.joinpath("sequences"),
            schema={
                "sequence_id": pa.int32(),
                "sequence": pa.string(),
                "length": pa.int32(),
                "esm2_perplexity": pa.float64()
            }
        )

        # Set collection distance
        self._distances_manager = ParquetManager(
            path=self._db_path.joinpath("distances"),
            schema={
                "sequence_id": pa.int32(),
                "aa_src": pa.int32(),
                "aa_dst": pa.int32(),
                "euclidean": pa.float64(),
                "canberra": pa.float64(),
                "lance_williams": pa.float64(),
                "clark": pa.float64(),
                "soergel": pa.float64(),
                "bhattacharyya": pa.float64(),
                "angular_separation": pa.float64()
            }
        )

        self._remove_inconsistent_sequences()

    def _remove_inconsistent_sequences(self):
        """
        This function ensures that the sequences and distances files contain consistent data.
        If there are discrepancies between the sequence IDs in both files, the distances file is updated.
            """
        # Remove inconsistent sequences
        if self._sequences_manager.empty != self._distances_manager.empty:
            # Ensure both files contain data; if their empty states differ, set both to False
            self._sequences_manager.remove_parquet()
            self._distances_manager.remove_parquet()

        elif not self._sequences_manager.empty:
            # Read sequence IDs from sequences file
            sequence_ids = self._sequences_manager.read_parquet(
                columns=['sequence_id'],
                partition_size=100
            )

            # Read distances and filter out entries that do not exist in sequences
            distances = self._distances_manager.read_parquet(
                partition_size=100
            )
            filtered_distances = distances[distances['sequence_id'].isin(sequence_ids['sequence_id'])]

            # Only overwrite the distances file if there are differences
            if len(distances) != len(filtered_distances):
                self._distances_manager.write_parquet(
                    filtered_distances,
                    write_index=False,
                    overwrite=True
                )


class DataIngestionManager(DataManager):
    def get_missing_sequences(self, new_sequences: dd.DataFrame) -> dd.DataFrame:
        """Checks which sequences are missing from the database."""
        if not self._sequences_manager.empty:
            existing_sequences = self._sequences_manager.read_parquet(
                columns=['sequence'],
                partition_size=100
            )

            return new_sequences[~new_sequences['sequence'].isin(existing_sequences['sequence'])]

        return new_sequences

    def append_sequences(self, new_sequences: dd.DataFrame):
        """Append new sequences to database."""
        # Assign sequence_id to new_sequences
        start_id = self._get_next_sequence_id()
        new_sequences["sequence_id"] = range(start_id, start_id + len(new_sequences))

        # Append to database
        self._sequences_manager.append_parquet(
            new_sequences[["sequence_id", "sequence", "length", "esm2_perplexity"]]
        )

        return new_sequences

    def _get_next_sequence_id(self):
        return int(self._sequences_manager.read_parquet(
            columns=['sequence_id'],
            partition_size=100
        ).max().compute().iloc[0] + 1) if not self._sequences_manager.empty else 1

    def append_distances(self, new_distances: dd.DataFrame):
        """Append new distances to database."""
        self._distances_manager.append_parquet(new_distances)


class DataAnalysisManager(DataManager):
    def __init__(self):
        super(DataAnalysisManager, self).__init__()
        self._sequences_manager_temp = ParquetManager(
            path=self._db_path.joinpath('_temp').joinpath('_sequences'),
            schema=self._sequences_manager.schema
        )

        self._distances_manager_temp = ParquetManager(
            path=self._db_path.joinpath('_temp').joinpath('_distances'),
            schema=self._distances_manager.schema
        )

    def initialize_analysis_data(self, sequences: dd.DataFrame):
        existing_sequences = self._prepare_sequences(sequences)
        self._prepare_distances(existing_sequences)

    def finalize_analysis_data(self):
        shutil.rmtree(self._db_path.joinpath('_temp'), ignore_errors=True)

    def _prepare_sequences(self, sequences: dd.DataFrame):
        if self._sequences_manager.empty:
            logging.getLogger('logger').critical(
                f"There are sequences for which data ingestion has not been performed.")
            quit()

        sequence_values = sequences['sequence'].compute().tolist()

        existing_sequences = self._sequences_manager.read_parquet(
            filters=[
                ('sequence', 'in', sequence_values)
            ],
            partition_size=100
        )

        if len(sequences) != len(existing_sequences):
            logging.getLogger('logger').critical(
                f"There are sequences for which data ingestion has not been performed.")
            quit()

        self._sequences_manager_temp.write_parquet(
            existing_sequences,
            write_index=False,
            overwrite=True
        )
        
        return existing_sequences['sequence_id'].compute().tolist()

    def _prepare_distances(self, sequence_ids: List):
        if self._distances_manager.empty:
            logging.getLogger('logger').critical(
                f"There are sequences for which data ingestion has not been performed.")
            quit()

        existing_distances = self._distances_manager.read_parquet(
            filters=[
                [('sequence_id', 'in', sequence_ids)]
            ],
            partition_size=100
        )

        self._distances_manager_temp.write_parquet(existing_distances)

    @staticmethod
    def _create_temporary_data(parquet_manager: ParquetManager, data: dd.DataFrame):
        parquet_manager = parquet_manager.path.joinpath('_temp')
        parquet_manager.write_parquet(
            data,
            write_index=False,
            overwrite=True
        )

    def get_sequence_length(self):
        data = self._sequences_manager_temp.read_parquet(
            columns=["sequence", "length"],
            partition_size=100
        )
        return data.compute()

    def get_perplexities(self):
        data = self._sequences_manager_temp.read_parquet(
            columns=["sequence", "esm2_perplexity"],
            partition_size=100
        )
        return data.compute()

    def get_distance_statistics(self, distance_functions):
        statistics = {}
        for distance_function in tqdm(distance_functions,
                                      desc="Computing inter-amino acid distance statistics"):
            column = self._distances_manager_temp.read_parquet(
                columns=[distance_function],
                partition_size=100
            ).compute()

            column_array = column.to_numpy()

            statistics[distance_function] = {
                "count": column.count().iloc[0],
                "mean": column.mean().iloc[0],
                "std": column.std().iloc[0],
                "min": column.min().iloc[0],
                "p25": column.quantile(0.25).iloc[0],
                "p50": column.quantile(0.50).iloc[0],
                "p75": column.quantile(0.75).iloc[0],
                "max": column.max().iloc[0],
                "skewness": stats.skew(column_array)[0],
                "kurtosis": stats.kurtosis(column_array, fisher=False)[0]
            }

        statistics = pd.DataFrame(statistics).T
        statistics.index.name = "distance_function"
        statistics.reset_index(inplace=True)

        statistics["count"] = statistics["count"].astype(int)

        return statistics
