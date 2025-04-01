###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################
from enum import Enum
from itertools import combinations
import networkx as nx
from sortedcontainers import SortedList
import copy


class State(Enum):
    """Enumeration for node states in the reduction process."""

    UNKNOWN_STATE = 0
    REMOVED = 1
    SELECTED = 2


class Candidate(object):
    """Readable and comparable pair of {degree, node_id}.

    These are sorted ascendingly by degree (first) and then node_id (second).

    Args:
        degree (int): The degree of the node.
        node (int): The identifier of the node.
    """

    def __init__(self, degree, node):
        self.degree = degree
        self.node = node

    def __lt__(self, other):
        """Compare candidates based on degree and node ID."""
        if self.degree == other.degree:
            return self.node < other.node
        return self.degree < other.degree

    def __eq__(self, other):
        """Check equality based on node ID."""
        return self.node == other.node

    def __repr__(self):
        """Return a string representation of the candidate."""
        return f"{self.node}({self.degree})"


class Reducer(object):
    """Class implementation to hold the graph and metadata while reducing.

    Args:
        verbose (bool): A boolean indicating whether to print verbose output.
        max_clique_size (int, optional): The maximum size of cliques to consider for reduction.
    """

    def __init__(self, verbose=False, max_clique_size=None):
        """Just store settings internally."""
        self.verbose = verbose
        self.max_clique_size = max_clique_size

    def has_unresolved(self):
        """Check if there are clique candidates left to check.

        Returns:
            bool: A boolean indicating if unresolved candidates exist.
        """
        return len(self.unresolved) > 0

    def is_below_max_clique_size(self):
        """Check if the smallest candidate is below max_clique_size.

        Returns:
            bool: A boolean indicating if the smallest candidate is below the max clique size.
        """
        if self.max_clique_size is None:
            return True
        return self.unresolved[0].degree < self.max_clique_size

    def reduce(self, graph):
        """Perform the reduction logic on the graph.

        This *will* modify the graph and return its reduced version.

        Args:
            graph (nx.Graph): The graph to be reduced.

        Returns:
            tuple: A tuple containing the reduced graph, removed nodes, and selected nodes.
        """
        self.graph = graph
        self.unresolved = SortedList()
        self.states = {node: State.UNKNOWN_STATE for node in graph.nodes}

        for node in list(graph.nodes):
            if node in graph.adj[node]:
                if self.verbose:
                    print(f"Removing {node} (self-loop)")
                graph.remove_node(node)
                self.states[node] = State.REMOVED

        for node in graph.nodes:
            self.unresolved.add(Candidate(graph.degree[node], node))

        while self.has_unresolved() and self.is_below_max_clique_size():
            candidate = self.unresolved.pop(0).node
            if self.is_exposed_clique(candidate):
                if self.verbose:
                    print(f"Removing {self.clique_str(candidate)}")
                self.remove_exposed_clique(candidate)
            elif self.verbose:
                print(f"Not a clique {self.clique_str(candidate)}")

        removed = [
            n
            for n, s in self.states.items()
            if s == State.REMOVED or s == State.SELECTED
        ]
        selected = [n for n, s in self.states.items() if s == State.SELECTED]
        return graph, removed, selected

    def reduce_once(self, graph):
        """Perform a single iteration of the reduction logic on the graph.

        This *will* modify the graph and return its reduced version.

        Args:
            graph (nx.Graph): The graph to be reduced.

        Returns:
            tuple: A tuple containing the reduced graph, removed nodes, and selected nodes.
        """
        self.graph = graph
        self.unresolved = SortedList()
        self.states = {node: State.UNKNOWN_STATE for node in graph.nodes}

        for node in list(graph.nodes):
            if node in graph.adj[node]:
                if self.verbose:
                    print(f"Removing {node} (self-loop)")
                graph.remove_node(node)
                self.states[node] = State.REMOVED
                break

        for node in graph.nodes:
            self.unresolved.add(Candidate(graph.degree[node], node))

        while self.has_unresolved() and self.is_below_max_clique_size():
            candidate = self.unresolved.pop(0).node
            if self.is_exposed_clique(candidate):
                if self.verbose:
                    print(f"Removing {self.clique_str(candidate)}")
                self.remove_exposed_clique(candidate)
            elif self.verbose:
                print(f"Not a clique {self.clique_str(candidate)}")
            break

        removed = [
            n
            for n, s in self.states.items()
            if s == State.REMOVED or s == State.SELECTED
        ]
        selected = [n for n, s in self.states.items() if s == State.SELECTED]
        return graph, removed, selected

    def remove_node(self, node):
        """Remove the designated node from the graph.

        Args:
            node (int): The node to be removed.
        """
        for i in self.graph.adj[node]:
            k = self.graph.degree[i]
            self.unresolved.discard(Candidate(k, i))
            self.unresolved.add(Candidate(k - 1, i))

        k = self.graph.degree[node]
        self.unresolved.discard(Candidate(k, node))
        self.states[node] = State.REMOVED
        self.graph.remove_node(node)

    def remove_exposed_clique(self, corner):
        """Remove the exposed clique identified by this corner.

        Args:
            corner (int): The node identifying the exposed clique.
        """
        for i in list(self.graph.adj[corner]):
            self.remove_node(i)
        self.unresolved.discard(Candidate(0, corner))
        self.states[corner] = State.SELECTED
        self.graph.remove_node(corner)

    def is_exposed_clique(self, corner):
        """Check whether nodes form a clique.

        Args:
            corner (int): The node to check for clique formation.

        Returns:
            bool: A boolean indicating if the nodes form a clique.
        """
        neighbors = self.graph.adj[corner]
        for i in neighbors:
            if self.graph.degree[i] < len(neighbors):
                return False
        for i, j in combinations(neighbors, 2):
            if j not in self.graph.adj[i]:
                return False
        return True

    def clique_str(self, node):
        """Show a clique candidate as a curly-braced list.

        Args:
            node (int): The node representing the clique candidate.

        Returns:
            str: A string representation of the clique.
        """
        clique = [node] + list(self.graph.adj[node])
        clique = ",".join(str(x) for x in clique)
        return "{" + clique + "}"


def get_reduced_graph(graph, verbose=False):
    """Expose a compatible interface to utils_reduction.py.

    Args:
        graph (nx.Graph): The graph to be reduced.
        verbose (bool): A boolean indicating whether to print verbose output.

    Returns:
        tuple: A tuple containing the reduced graph, removed nodes, and selected nodes.
    """
    graph_ = copy.deepcopy(graph)
    reducer = Reducer(verbose=verbose)
    graph_, removed, selected = reducer.reduce(graph_)
    return graph_, [], [[x] for x in selected]


def run_recursive_simplification(
    graph, mis_candidates_total=[], isolated_nodes_total=[], verbose=False
):
    """Run recursive simplification on the graph.

    Args:
        graph (nx.Graph): The graph to be simplified.
        mis_candidates_total (list): A list to store MIS candidates.
        isolated_nodes_total (list): A list to store isolated nodes.
        verbose (bool): A boolean indicating whether to print verbose output.

    Returns:
        tuple: A tuple containing the simplified graph, removed nodes, and selected nodes.
    """
    graph_ = copy.deepcopy(graph)
    reducer = Reducer(verbose=verbose)
    graph_, removed, selected = reducer.reduce(graph_)
    return graph_, [], [[x] for x in selected]


def run_simple_reduction(graph, isolated_total=[], dangling_total=[], verbose=False):
    """Run simple reduction on the graph.

    Args:
        graph (nx.Graph): The graph to be reduced.
        isolated_total (list): A list to store isolated nodes.
        dangling_total (list): A list to store dangling nodes.
        verbose (bool): A boolean indicating whether to print verbose output.

    Returns:
        tuple: A tuple containing the reduced graph, removed nodes, and selected nodes.
    """
    graph_ = copy.deepcopy(graph)
    reducer = Reducer(verbose=verbose, max_clique_size=3)
    graph_, removed, selected = reducer.reduce(graph_)
    return graph_, [], [[x] for x in selected]


def run_reduction_cutoff(
    graph,
    cutoff,
    mis_candidates_total=[],
    isolated_nodes_total=[],
    seed=0,
    verbose=False,
):
    """Run reduction with a cutoff on the graph.

    Args:
        graph (nx.Graph): The graph to be reduced.
        cutoff (int): The maximum clique size to consider for reduction.
        mis_candidates_total (list): A list to store MIS candidates.
        isolated_nodes_total (list): A list to store isolated nodes.
        seed (int): A seed for random operations.
        verbose (bool): A boolean indicating whether to print verbose output.

    Returns:
        tuple: A tuple containing the reduced graph, removed nodes, and selected nodes.
    """
    graph_ = copy.deepcopy(graph)
    reducer = Reducer(verbose=verbose, max_clique_size=cutoff)
    graph_, removed, selected = reducer.reduce(graph_)
    return graph_, [], [[x] for x in selected]
