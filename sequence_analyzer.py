import logging
import time
from module.argument_parser import argument_parser
from module.pipeline import SequenceAnalyzerPipeline


def main():
    parameters = argument_parser('sequence_analyzer')
    pipeline = SequenceAnalyzerPipeline(parameters)
    pipeline.execute()


if __name__ == '__main__':
    try:
        start_time = time.time()
        main()
        final_time = time.time()
        logging.getLogger('logger').info(
            f"Sequence analyzer execution time in: {str(final_time - start_time)} seconds")

    except Exception as e:
        logging.getLogger('workflow_logger').critical(e)
        quit()
