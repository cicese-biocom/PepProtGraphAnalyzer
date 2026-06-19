from typing import Dict
import networkx as nx
import numpy as np
from module.graph import DistanceBasedGraph


class GraphSimilarityComponent:
    def compute(self) -> Dict:
        pass


class EmptyGraphSimilarityComponent(GraphSimilarityComponent):
    def compute(self, graph1: DistanceBasedGraph, graph2: DistanceBasedGraph) -> Dict:
        metadata1 = graph1.get_metadata()
        metadata2 = graph2.get_metadata()

        return {
            "sequence": metadata1["sequence"],  # Both graphs share the same sequence
            "distance_function_1": metadata1["distance_function"],
            "interval_1": metadata1["interval"],
            "distance_function_2": metadata2["distance_function"],
            "interval_2": metadata2["interval"]
        }


class GraphSimilarityDecorator(GraphSimilarityComponent):
    _graph_similarity_component: GraphSimilarityComponent = None

    def __init__(self, graph_similarity_component: GraphSimilarityComponent):
        self._graph_similarity_component = graph_similarity_component

    @property
    def graph_similarity_component(self) -> GraphSimilarityComponent:
        return self._graph_similarity_component

    def compute(self, graph1: DistanceBasedGraph, graph2: DistanceBasedGraph) -> Dict:
        return self._graph_similarity_component.compute()


class CosineSimilarityDecorator(GraphSimilarityDecorator):
    def __init__(
            self,
            graph_similarity_component: GraphSimilarityComponent):
        super(CosineSimilarityDecorator, self).__init__(graph_similarity_component)

    def compute(self, graph1: DistanceBasedGraph, graph2: DistanceBasedGraph) -> Dict:
        graph_similarity_input = self.graph_similarity_component.compute(graph1, graph2)

        # Get eigenvalues of both graphs
        eigenvalues_1 = graph1.get_eigenvalues()
        eigenvalues_2 = graph2.get_eigenvalues()

        # Ensure the eigenvalue arrays are the same length
        if eigenvalues_1.shape != eigenvalues_2.shape:
            raise ValueError("Graphs must have the same number of eigenvalues for cosine similarity.")

        # Check if either eigenvalue array is zero, in which case return NaN
        if np.all(eigenvalues_1 == 0) or np.all(eigenvalues_2 == 0):
            graph_similarity_input['cosine_similarity'] = np.nan
        else:
            # Compute cosine similarity between the eigenvalue vectors
            graph_similarity_input['cosine_similarity'] = _cosine_similarity(eigenvalues_1, eigenvalues_2)

        return graph_similarity_input


class EditDistanceDecorator(GraphSimilarityDecorator):
    def __init__(
            self,
            graph_similarity_component: GraphSimilarityComponent,
            ged_timeout):
        super(EditDistanceDecorator, self).__init__(graph_similarity_component)
        self._ged_timeout = ged_timeout

    def compute(self, graph1: DistanceBasedGraph, graph2: DistanceBasedGraph) -> Dict:
        graph_similarity_input = self.graph_similarity_component.compute(graph1, graph2)

        graph_similarity_input['graph_edit_distance'] = nx.graph_edit_distance(
            graph1.nx_graph,
            graph2.nx_graph,
            node_match=lambda n1, n2: True,
            timeout=self._ged_timeout
        )

        return graph_similarity_input


class OptimizeEditDistanceDecorator(GraphSimilarityDecorator):
    def __init__(
            self,
            graph_similarity_component: GraphSimilarityComponent,
            ged_timeout):
        super(EditDistanceDecorator, self).__init__(graph_similarity_component)
        self._ged_timeout = ged_timeout

    def compute(self, graph1: DistanceBasedGraph, graph2: DistanceBasedGraph) -> Dict:
        graph_similarity_input = self.graph_similarity_component.compute(graph1, graph2)

        graph_similarity_input['optimize_graph_edit_distance'] = next(nx.optimize_graph_edit_distance(
            graph1.nx_graph,
            graph2.nx_graph
        ))

        return graph_similarity_input


class GraphSimilarityContext:
    def __init__(self):
        self._function_mapping = {
            'cosine_similarity': CosineSimilarityDecorator,
            'graph_edit_distance': EditDistanceDecorator,
            'optimize_graph_edit_distance': EditDistanceDecorator,
        }

    def compute(self, graph1: DistanceBasedGraph, graph2: DistanceBasedGraph, **kwargs):
        graph_similarity_component = EmptyGraphSimilarityComponent()

        for similarity_function in kwargs.get('graph_similarity_functions'):
            if similarity_function in self._function_mapping:
                func = self._function_mapping[similarity_function]
                kwargs['graph_similarity_component'] = graph_similarity_component
                params = {param: kwargs[param] for param in kwargs if param in func.__init__.__code__.co_varnames}
                graph_similarity_component = func(**params)

        return graph_similarity_component.compute(graph1, graph2)


def _cosine_similarity(vector_a, vector_b):
    # Dot product between the two vectors
    dot_product = np.sum(np.multiply(vector_a, vector_b))

    # Norms of the vectors (ensuring non-negative values)
    norm_a = np.sqrt(np.maximum(0, np.sum(np.power(vector_a, 2))))
    norm_b = np.sqrt(np.maximum(0, np.sum(np.power(vector_b, 2))))

    # Avoid division by zero
    if norm_a == 0 or norm_b == 0:
        return np.nan

    # Calculate cosine similarity (forcing real value)
    return np.divide(dot_product, (norm_a * norm_b)).real
