import json
import os
from datetime import datetime
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


def output_config(**kwargs):
    output_path = kwargs.get('output_path')
    mode = kwargs.get('mode')
    mode_path_name = kwargs.get('mode_path_name')

    # create output path
    current_time = datetime.now().replace(microsecond=0).isoformat().replace(':', '.')

    if not mode_path_name:
        output_path = output_path.joinpath(f"{current_time}")
    elif mode != 'notebook':
        output_path = output_path.joinpath(f"{current_time}-{mode_path_name}")

    output_path.mkdir(parents=True, exist_ok=True)

    # load output path setting
    base_path = os.getenv("FRAMEWORK_PATH")
    settings_file = os.path.join(base_path, "setting/output_config.json")

    if not settings_file:
        raise ValueError("Missing 'FRAMEWORK_PATH' environment variable in the .env file.")

    settings_file = Path(settings_file).resolve()

    data = load_json(settings_file)

    # create output file paths
    paths = {}
    for setting in data["output_settings"]:
        if mode in setting["modes"]:
            paths[setting["key"]] = output_path.joinpath(setting["name"])
            paths[setting["key"]].mkdir(parents=True, exist_ok=True)

            for file in setting.get("files", []):
                paths[file["key"]] = paths[setting["key"]].joinpath(file["name"])
    return paths


def input_config(input_path, mode):
    base_path = os.getenv("FRAMEWORK_PATH")
    settings_file = os.path.join(base_path, "setting/output_config.json")

    if not settings_file:
        raise ValueError("Missing 'FRAMEWORK_PATH' environment variable in the .env file.")

    settings_file = Path(settings_file).resolve()

    data = load_json(settings_file)

    # create output file paths
    paths = {}
    for setting in data["output_settings"]:
        if setting["key"] != 'log_path':
            paths[setting["key"]] = input_path.joinpath(setting["name"])

            for file in setting.get("files", []):
                paths[file["key"]] = paths[setting["key"]].joinpath(file["name"])
    return paths
