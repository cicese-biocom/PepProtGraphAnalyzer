import logging
import multiprocessing
from abc import ABC, abstractmethod
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
import pandas as pd
import dask.dataframe as dd
from tqdm import tqdm
from modules import esm2_model_handler
from modules.application_context import ApplicationContext
from modules.argument_parser import CommonArguments, TertiaryStructurePredictionMethod
from modules.tertiary_structure_handler import get_atom_coordinates_matrices
from utils.distances import distance
from modules.logging_handler import LoggingHandler
from utils.json_parser import get_distance_intervals

AMINO_ACIDS = list("ARNDCQEGHILKMFPSTWYV")
AMINO_ACID_3LETTER_CODES = [
    "ALA", "ARG", "ASN", "ASP", "CYS", "GLN", "GLU", "GLY", "HIS", "ILE",
    "LEU", "LYS", "MET", "PHE", "PRO", "SER", "THR", "TRP", "TYR", "VAL"
]


class Pipeline(ABC):
    def __init__(self, parameters: CommonArguments):
        self._parameters = parameters
        self._context = ApplicationContext(self._parameters.mode)

    def execute(self):
        # Step 1: Initialize logger
        self.initialize_logger()

        # Step 2: Load input data
        data = self.load_data()

        # Step 3: Validate input data
        data = self.validate_data(data)

        # Step 4: Get missing sequences in the database
        data = self.get_sequences_to_process(data)

        # Step 6: Process data
        self.process_data(data)

    def initialize_logger(self) -> None:
        LoggingHandler.initialize_logger(
            logger_settings_path=Path('settings').joinpath('logger_setting.json'),
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

    @abstractmethod
    def process_data(self, data):
        pass

    def get_sequences_to_process(self, data):
        pass


class DataIngestionPipeline(Pipeline):
    def get_sequences_to_process(self, data):
        missing_sequences = self._context.data_manager.get_missing_sequences(dd.from_pandas(data)).compute()

        if missing_sequences.empty:
            logging.getLogger('logger').info(f"All sequences have already been processed.")
            quit()

        return missing_sequences

    def process_data(self, data: pd.DataFrame):
        # Step 1: Calculate sequence length
        data = self._calculate_sequence_length(data)

        # Step 2: Calculate perplexities
        data = self._calculate_perplexities(data)

        # Step 3: Save sequences to parquet
        data = self._save_sequences_to_db(data)

        # Step 4: Calculate inter-amino acid distance
        distances = self._compute_inter_amino_acid_distance(data)

        # Step 5: Save distances to parquet
        self._save_distances_to_db(distances)

    def _calculate_sequence_length(self, data: pd.DataFrame):
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

    def _calculate_perplexities(self, data: pd.DataFrame):
        if self._parameters.tertiary_structure_method == TertiaryStructurePredictionMethod.esmfold:
            esm2_model = esm2_model_handler.get_models('esm2_t36')

            _, _, perplexities = esm2_model_handler.get_representations(data, esm2_model[0]['model'])
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
            (row['sequence_id'], atom_coordinates, self._parameters.distance_functions)
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
                                         columns=["sequence_id", "aa_src",
                                                  "aa_dst"] + self._parameters.distance_functions)

        logging.getLogger('logger').info(f"The inter-amino acid distance computation has been successfully completed.")

        return distances

    def _save_sequences_to_db(self, data):
        data_new = self._context.data_manager.append_sequences(dd.from_pandas(data))
        data_new = data_new[["sequence_id", "sequence", "id"]]

        logging.getLogger('logger').info("Successfully saved %d sequences to the database.", len(data))

        return data_new.compute()

    def _save_distances_to_db(self, distances):
        self._context.data_manager.append_distances(dd.from_pandas(distances))
        logging.getLogger('logger').info("Successfully saved %d distances to the database.", len(distances))


class AnalyzerPipeline(Pipeline):
    def get_sequences_to_process(self, data):
        self._context.data_manager.initialize_analysis_data(dd.from_pandas(data))
        return data


class SequenceAnalyzerPipeline(AnalyzerPipeline):
    def process_data(self, data: pd.DataFrame):
        # Get sequence length
        self._get_sequence_length()

        # Get perplexities
        self._get_perplexities()

        # Get amino acid composition
        self._calculate_amino_acid_composition(data)

        # Get inter-amino acid distance statistics
        self._get_inter_amino_acid_distance_statistics()

        # Finalize analysis data
        self._context.data_manager.finalize_analysis_data()

    def _get_sequence_length(self):
        sequence_length = self._context.data_manager.get_sequence_length()

        file_path = self._parameters.output_paths['sequence_length']
        sequence_length.to_csv(file_path, index=False)

        logging.getLogger('logger').info(f"Sequence lengths successfully recovered. See: {file_path}")

    def _get_perplexities(self):
        perplexities = self._context.data_manager.get_perplexities()

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

        logging.getLogger('logger').info(f"The amino acid composition has been successfully calculated. See: {file_path}")

    def _get_inter_amino_acid_distance_statistics(self):
        statistics = self._context.data_manager.get_distance_statistics(self._parameters.distance_functions)

        file_path = self._parameters.output_paths['sequence_inter_amino_acid_distances_statistics']
        statistics.to_csv(file_path, index=False)

        logging.getLogger('logger').info(
            f"Inter-amino acid distance statistics successfully computed. See: {file_path}")


class GraphAnalyzerPipeline(AnalyzerPipeline):
    def process_data(self, data):
        # Obtaining distance-based graph metrics
        self._get_distance_based_graph_metrics()

    def _get_distance_based_graph_metrics(self):
        distance_intervals = get_distance_intervals(self._parameters.distance_intervals_json)
        graph_metrics = self._context.data_manager.get_graph_metrics(distance_intervals, batch_size=1000)

        graph_metrics.to_csv("metrics_results_1.csv", index=False)

        file_path = self._parameters.output_paths['graph_metrics']
        graph_metrics.to_csv(file_path, index=False)

        logging.getLogger('logger').info(
            f"Graph metrics successfully computed. See: {file_path}")


def _compute_distance(sequence, atom_coordinates, distance_functions):
    number_of_amino_acid = len(atom_coordinates)

    distances = []

    for i in range(number_of_amino_acid):
        for j in range(i + 1, number_of_amino_acid):
            distance_values = [
                distance(atom_coordinates[i], atom_coordinates[j], distance_function)
                for distance_function in distance_functions
            ]

            distances.append((sequence, i, j, *distance_values))

    return distances
