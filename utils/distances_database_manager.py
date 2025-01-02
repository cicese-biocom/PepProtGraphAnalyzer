import pandas as pd
from dask.dataframe import dd


# repartition data
def _repartition_data(data, partition_size):
    total_size = data.memory_usage(deep=True).sum().compute()
    desired_partition_size = partition_size * 1e6  # 200 MB
    optimal_partitions = max(1, int(total_size / desired_partition_size))
    data = data.repartition(npartitions=optimal_partitions)
    data = data.persist()
    return data


def _load_data(database_path, columns=None, filters=None):
    data = dd.read_parquet(database_path, columns=columns, filters=filters)
    data = _repartition_data(data, 100)
    return data


# load and pivot the data data
def get_and_pivot_distances(database_path, distance_functions, sequence=None):
    filters = None
    if sequence is not None:
        filters = [('sequence', '==', sequence)]

    data = _load_data(database_path, distance_functions, filters)
    data = data.melt(var_name="distance_function", value_name="value")

    chunks = [chunk.compute() for chunk in data.to_delayed()]
    result = pd.concat(chunks, ignore_index=True)

    return result


# load data
def get_distances(database_path, distance_functions, sequence=None):
    filters = None
    if sequence is not None:
        filters = [('sequence', '==', sequence)]

    data = _load_data(database_path, distance_functions, filters)
    return data.compute()


# get sequence with max distance
def get_data_with_max_distance(database_path, distance_function):
    data = _load_data(database_path)

    max_distance = data[distance_function].max().compute()
    data_max_distance = data[data[distance_function] == max_distance].compute()
    return data_max_distance
