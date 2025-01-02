import logging
import multiprocessing
from abc import ABC, abstractmethod
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
import pandas as pd
import dask.dataframe as dd
from dask.array import stats
from tqdm import tqdm
from modules import esm2_model_handler
from modules.application_context import ApplicationContext
from modules.argument_parser import CommonArguments, TertiaryStructurePredictionMethod
from modules.tertiary_structure_handler import get_atom_coordinates_matrices
from utils.distances import distance
from modules.logging_handler import LoggingHandler


AMINO_ACIDS = list("ARNDCQEGHILKMFPSTWYV")
AMINO_ACID_3LETTER_CODES = [
    "ALA", "ARG", "ASN", "ASP", "CYS", "GLN", "GLU", "GLY", "HIS", "ILE",
    "LEU", "LYS", "MET", "PHE", "PRO", "SER", "THR", "TRP", "TYR", "VAL"
]


class Pipeline(ABC):
    def __init__(self, parameters: CommonArguments):
        self._context = ApplicationContext()
        self._parameters = parameters

    def execute(self):
        # Step 1: Initialize_logger
        self.initialize_logger()

        # Step 2: Load data
        data = self.load_data()

        # Step 4: Validate data
        data = self.validate_data(data)

        # Step 5: Analyze data
        self.analyze_data(data)

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
    def analyze_data(self, data):
        pass


class DataIngestionPipeline(Pipeline):
    def analyze_data(self, data):
        # Step 1: Calculate sequence length
        data = self._calculate_sequence_length(data)

        # Step 2: Calculate residue composition
        self._calculate_amino_acid_composition(data)

        # Step 3: Calculate perplexities
        self._calculate_perplexities(data)

        # Step 4: Calculate inter-amino acid distance
        self._compute_inter_amino_acid_distance(data)

        # Step 5: Calculate inter-amino acid distance statistics
        self._calculate_statistics()

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

        data.to_csv(self._parameters.output_paths['sequence_length'], index=False)

        logging.getLogger('logger').info("Calculated sequence length")

        return data.drop('length', axis=1)

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

        amino_acid_composition.to_csv(self._parameters.output_paths['sequence_amino_acid_composition'], index=False)

        logging.getLogger('logger').info("Calculated amino acid composition")

    def _calculate_perplexities(self, data: pd.DataFrame):
        if self._parameters.tertiary_structure_method == TertiaryStructurePredictionMethod.esmfold:
            esm2_model = esm2_model_handler.get_models('esm2_t36')

            _, _, perplexities = esm2_model_handler.get_representations(data, esm2_model[0]['model'])
            perplexities = data.merge(perplexities, on="sequence", how="inner")

            perplexities.to_csv(self._parameters.output_paths['sequence_perplexities'], index=False)

            logging.getLogger('logger').info("Calculated perplexities")

    def _compute_inter_amino_acid_distance(self, data: pd.DataFrame):
        # Get atom coordinate
        atom_coordinates_matrices = get_atom_coordinates_matrices(data, self._parameters)

        num_cores = multiprocessing.cpu_count()

        args = [
            (row['sequence'], atom_coordinates, self._parameters.distance_functions)
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
                                         columns=["sequence", "aminoacid_source",
                                                  "aminoacid_target"] + self._parameters.distance_functions)

                dask_distances = dd.from_pandas(distances, npartitions=4)
                dask_distances.to_parquet(
                    'data',
                    write_metadata_file=False
                )

        logging.getLogger('logger').info("Calculated inter-amino acid distances")

    def _calculate_statistics(self):
        statistics = {}
        for distance_function in tqdm(self._parameters.distance_functions, desc="Computing inter-amino acid distance statistics"):
            column = dd.read_parquet('data/', columns=[distance_function])

            column_array = column.to_dask_array(lengths=True)
            column_computed = column.compute()

            statistics[distance_function] = {
                "count": column.count().compute().iloc[0],
                "mean": column.mean().compute().iloc[0],
                "std": column.std().compute().iloc[0],
                "min": column.min().compute().iloc[0],
                "p25": column_computed.quantile(0.25).iloc[0],
                "p50": column_computed.quantile(0.50).iloc[0],
                "p75": column_computed.quantile(0.75).iloc[0],
                "max": column.max().compute().iloc[0],
                "skewness": stats.skew(column_array).compute()[0],
                "kurtosis": stats.kurtosis(column_array, fisher=False).compute()[0]
            }

        statistics = pd.DataFrame(statistics).T
        statistics.index.name = "distance_function"
        statistics.reset_index(inplace=True)

        statistics["count"] = statistics["count"].astype(int)

        statistics.to_csv(self._parameters.output_paths['sequence_inter_amino_acid_distances_statistics'], index=False)

        logging.getLogger('logger').info("Calculated inter-amino acid distances statistics")

    def _save_to_csv_inter_amino_acid_distance_per_distance_function(self, distances: dd.DataFrame):
        pass


class GraphAnalyzerPipeline(Pipeline):
    def analyze_data(self, data):
        pass


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

