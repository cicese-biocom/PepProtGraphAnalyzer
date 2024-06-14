import json
from pathlib import Path
from typing import Dict


def load_json(json_file: Path) -> Dict:
    with open(json_file, 'r') as file:
        return json.load(file)


def save_json(json_file: Path, json_data: Dict) -> None:
    with open(json_file, 'w') as file:
        json.dump(json_data, file, indent=4)


def get_distance_intervals(distance_intervals_json_path):
    distance_intervals_json = load_json(distance_intervals_json_path)

    distance_intervals = distance_intervals_json["distance_intervals"]

    intervals_list = []
    for distance_function_data in distance_intervals:
        distance_function_name = distance_function_data['distance_function']
        intervals = distance_function_data['intervals']

        for interval in intervals:
            min_value = interval['min']
            max_value = float('inf') if interval["max"] is None else interval["max"]

            data = {'distance_function': distance_function_name,
                    'interval': (min_value, max_value)}

            intervals_list.append(data)

    return intervals_list


def get_distance_threshold(distance_threshold_json_path):
    distance_threshold_json = load_json(distance_threshold_json_path)
    return distance_threshold_json["distance_thresholds"]
