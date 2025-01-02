import logging
import time
from modules.argument_parser import argument_parser
from modules.pipeline import DataIngestionPipeline


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
            f"Inference execution time in: {str(final_time - start_time)} seconds")

    except Exception as e:
        print(e)
        logging.getLogger('logger').critical(e)
        quit()
