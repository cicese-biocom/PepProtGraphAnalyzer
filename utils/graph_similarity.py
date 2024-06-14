import itertools
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import pandas as pd
from tqdm import tqdm
from utils.similarity import cosine_similarity


def get_graphs_similarity(graph_information):
    try:
        distance_intervals = graph_information[
            ['distance_function', 'min_interval', 'max_interval']].drop_duplicates().to_dict(orient='records')

        combinations_columns = list(itertools.combinations(distance_intervals, 2))

        similarity_args = []
        distance_interval_names = []
        for interval1, interval2 in combinations_columns:
            distance_function_1 = interval1['distance_function']
            min_interval_1 = interval1['min_interval']
            max_interval_1 = interval1['max_interval']

            distance_function_2 = interval2['distance_function']
            min_interval_2 = interval2['min_interval']
            max_interval_2 = interval2['max_interval']

            filtered_1 = graph_information[(graph_information['distance_function'] == distance_function_1) & (
                        graph_information['min_interval'] == min_interval_1) & (
                                                       graph_information['max_interval'] == max_interval_1)]

            filtered_2 = graph_information[(graph_information['distance_function'] == distance_function_2) & (
                    graph_information['min_interval'] == min_interval_2) & (
                                                   graph_information['max_interval'] == max_interval_2)]

            distance_interval_name_1 = f"{distance_function_1}({min_interval_1},{max_interval_1})"
            distance_interval_name_2 = f"{distance_function_2}({min_interval_2},{max_interval_2})"

            eigenvalues_1 = filtered_1.sort_values(by='number_of_nodes', ascending=False, ignore_index=True)[
                'eigenvalues']

            eigenvalues_2 = filtered_2.sort_values(by='number_of_nodes', ascending=False, ignore_index=True)[
                'eigenvalues']

            eigenvalues_1 = eigenvalues_1.apply(convert_to_numpy)
            eigenvalues_2 = eigenvalues_2.apply(convert_to_numpy)

            distance_interval_names.append((distance_interval_name_1, distance_interval_name_2))
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

        graph_similarity_list = []
        for (distance_interval_name_1, distance_interval_name_2), (
                avg_similarity, min_similarity, max_similarity) in zip(distance_interval_names, similarity_results):
            graph_similarity_list.append({
                'distance_interval_1': distance_interval_name_1,
                'distance_interval_2': distance_interval_name_2,
                'average_similarity': avg_similarity,
                'minimum_similarity': min_similarity,
                'maximum_similarity': max_similarity
            })

        return pd.DataFrame(graph_similarity_list, columns=['distance_interval_1',
                                                            'distance_interval_2',
                                                            'average_similarity',
                                                            'minimum_similarity',
                                                            'maximum_similarity'])
    except Exception as e:
        raise


def compute_similarity(args):
    eigenvalues1, eigenvalues2 = args
    try:
        avg_similarity, min_similarity, max_similarity = cosine_similarity(eigenvalues1, eigenvalues2)
        return avg_similarity, min_similarity, max_similarity
    except ValueError as e:
        print("Error:", e)
        return np.nan, np.nan, np.nan


def convert_to_numpy(eigenvalue_str):
    eigenvalue_str = eigenvalue_str.strip("[]")
    eigenvalue_str = eigenvalue_str.replace("'", "").split(', ')
    return np.array([float(val) for val in eigenvalue_str])
