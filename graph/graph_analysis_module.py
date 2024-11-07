import itertools
import logging
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Dict
import networkx as nx
import numpy as np
import pandas as pd
from tqdm import tqdm
from graph.construct_graph import construct_distance_based_graph
from utils.application_context import ApplicationContext
from utils.batch import batch
from utils.csv_parser import add_to_csv
from utils.data_loader import DataLoaderContext
from utils.database_handler import PepProtGraphDatabase
from utils.dataset_validator import DatasetValidatorContext
from utils.json_parser import get_distance_intervals
from utils.logging_handler import LoggingHandler
from utils.path_creator import PathCreatorContext
from utils.similarity import eigenvalues, cosine_similarity


class GraphAnalysisModule:
    def execute(self, context: ApplicationContext, parameters: Dict) -> None:
        # Step 1: Create output path
        output_path = parameters.get('output_path')
        output_setting = self.create_path(context.path_creator, output_path)

        # Step 2: Initialize logger
        logger_settings_path = output_setting['log_file']
        self.initialize_logger(logger_settings_path)

        # Step 3: Load dataset
        dataset = parameters.get('dataset')
        data = self.load_data(dataset, output_setting, context.data_loader, context.dataset_validator)

        # Step 4: Filter data
        minimum_sequence_length = parameters.get('minimum_sequence_length')
        maximum_sequence_length = parameters.get('maximum_sequence_length')
        data = self.filter_data_by_sequence_length(data, minimum_sequence_length, maximum_sequence_length)

        # Step 5: Initialize database
        graph_database = self.initialize_database()

        # Step 6: Load intervals
        distance_intervals_json_path = parameters.get('distance_intervals_json_path')
        distance_intervals = get_distance_intervals(distance_intervals_json_path)

        # Step 7: Construct distance based graph
        pdb_path = parameters.get('pdb_path')
        batch_size = parameters.get('batch_size')
        tertiary_structure_method = parameters.get('tertiary_structure_method')
        amino_acid_representation = parameters.get('amino_acid_representation')
        predict_tertiary_structure = parameters.get('predict_tertiary_structure')
        args = (data, graph_database, output_setting, predict_tertiary_structure, tertiary_structure_method,
                amino_acid_representation, pdb_path, batch_size, distance_intervals)
        construct_distance_based_graph(args)

        # Step 9: Inter amino acid distances
        args = (data, graph_database, output_setting, tertiary_structure_method, distance_intervals)
        self.inter_amino_acid_distances(args)

        # Step 10: Get graphs based distance threshold
        args = (data, graph_database, tertiary_structure_method, distance_intervals, output_setting)
        graph_information = self.get_graphs_information(args)

        # Step 12: Drop empty graph
       # args = (graph_information, output_setting)
       # graph_information = self.drop_empty_graph(args)

        # Step 12: Get graphs similarity
        args = (graph_information, distance_intervals, output_setting)
        self.get_graphs_similarity(args)

    def create_path(self, path_creator_context: PathCreatorContext, output_path):
        return path_creator_context.create_path(output_path)

    def initialize_logger(self, log_output_path: Path):
        LoggingHandler.initialize_logger(logger_settings_path=Path('settings').joinpath('logger_setting.json'),
                                         log_output_path=log_output_path)

    def load_data(self, dataset: Path, output_setting: Dict, data_loader: DataLoaderContext,
                  dataset_validator: DatasetValidatorContext) -> pd.DataFrame:
        data = data_loader.read_file(filepath=dataset)
        data = dataset_validator.processing_dataset(dataset=data,
                                                    output_setting=output_setting)
        return data

    def filter_data_by_sequence_length(self, data, minimum_sequence_length, maximum_sequence_length):
        data = data[(data['length'] >= minimum_sequence_length) & (data['length'] <= maximum_sequence_length)]
        return data

    def initialize_database(self):
        graph_database = PepProtGraphDatabase('settings/database_setting.json')
        return graph_database

    def inter_amino_acid_distances(self, args):
        try:
            data, graph_database, output_setting, tertiary_structure_method, distance_intervals = args
            distance_functions = list({interval['distance_function'] for interval in distance_intervals})

            sequences = list(data['sequence'])
            batch_size = 100
            csv_path = output_setting['inter_amino_acid_distances']

            with tqdm(range(len(sequences)), total=len(sequences),
                      desc="Generating inter-amino acid distances") as progress:
                for sequences_batch in batch(sequences, batch_size):
                    for distance_function in distance_functions:
                        results = graph_database.get_inter_amino_acid_distances(sequences_batch,
                                                                                tertiary_structure_method,
                                                                                distance_function)
                        for result in results:
                            distance_values = result['distance_values']
                            filename = f"{csv_path}-{distance_function}.csv"
                            add_to_csv(distance_values, filename)

                    progress.update(len(sequences_batch))
        except Exception as e:
            raise

    def get_graphs_information(self, args):
        try:
            data, graph_database, tertiary_structure_method, distance_intervals, output_setting = args

            sequences = list(data['sequence'])
            batch_size = 100

            rows = []
            with tqdm(range(len(sequences)), total=len(sequences), desc="Generating graph information") as progress:
                for sequences_batch in batch(sequences, batch_size):
                    for interval in distance_intervals:
                        distance_function = interval['distance_function']
                        min_interval = interval['interval'][0]
                        max_interval = interval['interval'][1]

                        graphs = graph_database.get_graphs_based_distance_threshold(sequences_batch,
                                                                                    tertiary_structure_method,
                                                                                    distance_function,
                                                                                    max_interval)
                        for graph in graphs:
                            nx_graph = nx.node_link_graph(graph)
                            sequence = nx_graph.graph['sequence']
                            adjacency_matrix = nx.to_numpy_array(nx_graph, weight=None)
                            eigen_values = eigenvalues(adjacency_matrix)
                            eigen_values = [f'{value:.16f}' for value in eigen_values]
                            number_of_nodes = nx.number_of_nodes(nx_graph)
                            number_of_edges = nx.number_of_edges(nx_graph)
                            density = nx.density(nx_graph)

                            row = [
                                sequence,
                                distance_function,
                                min_interval,
                                max_interval,
                                number_of_nodes,
                                number_of_edges,
                                density,
                                eigen_values
                            ]

                            rows.append(row)

                    progress.update(len(sequences_batch))

            csv_path = output_setting['graph_information']
            filename = f"{csv_path}"
            graph_information = pd.DataFrame(rows, columns=['sequence', 'distance_function', 'min_interval',
                                                            'max_interval', 'number_of_nodes', 'number_of_edges',
                                                            'density', 'eigenvalues'])
            graph_information.to_csv(filename, index=False)
            return graph_information
        except Exception as e:
            raise

    def drop_empty_graph(self, args):
        graph_information, output_setting = args

        csv_file = output_setting['non_analyzed_graph']
        sequence_df = graph_information.copy()
        sequences_to_exclude = sequence_df[sequence_df['number_of_edges'] == 0]

        if not sequences_to_exclude.empty:
            sequences_to_exclude.to_csv(csv_file, index=False)
            sequence_df = sequence_df.drop(sequences_to_exclude.index)
            logging.getLogger('workflow_logger'). \
                warning(f"Sequences that generate empty graphs. See: {csv_file}")
        return sequence_df

    def get_graphs_similarity(self, args):
        try:
            graph_information, distance_intervals, output_setting = args

            combinations_columns = list(itertools.combinations(distance_intervals, 2))

            similarity_args = []
            distance_interval_str = []
            for interval1, interval2 in combinations_columns:
                eigenvalues_1, interval_str_1 = get_eigenvalues_and_interval_str(graph_information, interval1)
                eigenvalues_2, interval_str_2 = get_eigenvalues_and_interval_str(graph_information, interval2)

                distance_interval_str.append((interval_str_1, interval_str_2))
                similarity_args.append((eigenvalues_1, eigenvalues_2))

            num_cores = multiprocessing.cpu_count()

            with tqdm(total=len(similarity_args), desc="Calculating graph similarity") as progress:
                with ProcessPoolExecutor(max_workers=num_cores) as pool:
                    futures = []
                    for arg in similarity_args:
                        future = pool.submit(compute_similarity, arg)
                        future.add_done_callback(lambda p: progress.update())
                        futures.append(future)

                    similarity_results = [future.result() for future in futures]

            rows = []
            similarities_df = pd.DataFrame()
            for (distance_interval_name_1, distance_interval_name_2), (
                    similarities, avg_similarity, min_similarity, max_similarity) in zip(distance_interval_str,
                                                                                         similarity_results):
                rows.append({
                    'distance_interval_1': distance_interval_name_1,
                    'distance_interval_2': distance_interval_name_2,
                    'average_similarity': avg_similarity,
                    'minimum_similarity': min_similarity,
                    'maximum_similarity': max_similarity
                })

                column_name = f'{distance_interval_name_1}_{distance_interval_name_2}'
                new_column_df = pd.DataFrame({column_name: similarities})
                similarities_df = pd.concat([similarities_df, new_column_df], axis=1)

            csv_path = output_setting['graph_similarity_summary']
            filename = f"{csv_path}"
            graph_similarity = pd.DataFrame(rows, columns=['distance_interval_1',
                                                           'distance_interval_2',
                                                           'average_similarity',
                                                           'minimum_similarity',
                                                           'maximum_similarity'])
            graph_similarity.to_csv(filename, index=False)

            csv_path = output_setting['graph_similarity']
            filename = f"{csv_path}"
            similarities_df.to_csv(filename, index=False)

            return graph_similarity

        except Exception as e:
            raise


def compute_similarity(args):
    eigenvalues1, eigenvalues2 = args
    try:
        similarities, avg_similarity, min_similarity, max_similarity = cosine_similarity(eigenvalues1, eigenvalues2)
        return similarities, avg_similarity, min_similarity, max_similarity
    except ValueError as e:
        print("Error:", e)
        return [], np.nan, np.nan, np.nan


def get_eigenvalues_and_interval_str(graph_information, interval):
    distance_function = interval['distance_function']
    distance_interval = interval['interval']

    filtered = graph_information[(graph_information['distance_function'] == distance_function) & (
            graph_information['min_interval'] == distance_interval[0]) & (
                                         graph_information['max_interval'] == distance_interval[1])]

    eigenvalues = filtered.sort_values(by='number_of_nodes', ascending=False, ignore_index=True)['eigenvalues']
    eigenvalues = eigenvalues.apply(convert_to_numpy)

    interval_str = f"{distance_function}{distance_interval}"

    return eigenvalues, interval_str


def convert_to_numpy(eigenvalue_str):
    return np.array([float(val) for val in eigenvalue_str])
