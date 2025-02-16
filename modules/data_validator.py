from typing import Dict, Optional, Any
import pandas as pd
import re
from abc import ABC, abstractmethod
import logging

pattern = re.compile('[^ARNDCQEGHILKMFPSTWYV]')


class DataValidator(ABC):
    @abstractmethod
    def validate(self, **kwargs):
        pass


class SequenceValidator(DataValidator):
    def validate(self, **kwargs):
        try:
            data: pd.DataFrame = kwargs.get('data')
            output_paths: Dict = kwargs.get('output_paths')

            if data.empty:
                raise Exception(f"No data")

            data = self.validate_columns(data)
            data = self.check_duplicated_sequence_ids(data, output_paths)
            data = self.check_duplicated_sequences(data, output_paths)
            data = self.filter_sequences_with_non_natural_amino_acids(data, output_paths)

            if data.empty:
                raise Exception(f"Invalid data")

            return data

        except Exception as e:
            logging.getLogger('logger').exception(e)
            raise

    def validate_columns(self, data: pd.DataFrame):
        required_columns = ['id', 'sequence']

        missing_columns = set(required_columns) - set(data.columns)

        if missing_columns:
            raise Exception(f"The following columns are missing: {missing_columns}")

        return data[required_columns]

    def check_duplicated_sequence_ids(self, data: pd.DataFrame, output_paths: Dict) -> pd.DataFrame:
        csv_file = output_paths['duplicated_sequence_ids_file']
        sequences_to_exclude = data[data.duplicated(subset='id', keep=False)]

        if not sequences_to_exclude.empty:
            sequences_to_exclude.sort_values(by='id')
            sequences_to_exclude.to_csv(csv_file, index=False)
            raise ValueError(f"Duplicate sequences IDs. See: {csv_file}")
        return data

    def check_duplicated_sequences(self, data: pd.DataFrame, output_paths: Dict) -> pd.DataFrame:
        csv_file = output_paths['duplicated_sequences_file']
        sequences_to_exclude = data[data.duplicated(subset='sequence', keep=False)]

        if not sequences_to_exclude.empty:
            data = data.drop(sequences_to_exclude.index)

            sequences_to_exclude.sort_values(by='sequence')
            sequences_to_exclude.to_csv(csv_file, index=False)

            logging.getLogger('logger'). \
                warning(f"Duplicate sequences. See: {csv_file}")

        return data

    def not_sequences_with_non_natural_amino_acids(self, sequence):
        return pattern.search(sequence) is not None

    def filter_sequences_with_non_natural_amino_acids(self, data: pd.DataFrame, output_paths: Dict) -> pd.DataFrame:
        csv_file = output_paths['sequences_with_non_natural_amino_acids_file']
        sequences_to_exclude_mask = data['sequence'].apply(self.not_sequences_with_non_natural_amino_acids)
        sequences_to_exclude = data[sequences_to_exclude_mask]

        if not sequences_to_exclude.empty:
            data = data.drop(sequences_to_exclude.index)

            sequences_to_exclude.to_csv(csv_file, index=False)

            logging.getLogger('logger'). \
                warning(f"Sequences with non-natural amino acids were excluded. See: {csv_file}")

        return data


class DataValidatorContext:
    def __init__(self, data_validator: DataValidator) -> None:
        self._data_validator = data_validator

    def validate(self, **kwargs):
        return self._data_validator.validate(**kwargs)
