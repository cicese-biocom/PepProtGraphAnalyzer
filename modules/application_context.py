from injector import Injector
from modules.data_validator import DataValidatorContext, SequenceValidator
from modules.data_loader import DataLoaderContext, CSVLoader
from modules.parquet_data_manager import DataManager, DataIngestionManager, DataAnalysisManager


class ApplicationContext:
    def __init__(self, mode):
        self.__injector = Injector()

        self.__injector.binder.bind(DataLoaderContext, CSVLoader)
        self.__injector.binder.bind(DataValidatorContext, SequenceValidator)

        self.__data_validator = self.__injector.get(DataValidatorContext)
        self.__data_loader = self.__injector.get(DataLoaderContext)

        if mode == 'data_ingestion':
            self.__injector.binder.bind(DataManager, DataIngestionManager)
        if mode in ('sequence_analyzer', 'graph_analyzer'):
            self.__injector.binder.bind(DataManager, DataAnalysisManager)

        self.__data_manager = self.__injector.get(DataManager)

    @property
    def path_creator(self):
        return self.__path_creator

    @property
    def data_validator(self):
        return self.__data_validator

    @property
    def data_loader(self):
        return self.__data_loader

    @property
    def data_manager(self):
        return self.__data_manager
