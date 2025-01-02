from injector import Injector
from modules.data_validator import DataValidatorContext, SequenceValidator
from modules.data_loader import DataLoaderContext, CSVLoader


class ApplicationContext:
    def __init__(self):
        self.__injector = Injector()

        self.__injector.binder.bind(DataLoaderContext, CSVLoader)
        self.__injector.binder.bind(DataValidatorContext, SequenceValidator)

        self.__data_validator = self.__injector.get(DataValidatorContext)
        self.__data_loader = self.__injector.get(DataLoaderContext)

    @property
    def path_creator(self):
        return self.__path_creator

    @property
    def data_validator(self):
        return self.__data_validator

    @property
    def data_loader(self):
        return self.__data_loader
