import logging
import time
from module.argument_parser import argument_parser
from module.pipeline import GraphAnalyzerPipeline


def main():
    parameters = argument_parser('graph_analyzer')
    pipeline = GraphAnalyzerPipeline(parameters)
    pipeline.execute()


if __name__ == '__main__':
    try:
        start_time = time.time()
        main()
        final_time = time.time()
        logging.getLogger('logger').info(
            f"Graph analyzer execution time in: {str(final_time - start_time)} seconds")

    except Exception as e:
        print(e)
        logging.getLogger('workflow_logger').critical(e)
        quit()
