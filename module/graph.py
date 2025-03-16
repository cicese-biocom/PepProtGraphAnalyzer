import networkx as nx
from statistics import mean
import numpy as np
import pandas as pd
from typing import List


class DistanceBasedGraph:
    def __init__(self, sequence_value, distances, distance_function, interval):
        # empty graph
        self._nx_graph = nx.Graph()

        # graph metadata
        self._nx_graph.graph['sequence'] = sequence_value
        self._nx_graph.graph['distance_function'] = distance_function
        self._nx_graph.graph['interval'] = interval

        # add nodes
        self._nx_graph.add_nodes_from(range(len(sequence_value)))

        # add edges
        if not distances.empty:
            self._nx_graph.add_edges_from(zip(distances['aa_src'].values, distances['aa_dst'].values))

    @property
    def nx_graph(self):
        return self._nx_graph

    def get_metadata(self):
        return {
            'sequence': self._nx_graph.graph['sequence'],
            'distance_function': self._nx_graph.graph['distance_function'],
            'interval': self._nx_graph.graph['interval']
        }

    def compute_metrics(self):
        # Check if the graph is connected and has enough nodes for eigenvector centrality
        if nx.is_connected(self._nx_graph) and self._nx_graph.number_of_nodes() > 2:
            try:
                eigenvector_centrality = mean(nx.eigenvector_centrality_numpy(self._nx_graph).values())
            except Exception:
                eigenvector_centrality = np.nan  # Handle exceptions gracefully
        else:
            eigenvector_centrality = np.nan  # Assign NaN if the graph is disconnected or too small

        return {
            'sequence': self._nx_graph.graph['sequence'],
            'distance_function': self._nx_graph.graph['distance_function'],
            'interval': self._nx_graph.graph['interval'],
            'number_of_nodes': self._nx_graph.number_of_nodes(),
            'number_of_edges': self._nx_graph.number_of_edges(),
            'density': nx.density(self._nx_graph),
            'degree_centrality': mean(
                nx.degree_centrality(self._nx_graph).values()) if self._nx_graph.number_of_nodes() > 1 else np.nan,
            'eigenvector_centrality': eigenvector_centrality,
            'closeness_centrality': mean(
                nx.closeness_centrality(self._nx_graph).values()) if self._nx_graph.number_of_nodes() > 1 else np.nan,
            'betweenness_centrality': mean(
                nx.betweenness_centrality(self._nx_graph).values()) if self._nx_graph.number_of_nodes() > 1 else np.nan,
            'harmonic_centrality': mean(
                nx.harmonic_centrality(self._nx_graph).values()) if self._nx_graph.number_of_nodes() > 1 else np.nan
        }

    def get_eigenvalues(self):
        if self._nx_graph.number_of_nodes() > 1:
            adjacency_matrix = nx.to_numpy_array(self._nx_graph)
            return np.linalg.eigvals(adjacency_matrix)
        return np.array([])

    def get_erdos_renyi_graph(self, number_of_random_graphs: int = 30, p: float = 0.5) -> List['DistanceBasedGraph']:
        random_graphs = []

        metadata = self.get_metadata()

        for _ in range(number_of_random_graphs):
            random_graph = DistanceBasedGraph(
                sequence_value=metadata['sequence'],
                distances=pd.DataFrame(),
                distance_function=metadata['distance_function'],
                interval=metadata['interval']
            )

            random_graph._nx_graph = nx.erdos_renyi_graph(
                n=self.nx_graph.number_of_nodes(),
                p=p
            )

            random_graph._nx_graph.graph['sequence'] = metadata['sequence']
            random_graph._nx_graph.graph['distance_function'] = metadata['distance_function']
            random_graph._nx_graph.graph['interval'] = metadata['interval']

            random_graphs.append(random_graph)

        return random_graphs




