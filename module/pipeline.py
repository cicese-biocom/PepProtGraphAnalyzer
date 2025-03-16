import logging
import multiprocessing
from abc import ABC, abstractmethod
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from tqdm import tqdm
from module.esm2_model_handler import get_representations, get_models
from module.application_context import ApplicationContext
from module.argument_parser import TertiaryStructurePredictionMethod
from module.tertiary_structure_handler import get_atom_coordinates_matrices
from module.logger_handler import LoggerHandler
from util.statistics import get_stats

AMINO_ACIDS = list("ARNDCQEGHILKMFPSTWYV")
AMINO_ACID_3LETTER_CODES = [
    "ALA", "ARG", "ASN", "ASP", "CYS", "GLN", "GLU", "GLY", "HIS", "ILE",
    "LEU", "LYS", "MET", "PHE", "PRO", "SER", "THR", "TRP", "TYR", "VAL"
]


class Pipeline(ABC):
    def __init__(self, parameters):
        self._parameters = parameters
        self._context = ApplicationContext(**parameters.dict())

    def execute(self):
        # Step 1: Initialize logger
        self.init_logger()

        # Step 2: Load input data
        data = self.load_data()

        # Step 3: Validate input data
        data = self.validate_data(data)

        # Step 4: Prepare database
        data = self.prepare_data(data)

        # Step 6: Process data
        self.process_data(data)

    def init_logger(self) -> None:
        LoggerHandler.init_logger(
            log_output_path=self._parameters.output_paths['log_file']
        )

    def load_data(self) -> pd.DataFrame:
        return self._context.data_loader.read_file(
            filepath=self._parameters.dataset
        )

    def validate_data(self, data: pd.DataFrame) -> pd.DataFrame:
        data = self._context.data_validator.validate(
            data=data,
            output_paths=self._parameters.output_paths
        )
        return data

    def prepare_data(self, data):
        return self._context.db_service.prepare_data(data)

    @abstractmethod
    def process_data(self, data):
        pass


class DataIngestionPipeline(Pipeline):
    def process_data(self, data: pd.DataFrame):
        # Step 1: Calculate sequence lengths
        sequences = self._compute_sequence_lengths(data)

        # Step 2: Calculate perplexities
        sequences = self._compute_sequence_perplexities(sequences)

        # Step 3: Calculate inter-amino acid distance
        distances = self._compute_inter_amino_acid_distance(sequences)

        # Step 4: Save sequences to parquet
        self._save_to_db(sequences, distances)

    def _compute_sequence_lengths(self, data: pd.DataFrame):
        data = data.assign(length=data['sequence'].str.len())

        minimum_sequence_length = self._parameters.minimum_sequence_length
        maximum_sequence_length = self._parameters.maximum_sequence_length

        if minimum_sequence_length and maximum_sequence_length:
            data = data[(data['length'] >= minimum_sequence_length) & (data['length'] <= maximum_sequence_length)]

        if minimum_sequence_length:
            data = data[data['length'] >= minimum_sequence_length]

        if maximum_sequence_length:
            data = data[data['length'] <= maximum_sequence_length]

        logging.getLogger('logger').info(f"The sequence length calculation has been successfully completed.")

        return data

    def _compute_sequence_perplexities(self, data: pd.DataFrame):
        if self._parameters.tertiary_structure_method == TertiaryStructurePredictionMethod.esmfold:
            esm2_model = get_models('esm2_t36')

            _, _, perplexities = get_representations(data, esm2_model[0]['model'])
            data = data.merge(perplexities, on="sequence", how="inner")

            logging.getLogger('logger').info(f"The perplexity calculation has been successfully completed.")
        else:
            data['esm2_perplexity'] = np.nan

        return data

    def _compute_inter_amino_acid_distance(self, data: pd.DataFrame):
        # Get atom coordinate
        atom_coordinates_matrices = get_atom_coordinates_matrices(data, self._parameters)

        num_cores = multiprocessing.cpu_count()

        args = [
            (row['sequence'], atom_coordinates, self._parameters.distance_strategies)
            for (_, row), atom_coordinates in zip(data.iterrows(), atom_coordinates_matrices)
        ]

        with tqdm(total=len(args), desc="Computing inter-amino acid distance") as progress:
            with ProcessPoolExecutor(max_workers=num_cores) as pool:
                futures = []
                for arg in args:
                    future = pool.submit(_compute_distance, *arg)
                    future.add_done_callback(lambda p: progress.update())
                    futures.append(future)

                distances = [item for future in futures for item in future.result()]
                distances = pd.DataFrame(distances,
                                         columns=["sequence", "aa_src",
                                                  "aa_dst"] + self._parameters.distance_functions)

        logging.getLogger('logger').info(f"The inter-amino acid distance computation has been successfully completed.")

        return distances

    def _save_to_db(self, sequences, distances):
        sequences = self._save_sequences_to_db(sequences)
        distances = merge_data(sequences, distances)
        self._save_distances_to_db(distances)

    def _save_sequences_to_db(self, sequences):
        data_new = self._context.db_service.add_sequences(sequences)
        logging.getLogger('logger').info("Successfully saved %d sequences to the database.", len(sequences))

        return data_new

    def _save_distances_to_db(self, distances):
        self._context.db_service.add_distances(distances)
        logging.getLogger('logger').info("Successfully saved %d distances to the database.", len(distances))


def _compute_distance(sequence, atom_coordinates, distance_strategies):
    number_of_amino_acid = len(atom_coordinates)

    distances = []

    for i in range(number_of_amino_acid):
        for j in range(i + 1, number_of_amino_acid):
            distance_values = [
                strategy.compute(atom_coordinates[i], atom_coordinates[j])
                for strategy in distance_strategies
            ]

            distances.append((sequence, i, j, *distance_values))

    return distances


def merge_data(sequences: pd.DataFrame, distances: pd.DataFrame) -> pd.DataFrame:
    sequences = sequences[["sequence_id", "sequence"]]

    # Merge DataFrames based on the 'sequence' column
    merged_data = distances.merge(sequences, on="sequence", how="inner")

    # Remove the 'sequence' column after merging
    merged_data.drop(columns=['sequence'], inplace=True)

    return merged_data


class SequenceAnalyzerPipeline(Pipeline):
    def process_data(self, data):
        # Get sequence length
        self._get_sequence_lengths()

        # Get perplexities
        self._get_sequence_perplexities()

        # Get amino acid composition
        self._calculate_amino_acid_composition(data)

        # Get inter-amino acid distance summary
        self._get_inter_amino_acid_distance_summary()

    def _get_sequence_lengths(self):
        sequence_lengths = self._context.db_service.get_sequence_lengths()

        file_path = self._parameters.output_paths['sequence_length']
        sequence_lengths.to_csv(file_path, index=False)

        logging.getLogger('logger').info(f"Sequence lengths successfully recovered. See: {file_path}")

    def _get_sequence_perplexities(self):
        perplexities = self._context.db_service.get_sequence_perplexities()

        file_path = self._parameters.output_paths['sequence_perplexities']
        perplexities.to_csv(file_path, index=False)

        logging.getLogger('logger').info(f"Perplexities successfully recovered. See: {file_path}")

    def _calculate_amino_acid_composition(self, data: pd.DataFrame):
        counts = np.zeros(len(AMINO_ACIDS), dtype=np.int64)

        for seq in tqdm(data['sequence'], total=len(data), desc=f"Calculating amino acid composition"):
            seq_array = np.array(list(seq))
            for i, aa in enumerate(AMINO_ACIDS):
                counts[i] += np.sum(seq_array == aa)

        amino_acid_composition = pd.DataFrame({
            "code_short": AMINO_ACIDS,
            "code_large": AMINO_ACID_3LETTER_CODES,
            "count": counts
        })

        file_path = self._parameters.output_paths['sequence_amino_acid_composition']
        amino_acid_composition.to_csv(file_path, index=False)

        logging.getLogger('logger').info(
            f"The amino acid composition has been successfully calculated. See: {file_path}")

    def _get_inter_amino_acid_distance_summary(self):
        summary = self._context.db_service.get_distance_stats(
            distance_functions=self._parameters.distance_functions
        )

        file_path = self._parameters.output_paths['sequence_inter_amino_acid_distances_summary']
        summary.to_csv(file_path, index=False)

        logging.getLogger('logger').info(
            f"Inter-amino acid distance summary successfully computed. See: {file_path}")


class GraphAnalyzerPipeline(Pipeline):
    def process_data(self, data):
        # Step 1: Compute graph metrics
        metrics = self._compute_graph_metrics()

        # Step 2: Compute graph metrics summary
        self._compute_graph_metrics_summary(metrics)

        # Step 3: Compute empty graph summary
        self._compute_empty_graph_summary(metrics)

        # Step 4: Compute graph similarity
        similarities = self._compute_graph_similarity()

        # Step 5: Compute graph similarity summary
        self._compute_graph_similarity_summary(similarities)

        # Step 6: Compare with random graphs
        comparison = self._compare_with_random_graphs()

        # Step 7: Compare with random graphs
        self._compare_with_random_graphs_summary(comparison)

    def _compute_graph_metrics(self):
        metrics = self._context.db_service.compute_graph_metrics()

        file_path = self._parameters.output_paths['graph_metrics']
        metrics.to_csv(file_path, index=False)

        logging.getLogger('logger').info(
            f"Graph metrics successfully computed. See: {file_path}")

        return metrics

    def _compute_graph_similarity(self):
        similarities = self._context.db_service.compute_graph_similarity()

        file_path = self._parameters.output_paths['graph_similarities']
        similarities.to_csv(file_path, index=False)

        logging.getLogger('logger').info(
            f"Graph similarities successfully computed. See: {file_path}")

        return similarities

    def _compute_graph_metrics_summary(self, metrics: pd.DataFrame):
        numeric_cols = metrics.select_dtypes(include=['number', 'float']).columns

        file_path = self._parameters.output_paths['graph_metrics_summary']

        for col in tqdm(numeric_cols, total=len(numeric_cols), desc='Calculating metrics statistics.'):
            filtered_metrics = metrics[["sequence", "distance_function", "interval", col]]
            stats = (
                filtered_metrics.groupby(["distance_function", "interval"])[col]
                .apply(get_stats)
                .apply(pd.Series)
                .reset_index()
            )

            stats.columns = ["distance_function", "interval", "stat", "value"]

            stats = stats.pivot(
                index=["distance_function", "interval"],
                columns="stat",
                values="value"
            ).reset_index()

            stats = stats[
                ["distance_function", "interval", "count", "min", "mean", "std", "p25", "p50", "p75", "max", "skewness",
                 "kurtosis"]]
            stats["count"] = stats["count"].astype(int)

            stats.to_csv(f"{file_path}-{col}.csv", index=False)

        logging.getLogger('logger').info(
            f"Graph metrics summary successfully computed. See: {file_path}")

    def _compute_empty_graph_summary(self, metrics: pd.DataFrame):
        filtered_metrics = metrics[metrics["number_of_edges"] == 0][
            ["distance_function", "interval", "number_of_edges"]]

        logging.getLogger('logger').info(
            f"Total graphs processed {len(metrics)}, "
            f"{len(metrics) - len(filtered_metrics)} non-empty graphs and {len(filtered_metrics)} empty graphs."
        )

        if not filtered_metrics.empty:
            stats = (
                filtered_metrics.groupby(["distance_function", "interval"])
                .count()
                .apply(pd.Series)
                .reset_index()
            )

            stats.columns = ["distance_function", "interval", "number_of_empty_graphs"]

            stats = stats[["distance_function", "interval", "number_of_empty_graphs"]]

            file_path = self._parameters.output_paths['empty_graph_summary']
            stats.to_csv(file_path, index=False)

            logging.getLogger('logger').info(
                f"Empty graph summary successfully computed. See: {file_path}")

    def _compute_graph_similarity_summary(self, similarities):
        index_columns = ["distance_function_1", "interval_1", "distance_function_2", "interval_2"]

        file_path = self._parameters.output_paths['graph_similarity_summary']

        for col in tqdm(self._parameters.graph_similarity_functions,
                        total=len(self._parameters.graph_similarity_functions),
                        desc='Calculating similarity statistics.'):
            filtered_similarity = similarities[['sequence', *index_columns, col]]
            stats = (
                filtered_similarity.groupby([*index_columns])[col]
                .apply(get_stats)
                .apply(pd.Series)
                .reset_index()
            )

            stats.columns = [*index_columns, "stat", "value"]

            stats = stats.pivot(
                index=[*index_columns],
                columns="stat",
                values="value"
            ).reset_index()

            stats = stats[
                [*index_columns, "count", "min", "mean", "std", "p25", "p50", "p75", "max", "skewness", "kurtosis"]]
            stats["count"] = stats["count"].astype(int)

            stats.to_csv(f"{file_path}-{col}.csv", index=False)

        logging.getLogger('logger').info(
            f"Graph similarity summary successfully computed. See: {file_path}")

    def _compare_with_random_graphs(self):
        comparison = self._context.db_service.compare_with_random_graphs()

        comparison["random_graph"] = comparison.groupby(["sequence", "distance_function_2", "interval_2"]).cumcount()+1
        comparison.drop(columns=["distance_function_2", "interval_2"], inplace=True)

        comparison.rename(columns={"distance_function_1": "distance_function"}, inplace=True)
        comparison.rename(columns={"interval_1": "interval"}, inplace=True)
        comparison = comparison[['sequence', 'distance_function', 'interval', 'random_graph', *self._parameters.random_graph_sim_funcs]]

        file_path = self._parameters.output_paths['random_graph_comparison']
        comparison.to_csv(file_path, index=False)

        logging.getLogger('logger').info(
            f"Graph similarities successfully computed. See: {file_path}")

        return comparison

    def _compare_with_random_graphs_summary(self, comparison):
        index_columns = ["distance_function", "interval"]

        file_path = self._parameters.output_paths['random_graph_comparison_summary']

        for col in tqdm(self._parameters.random_graph_sim_funcs,
                        total=len(self._parameters.random_graph_sim_funcs),
                        desc='Calculating similarity statistics.'):
            filtered_similarity = comparison[[*index_columns, col]]
            stats = (
                filtered_similarity.groupby([*index_columns])[col]
                .apply(get_stats)
                .apply(pd.Series)
                .reset_index()
            )

            stats.columns = [*index_columns, "stat", "value"]

            stats = stats.pivot(
                index=[*index_columns],
                columns="stat",
                values="value"
            ).reset_index()

            stats = stats[
                [*index_columns, "count", "min", "mean", "std", "p25", "p50", "p75", "max", "skewness", "kurtosis"]]
            stats["count"] = stats["count"].astype(int)

            stats.to_csv(f"{file_path}-{col}.csv", index=False)

        logging.getLogger('logger').info(
            f"Compare with random graphs summary successfully computed. See: {file_path}")
