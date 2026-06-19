from injector import Injector
from module.data_validator import DataValidatorContext, SequenceValidator
from module.data_loader import DataLoaderContext, CSVLoader
from module.db_manager import DBServiceContext, IngestionService, GraphAnalysisService, SequenceAnalysisService, NotebookDBService


class ApplicationContext:
    def __init__(self, **kwargs):

        self.__injector = Injector()

        self.__injector.binder.bind(DataLoaderContext, CSVLoader)
        self.__injector.binder.bind(DataValidatorContext, SequenceValidator)

        self.__data_validator = self.__injector.get(DataValidatorContext)
        self.__data_loader = self.__injector.get(DataLoaderContext)

        if kwargs.get('mode') == 'data_ingestion':
            self.__injector.binder.bind(DBServiceContext, IngestionService(**kwargs))
        if kwargs.get('mode') == 'sequence_analyzer':
            self.__injector.binder.bind(DBServiceContext, SequenceAnalysisService(**kwargs))
        if kwargs.get('mode') == 'graph_analyzer':
            self.__injector.binder.bind(DBServiceContext, GraphAnalysisService(**kwargs))
        if kwargs.get('mode') == 'notebook':
            self.__injector.binder.bind(DBServiceContext, NotebookDBService(**kwargs))

        self.__db_service = self.__injector.get(DBServiceContext)

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
    def db_service(self):
        return self.__db_service
