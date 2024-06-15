import time
from pathlib import Path
from graph.graph_analysis_module import GraphAnalysisModule
from utils.application_context import ApplicationContext
from utils.args_parser_handler import ArgsParserHandler


def graph_analyzer(args):
    try:
        context = ApplicationContext()
        GraphAnalysisModule().execute(context=context, parameters=args)

    except Exception as e:
        raise


if __name__ == '__main__':
    args_handler = ArgsParserHandler()
    args = args_handler.get_graph_analyzer_arguments()

    """""
    args['dataset'] = Path('example/ExampleDataset.csv')
    args['pdb_path'] = Path('example/ESMFold_pdbs/')
    args['tertiary_structure_method'] = 'esmfold'
    args['amino_acid_representation'] = 'CA'
    args['predict_tertiary_structure'] = False
    args['output_path'] = Path('output/example/')
    args['batch_size'] = 56
    args['distance_intervals_json_path'] = Path('datasets/json/distance_intervals.json')
    """""

    start_time = time.time()
    graph_analyzer(args)
    final_time = time.time()
    print(
        f"Execution time: {str(final_time - start_time)} seconds"
    )
