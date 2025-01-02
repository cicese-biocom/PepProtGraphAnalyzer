import logging
from modules.argument_parser import argument_parser
from modules.pipeline import GraphAnalyzerPipeline


def main():
    parameters = argument_parser('graph_analyzer')
    pipeline = GraphAnalyzerPipeline(parameters)
    pipeline.execute()


if __name__ == '__main__':
    try:
        main()

    except Exception as e:
        print(e)
        logging.getLogger('workflow_logger').critical(e)
        quit()
