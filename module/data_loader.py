from abc import abstractmethod
from typing import List
import pandas as pd


class DataLoader:
    @abstractmethod
    def read_file(self, **kwargs):
        pass


class CSVLoader(DataLoader):
    def read_file(self, **kwargs) -> List:
        return pd.read_csv(kwargs.get('filepath'))


class CSVByChunkLoader(DataLoader):
    def read_file(self, **kwargs) -> pd.DataFrame:
        for data_chunk in pd.read_csv(kwargs.get('dataset'), chunksize=kwargs.get('batch_size')):
            yield data_chunk


class DataLoaderContext:
    def __init__(self, data_loader: DataLoader) -> None:
        self._data_loader = data_loader

    def read_file(self, **kwargs) -> pd.DataFrame:
        return self._data_loader.read_file(**kwargs)
