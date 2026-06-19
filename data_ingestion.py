import logging
import time
from module.argument_parser import argument_parser
from module.pipeline import DataIngestionPipeline


def main():
    parameters = argument_parser('data_ingestion')
    pipeline = DataIngestionPipeline(parameters)
    pipeline.execute()


if __name__ == '__main__':
    try:
        start_time = time.time()
        main()
        final_time = time.time()
        logging.getLogger('logger').info(
            f"Ingestion data execution time in: {str(final_time - start_time)} seconds")

    except Exception as e:
        print(e)
        logging.getLogger('logger').critical(e)
        quit()
