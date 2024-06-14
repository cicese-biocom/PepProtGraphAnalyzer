import os
import json
import numpy as np


def get_intervals_per_distance_function(intervals_per_distance_function_json_path):
    intervals_per_distance_function_json = open_json(intervals_per_distance_function_json_path)

    intervals_per_distance_function = intervals_per_distance_function_json["intervals_per_distance_function"]

    intervals_list = []
    for distance_function_data in intervals_per_distance_function:
        distance_function_name = distance_function_data['distance_function']
        intervals = distance_function_data['intervals']

        for interval in intervals:
            min_value = interval['min']
            max_value = float('inf') if interval["max"] is None else interval["max"]

            data = {'distance_function': distance_function_name,
                    'interval': (min_value, max_value)}

            intervals_list.append(data)

    return intervals_list


def open_json(json_path):
    """
    Opens a JSON file and loads its content into a Python dictionary.

    Args:
    - json_path (str): The path to the JSON file.

    Returns:
    - dict: The content of the JSON file as a dictionary.
    """
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"File '{json_path}' not found.")

    with open(json_path, 'r') as json_file:
        data = json.load(json_file)

    return data


