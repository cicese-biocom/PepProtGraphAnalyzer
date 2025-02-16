import logging
from modules.argument_parser import argument_parser
from modules.pipeline import SequenceAnalyzerPipeline


def main():
    parameters = argument_parser('sequence_analyzer')
    pipeline = SequenceAnalyzerPipeline(parameters)
    pipeline.execute()


if __name__ == '__main__':
    try:
        main()

    except Exception as e:
        logging.getLogger('workflow_logger').critical(e)
        quit()
