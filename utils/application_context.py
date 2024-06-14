from injector import Binder, Module, Injector, singleton

from utils.data_loader import DataLoaderContext, CSVLoader
from utils.dataset_validator import DatasetValidatorContext, LabeledDatasetValidator, DatasetValidator
from utils.path_creator import GraphAnalysisModePathCreator, PathCreatorContext


class ApplicationContext:
    def __init__(self):
        self.__injector = Injector()

        self.__injector.binder.bind(DataLoaderContext, CSVLoader)
        self.__injector.binder.bind(DatasetValidatorContext, DatasetValidator)
        self.__injector.binder.bind(PathCreatorContext, GraphAnalysisModePathCreator)

        self.__path_creator = self.__injector.get(PathCreatorContext)
        self.__dataset_validator = self.__injector.get(DatasetValidatorContext)
        self.__data_loader = self.__injector.get(DataLoaderContext)

    @property
    def path_creator(self):
        return self.__path_creator

    @property
    def dataset_validator(self):
        return self.__dataset_validator

    @property
    def data_loader(self):
        return self.__data_loader





