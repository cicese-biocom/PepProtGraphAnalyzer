import logging
import networkx as nx
import pandas as pd
from pydantic import BaseModel
from tqdm import tqdm
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from threading import Thread
from _misc.batch import batch
from utils.distances import distance


def construct_distance_based_graph(data: pd.DataFrame, atom_coordinates_matrices, parameters: BaseModel, graph_database):
    args = [
        (row['sequence'], row['distance_functions'], atom_coordinates, parameters.tertiary_structure_method)
        for (_, row), atom_coordinates in zip(data.iterrows(), atom_coordinates_matrices)
    ]

    num_cores = multiprocessing.cpu_count()

    with tqdm(total=len(args), desc="Generating distance-based graphs") as progress:
        for arg_batch in batch(args, parameters.batch_size):
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

    logging.getLogger('logger').info(f'{len(data)} new graphs have been generated')


def get_distance_based_graph(args):
    sequence, distance_functions, atom_coordinates, tertiary_structure_method = args

    number_of_amino_acid = len(atom_coordinates)

    nx_graph = nx.Graph()
    nx_graph.graph['sequence'] = sequence
    nx_graph.graph['tertiary_structure_method'] = tertiary_structure_method

    distances_list = []

    for i in range(number_of_amino_acid):
        for j in range(i + 1, number_of_amino_acid):
            edge_data = {}
            for distance_function in distance_functions:
                distance_value = distance(atom_coordinates[i], atom_coordinates[j], distance_function)
                edge_data[distance_function] = distance_value
            nx_graph.add_edge(i, j, **edge_data)
            distances_list.append({
                'distance_function': distance_function,
                'value': distance_value
            })

    return nx.node_link_data(nx_graph), distances_list
