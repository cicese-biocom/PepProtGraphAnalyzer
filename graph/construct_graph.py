import logging
import networkx as nx
import pandas as pd
from tqdm import tqdm
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from threading import Thread
from utils.batch import batch
from utils.distances import distance
from .tertiary_structure_handler import predict_tertiary_structures, load_tertiary_structures


def construct_distance_based_graph(args):
    data, graph_database, output_setting, predict_tertiary_structure, tertiary_structure_method, amino_acid_representation, pdb_path, batch_size, distance_intervals = args
    distance_functions = list({interval['distance_function'] for interval in distance_intervals})

    data_new = pd.DataFrame(columns=list(data.columns) + ['graph_distance_functions'])
    with tqdm(range(len(data)), total=len(data), desc="Processing graphs to be generated", disable=False) as progress:
        for index, row in data.iterrows():
            sequence_distance_functions = graph_database.get_distance_functions(row['sequence'],
                                                                                tertiary_structure_method)

            distance_functions_diff = list(set(distance_functions) - set(sequence_distance_functions))

            if distance_functions_diff:
                new_row = row.to_dict()
                new_row['distance_functions'] = distance_functions_diff

                data_new = data_new.append(new_row, ignore_index=True)
            progress.update(1)

    if not data_new.empty:
        if predict_tertiary_structure:
            args = (pdb_path, amino_acid_representation, data_new)
            atom_coordinates_matrices = predict_tertiary_structures(args)
        else:
            args = (pdb_path, amino_acid_representation, output_setting, data_new)
            atom_coordinates_matrices, data_new = load_tertiary_structures(args)

        if not data_new.empty:
            args = [
                (row['sequence'], row['distance_functions'], atom_coordinates, tertiary_structure_method)
                for (_, row), atom_coordinates in zip(data_new.iterrows(), atom_coordinates_matrices)
            ]

            num_cores = multiprocessing.cpu_count()

            with tqdm(total=len(args), desc="Generating graphs") as progress:
                for arg_batch in batch(args, batch_size):
                    with ProcessPoolExecutor(max_workers=num_cores) as pool:
                        futures = []
                        for arg in arg_batch:
                            future = pool.submit(get_distance_based_graph, arg)
                            future.add_done_callback(lambda p: progress.update())
                            futures.append(future)

                        nx_graphs = [future.result() for future in futures]

                        thread = Thread(target=graph_database.insert_graphs, args=(nx_graphs,))
                        thread.start()
                        thread.join()

    logging.getLogger('workflow_logger').info(f'{len(data_new)} new graphics will be generated')


def get_distance_based_graph(args):
    sequence, distance_functions, atom_coordinates, tertiary_structure_method = args

    number_of_amino_acid = len(atom_coordinates)

    nx_graph = nx.Graph()
    nx_graph.graph['sequence'] = sequence
    nx_graph.graph['tertiary_structure_method'] = tertiary_structure_method
    nx_graph.graph['distance_functions'] = distance_functions

    for i in range(number_of_amino_acid):
        for j in range(i + 1, number_of_amino_acid):
            edge_data = {}
            for distance_function in distance_functions:
                edge_data[distance_function] = distance(atom_coordinates[i], atom_coordinates[j], distance_function)
            nx_graph.add_edge(i, j, **edge_data)
    return nx.node_link_data(nx_graph)
