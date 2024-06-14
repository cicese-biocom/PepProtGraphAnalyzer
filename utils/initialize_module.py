import time
from pathlib import Path
import pandas as pd
from typing import Dict
from utils.data_loader import DataLoaderContext, CSVLoader
from utils.dataset_validator import DatasetValidatorContext, LabeledDatasetValidator
from utils.file_system_handler import create_output_path
from utils.logging_handler import LoggingHandler


def initialize_module(args):
    try:
        dataset, distance_intervals_json_path, output_path = args

        output_setting = create_output_path(output_path)
        initialize_logger(log_output_path=output_setting['log_file'])

        data_loader = DataLoaderContext(CSVLoader())
        dataset_validator = DatasetValidatorContext(LabeledDatasetValidator())
        data = load_data(dataset, output_setting, data_loader, dataset_validator)

        return data, output_setting

    except Exception as e:
        raise

def initialize_logger(log_output_path: Path):
    LoggingHandler.initialize_logger(logger_settings_path=Path('settings').joinpath('logger_setting.json'),
                                     log_output_path=log_output_path)


def load_data(dataset: Path, output_setting: Dict, data_loader: DataLoaderContext,
              dataset_validator: DatasetValidatorContext) -> pd.DataFrame:
    data = data_loader.read_file(filepath=dataset)
    data = dataset_validator.processing_dataset(dataset=data,
                                                output_setting=output_setting)
    return data
