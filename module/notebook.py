import pandas as pd
from dotenv import load_dotenv
from pydantic import BaseModel, FilePath, Field, root_validator, DirectoryPath
from module.application_context import ApplicationContext
from module.logger_handler import LoggerHandler
from util.json_parser import output_config

DISTANCE_FUNCTIONS = ['euclidean', 'canberra', 'lance_williams', 'clark', 'soergel', 'bhattacharyya', 'angular_separation']


class NotebookArguments(BaseModel):
    dataset: FilePath = Field(description="Path to the input dataset in csv format.")
    output_path: DirectoryPath = Field(description="The path to save the outputs")

    @root_validator
    def validator(cls, values):
        # mode
        values['mode'] = "notebook"
        values['mode_path_name'] = "Notebook"

        # distance functions
        values['distance_functions'] = DISTANCE_FUNCTIONS

        # output paths
        values['output_paths'] = output_config(**values)

        return values


class DBClient:
    def __init__(self, dataset_path, output_path):
        load_dotenv(dotenv_path=".env.jupyter")
        self._args = NotebookArguments(dataset=dataset_path, output_path=output_path)
        self._context = ApplicationContext(**self._args.dict())

        # Step 1: Initialize logger
        self._init_logger()

        # Step 2: Load input data
        data = self._load_data()

        # Step 3: Validate input data
        data = self._validate_data(data)

        self._data = self._prepare_data(data)

    @property
    def data(self):
        return self._data

    def _init_logger(self) -> None:
        LoggerHandler.init_logger(
            log_output_path=self._args.output_paths['log_file']
        )

    def _load_data(self) -> pd.DataFrame:
        return self._context.data_loader.read_file(
            filepath=self._args.dataset
        )

    def _validate_data(self, data: pd.DataFrame) -> pd.DataFrame:
        data = self._context.data_validator.validate(
            data=data,
            output_paths=self._args.output_paths
        )
        return data

    def _prepare_data(self, data):
        return self._context.db_service.prepare_data(data)

    def get_sequences_with_max_distance(self, distance_function):
        sequences_with_max_distance = self._context.db_service.get_sequences_with_max_distance(distance_function)
        columns = ['sequence', 'aa_src', 'aa_dst', 'aa_src', *self._args.distance_functions]

        return sequences_with_max_distance[columns]
