import logging

import networkx as nx
from pymongo import MongoClient, errors
from utils.json_parser import load_json


class MongoDBConnector:
    def __init__(self, **kwargs):
        username = kwargs.get("username")
        password = kwargs.get("password")
        server = kwargs.get("server")
        port = kwargs.get("port", 27017)
        database = kwargs.get("database")

        connector = f"mongodb://{username}:{password}@{server}:{port}"
        client = MongoClient(connector)
        self._database = client[database]

    @property
    def database(self):
        return self._database


class PepProtGraphDatabase:
    def __init__(self, database_setting_json):
        database_setting = load_json(database_setting_json)
        database_connection_str = database_setting['mongodb_settings']['connection']
        client = MongoDBConnector(**database_connection_str).database
        self.distance_based_graph_collection = client['distance_based_graph']
        
    def insert_distance_based_graphs(self, graphs):
        self.distance_based_graph_collection.insert_many(graphs)

    def get_all_distance_based_graphs(self):
        self.distance_based_graph_collection.find({})

    def is_exist_graph(self, graph):
        return self.distance_based_graph_collection.find_one(graph) is not None

    def is_exist_sequence(self, sequence):
        return self.distance_based_graph_collection.find_one({'graph.sequence': sequence}) is not None

    def insert_graphs(self, graphs):
        self.distance_based_graph_collection.insert_many(graphs)

    def delete_graphs(self):
        self.distance_based_graph_collection.delete_many({})

    def insert_graphs_old(self, graphs):
        for graph in graphs:
            try:
                self.distance_based_graph_collection.insert_one(graph)
            except errors.DuplicateKeyError:
                continue

    def get_distance_functions(self, sequence, tertiary_structure_method):
        try:
            pipeline = [
                MongoDBPipelineStages().match_sequence([sequence],
                                                       tertiary_structure_method),
                MongoDBPipelineStages().project_distance_functions(),
            ]

            result = list(self.distance_based_graph_collection.aggregate(pipeline))

            if result:
                sequence_distance_functions = result[0]['distance_functions']
            else:
                sequence_distance_functions = []

            return sequence_distance_functions

        except Exception as e:
            logging.getLogger('workflow_logger').info(f"Error retrieving distance functions: {e}")
            quit()

        except Exception as e:
            logging.getLogger('workflow_logger').info(f"Error retrieving distance functions: {e}")
            quit()

    def get_inter_amino_acid_distances(self, sequences, tertiary_structure_method, distance_functions):
        """Retrieve inter-amino acid distances for given sequences."""
        try:
            pipeline = [
                MongoDBPipelineStages().match_sequence(sequences, tertiary_structure_method),
                MongoDBPipelineStages().group_weight_by_distance_function(distance_functions),
                MongoDBPipelineStages().project_distance_values(),
            ]

            result = list(self.distance_based_graph_collection.aggregate(pipeline))

            if result:
                return result
            else:
                return []

        except Exception as e:
            logging.getLogger('workflow_logger').info(f"Error retrieving distance functions: {e}")
            quit()

    def get_graphs_based_distance_threshold(self, sequences, tertiary_structure_method, distance_function,
                                           distance_threshold):
        try:
            pipeline = [
                MongoDBPipelineStages().match_sequence(sequences, tertiary_structure_method),
                MongoDBPipelineStages().project_edges_filtered_by_distance_threshold(distance_function,
                                                                                     distance_threshold),
                MongoDBPipelineStages().project_graph_by_distance_threshold(distance_function),
            ]

            result = list(self.distance_based_graph_collection.aggregate(pipeline))

            if result:
                return result
            else:
                return []

        except Exception as e:
            logging.getLogger('workflow_logger').info(f"Error retrieving the graph: {e}")
            quit()


class MongoDBPipelineStages:
    @staticmethod
    def match_sequence(sequence, tertiary_structure_method):
        return {
            '$match': {
                'graph.sequence': {
                    '$in': sequence
                },
                'graph.tertiary_structure_method': tertiary_structure_method
            }
        }

    @staticmethod
    def group_weight_by_distance_function(distance_functions):
        return {
            '$group': {
                '_id': '$graph.distance_function',
                'distance_value': {
                    '$push': f'$links.{distance_functions}'
                }
            }
        }

    @staticmethod
    def project_distance_values():
        return {
            '$project': {
                '_id': 0,
                'distance_values': {
                    '$reduce': {
                        'input': '$distance_value',
                        'initialValue': [],
                        'in': {
                            '$concatArrays': [
                                '$$value', '$$this'
                            ]
                        }
                    }
                }
            }
        }

    @staticmethod
    def project_distance_functions():
        return {
            '$project': {
                '_id': 0,
                "distance_functions": "$graph.distance_functions"
                }
        }

    @staticmethod
    def project_weight_per_distance_function():
        return {
            '$project': {
                '_id': 0,
                'distance_function': '$_id',
                'weights': {
                    '$reduce': {
                        'input': '$all_weights',
                        'initialValue': [],
                        'in': {
                            '$concatArrays': [
                                '$$value', '$$this'
                            ]
                        }
                    }
                }
            }
        }

    @staticmethod
    def project_edges_filtered_by_distance_threshold(distance_function, distance_threshold):
        return {
            '$project': {
                '_id': 0,
                'directed': 1,
                'multigraph': 1,
                'graph': 1,
                'nodes': 1,
                'links': {
                    '$filter': {
                        'input': '$links',
                        'as': 'link',
                        'cond': {
                            '$lt': [
                                f'$$link.{distance_function}', distance_threshold
                            ]
                        }
                    }
                }
            }
        }

    @staticmethod
    def project_graph_by_distance_threshold(distance_function):
        return {
            '$project': {
                '_id': 0,
                'directed': 1,
                'multigraph': 1,
                'graph': 1,
                'nodes': 1,
                'links': {
                    '$map': {
                        'input': '$links',
                        'as': 'link',
                        'in': {
                            'source': '$$link.source',
                            'target': '$$link.target',
                            'weight': f'$$link.{distance_function}'
                        }
                    }
                }
            }
        }


if __name__ == "__main__":
    graph_database = PepProtGraphDatabase('../settings/database_setting.json')

    tertiary_structure_method = None
    distance_function = "euclidean"
    distance_threshold = 15
    sequence = 'GLFDIIKNIFSGL'

    graph_database.delete_graphs()

    graphs = graph_database.get_distance_based_graphs(sequence, tertiary_structure_method, distance_function,
                                                      distance_threshold)

    for graph in graphs:
        weight_matrix = nx.to_numpy_array(graph)
