import logging
import os
from pathlib import Path
from typing import Optional
import pandas as pd
from dotenv import load_dotenv
from pydantic import BaseModel, FilePath, Field, root_validator, DirectoryPath, PositiveInt, ValidationError
from module.application_context import ApplicationContext
from module.logger_handler import LoggerHandler
from util.json_parser import output_config, input_config

DISTANCE_FUNCTIONS = ['euclidean', 'canberra', 'lance_williams', 'clark', 'soergel', 'bhattacharyya', 'angular_separation']


class NotebookArguments(BaseModel):
    dataset: FilePath = Field(description="Path to the input dataset in csv format.")
    output_path: DirectoryPath = Field(description="The path to save the outputs")

    min_sequence_len: Optional[PositiveInt] = Field(
        default=None,
        description="Minimum sequence length."
    )

    max_sequence_len: Optional[PositiveInt] = Field(
        default=None,
        description="Maximum sequence length."
    )

    @root_validator
    def validator(cls, values):
        # sequence_len
        min_len = values.get("min_sequence_len")
        max_len = values.get("max_sequence_len")

        if min_len is not None and max_len is not None and max_len <= min_len:
            raise ValidationError("max_sequence_len must be greater than min_sequence_len.")

        # mode
        values['mode'] = "notebook"
        values['mode_path_name'] = "Notebook_Analysis"

        # distance functions
        values['distance_functions'] = DISTANCE_FUNCTIONS

        # output paths
        values['output_paths'] = output_config(**values)

        return values


class NotebookApp:
    _instance = None  # This is the single instance of the class

    def __new__(cls, dotenv_path):
        if cls._instance is None:
            # Create a new instance only if one doesn't already exist
            cls._instance = super(NotebookApp, cls).__new__(cls)
            cls._instance._init(dotenv_path)

        config = {
            'dataset_path': Path(os.getenv("DATASET_PATH")).resolve(),
            'pdb_path': Path(os.getenv("PDB_PATH")).resolve(),
            'notebook_output_path': Path(os.getenv("NOTEBOOK_OUTPUT_PATH")).resolve(),
            'sequence_analysis_path': Path(os.getenv("SEQUENCE_ANALYSIS_PATH")).resolve(),
            'graph_analysis_path': Path(os.getenv("GRAPH_ANALYSIS_PATH")).resolve(),
            'min_sequence_len': os.getenv("MIN_SEQUENCE_LEN"),
            'max_sequence_len': os.getenv("MAX_SEQUENCE_LEN"),
        }

        logging.getLogger('logger').info(
            "Setting:\n" + "\n".join(f"{key}: {value}" for key, value in config.items())
        )

        return cls._instance

    def _init(self, dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)

        dataset_path = Path(os.getenv("DATASET_PATH")).resolve()
        output_path = Path(os.getenv("NOTEBOOK_OUTPUT_PATH")).resolve()
        self._pdb_path = Path(os.getenv("PDB_PATH")).resolve()
        min_sequence_len = os.getenv("MIN_SEQUENCE_LEN")
        max_sequence_len = os.getenv("MAX_SEQUENCE_LEN")

        self._config = NotebookArguments(
            dataset=dataset_path,
            output_path=output_path,
            min_sequence_len=min_sequence_len,
            max_sequence_len=max_sequence_len
        )

        self._context = ApplicationContext(**self._config.dict())

        self._sequence_analysis = input_config(
                input_path=Path(os.getenv("SEQUENCE_ANALYSIS_PATH")).resolve(),
                mode=self._config.mode
        )

        self._graph_analysis = input_config(
                input_path=Path(os.getenv("GRAPH_ANALYSIS_PATH")).resolve(),
                mode=self._config.mode
        )

        # Step 1: Initialize logger
        self._init_logger()

        # Step 2: Load input data
        data = self._load_data()

        # Step 3: Validate input data
        data = self._validate_data(data)

        # Step 4: Filter sequences by length
        data = self._filter_sequences_by_length(data)

        # Step 5: Prepare database
        self._data = self._prepare_data(data)

    @property
    def data(self):
        return self._data

    @property
    def pdb_path(self):
        return self._pdb_path

    @property
    def sequence_analysis(self):
        return self._sequence_analysis

    @property
    def graph_analysis(self):
        return self._graph_analysis

    @property
    def graph_analysis(self):
        return self._graph_analysis

    def paths(self):
        return self._config.output_paths

    def _init_logger(self) -> None:
        LoggerHandler.init_logger(
            log_output_path=self._config.output_paths['log_file']
        )

    def _load_data(self) -> pd.DataFrame:
        return self._context.data_loader.read_file(
            filepath=self._config.dataset
        )

    def _validate_data(self, data: pd.DataFrame) -> pd.DataFrame:
        data = self._context.data_validator.validate(
            data=data,
            output_paths=self._config.output_paths
        )
        return data

    def _filter_sequences_by_length(self, data: pd.DataFrame) -> pd.DataFrame:
        data = data.assign(length=data['sequence'].str.len())

        min_sequence_len = self._config.min_sequence_len
        max_sequence_len = self._config.max_sequence_len

        if min_sequence_len and max_sequence_len:
            data = data[(data['length'] >= min_sequence_len) & (data['length'] <= max_sequence_len)]

        if min_sequence_len:
            data = data[data['length'] >= min_sequence_len]

        if max_sequence_len:
            data = data[data['length'] <= max_sequence_len]

        return data

    def _prepare_data(self, data):
        return self._context.db_service.prepare_data(data)

    def get_sequences_with_largest_distance(self, distance_function):
        sequences_with_largest_distance = self._context.db_service.get_sequences_with_largest_distance(distance_function)
        columns = ['sequence', 'aa_src', 'aa_dst', *self._config.distance_functions]
        return sequences_with_largest_distance[columns]

    def get_distance_values(self, distance_functions):
        return self._context.db_service.get_distance_values(distance_functions)

    def get_distance_values_and_pivot(self, distance_functions, sequence=None):
        return self._context.db_service.get_distance_values_and_pivot(distance_functions, sequence)
