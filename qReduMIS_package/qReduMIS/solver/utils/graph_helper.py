###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################
import json
from typing import List
import networkx as nx


def load_atoms(filepath: str) -> dict:
    """
    Loads atom data from a JSON file.

    Args:
        filepath (str): The path to the JSON file containing atom data.

    Returns:
        dict: The atom data loaded from the file.
    """
    with open(filepath, "r") as infile:
        input_atoms = json.load(infile)

    return input_atoms


def construct_graph_from_atom_positions(atom_positions: List[tuple]) -> nx.Graph:
    """
    Constructs a graph from atom positions.

    Args:
        atom_positions (List[tuple]): A list of tuples representing the positions of atoms.

    Returns:
        networkx.Graph or None: A graph where nodes represent atoms and edges represent proximity, or None if no positions are provided.
    """
    if len(atom_positions) == 0:
        return None

    node_labels = range(len(atom_positions))

    edge_dict = {}
    for i in range(len(atom_positions)):
        x, y = atom_positions[i]
        edge_dict[node_labels[i]] = []
        for j in range(i + 1, len(atom_positions)):
            u, v = atom_positions[j]
            if abs(x - u) <= 1 and abs(y - v) <= 1:
                edge_dict[node_labels[i]] += [node_labels[j]]

    G = nx.from_dict_of_lists(edge_dict)
    return G


def get_out_set(counter: dict, n_nodes: int, num_select: int) -> List[int]:
    """
    Determines a set of nodes to be excluded based on their occurrence in a counter.

    Args:
        counter (dict): A counter of node occurrences.
        n_nodes (int): The total number of nodes.
        num_select (int): The number of nodes to select for exclusion.

    Returns:
        List[int]: A list of node indices to be excluded.
    """
    nodes_out_set = [n for n in range(n_nodes) if n not in list(counter.keys())]
    if len(nodes_out_set) >= num_select:
        return nodes_out_set[:num_select]
    else:
        k = num_select - len(nodes_out_set)
        lowest_prob = [key for key, value in counter.most_common()[::-1][:k]]
        for p in lowest_prob:
            nodes_out_set.append(p)
        return nodes_out_set


def get_reduction_factor(original_graph: nx.Graph, reduced_graph: nx.Graph) -> float:
    """
    Calculates the reduction factor between the original and reduced graphs.

    Args:
        original_graph (networkx.Graph): The original graph.
        reduced_graph (networkx.Graph): The reduced graph.

    Returns:
        float: The reduction factor, representing the proportion of nodes removed.
    """
    n_pre = len(original_graph.nodes())
    n_post = len(reduced_graph.nodes())
    reduction_factor = (n_pre - n_post) / n_pre

    return reduction_factor


def separate_atom_positions(
    atom_positions_init: List[tuple], s: List[int], r: List[int]
) -> tuple:
    """
    Separates atom positions into three lists based on indices in s and r.

    Args:
        atom_positions_init (List[tuple]): Initial list of atom positions.
        s (List[int]): Indices for the first subset of atom positions.
        r (List[int]): Indices for the second subset of atom positions.

    Returns:
        tuple: Three lists of atom positions corresponding to indices in s, r, and the remaining indices (kernel).
    """
    s_set, r_set = set(s), set(r)

    atom_positions_s = [
        atom_positions_init[i] for i in range(len(atom_positions_init)) if i in s_set
    ]
    atom_positions_r = [
        atom_positions_init[i] for i in range(len(atom_positions_init)) if i in r_set
    ]
    atom_positions_K = [
        atom_positions_init[i]
        for i in range(len(atom_positions_init))
        if (i not in s_set) and (i not in r_set)
    ]

    return atom_positions_s, atom_positions_r, atom_positions_K
