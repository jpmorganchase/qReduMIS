###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################

import random
import itertools
import json
from collections import Counter
from typing import List, Tuple, Dict, Union
import networkx as nx


def get_outset(counter: Counter, num_nodes: int, num_select: int) -> List[int]:
    """
    Gets nodes with high probability to be out of the independent set given the counts from the backend.

    Args:
        counter (Counter): Counter of node occurrences in solutions.
        num_nodes (int): Total number of nodes in the graph.
        num_select (int): Number of nodes to select.

    Returns:
        List[int]: List of node indices likely to be out of the set.
    """
    counter_keys = set(counter.keys())
    nodes_out_set = [n for n in range(num_nodes) if n not in counter_keys]

    if len(nodes_out_set) >= num_select:
        return nodes_out_set[:num_select]

    rem_needed = num_select - len(nodes_out_set)
    lowest_probability_nodes = [key for key, _ in counter.most_common()[::-1][:rem_needed]]
    nodes_out_set.extend(lowest_probability_nodes)

    return nodes_out_set


def get_inset(counter: Counter, num_select: int) -> List[int]:
    """
    Gets nodes with high probability to be in the independent set.

    Args:
        counter (Counter): Counter of node occurrences in solutions.
        num_select (int): Number of nodes to select.

    Returns:
        List[int]: List of node indices likely to be in the set.
    """
    return [key for key, _ in counter.most_common()[:num_select]]


def quantum_mis(clean_counts: List[Dict[str, Union[List[int], str, int]]], atom_positions: List[Tuple[float, float]], seed: int, version: str = "semi-greedy") -> List[Tuple[float, float]]:
    """
    Extracts the largest solution measured by the backend given the counts.

    Args:
        clean_counts (List[Dict[str, Union[List[int], str, int]]]): Processed results from quantum computation.
        atom_positions (List[Tuple[float, float]]): List of atom positions.
        seed (int): Random seed for reproducibility.
        version (str): Algorithm version to use.

    Returns:
        List[Tuple[float, float]]: List of atom positions in the selected solution.
    """
    max_size = max([len(clean_counts[i]["nodes"]) for i in range(len(clean_counts))])
    sols_max_size = [clean_counts[i] for i in range(len(clean_counts)) if len(clean_counts[i]["nodes"]) == max_size]

    if version == "semi-greedy":
        random.seed(seed)

    a_sol_max_size = random.choice(sols_max_size)
    
    return [atom_positions[i] for i in a_sol_max_size["nodes"]]


def quantum_select(
    clean_counts: List[Dict[str, Union[List[int], str, int]]],
    atom_positions: List[Tuple[float, float]],
    kernel_graph: nx.Graph,
    original_positions: List[Tuple[float, float]],
    seed: int,
    k_size: int = 2,
    num_nodes_frac: float = 0.4,
    selection_algo: str = "outset",
    version: str = "semi-greedy",
) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]], List[Tuple[float, float]]]:
    """
    Selects nodes to be included in or removed from the solution based on selection algorithm.

    Args:
        clean_counts (List[Dict[str, Union[List[int], str, int]]]): Processed results from quantum computation after running for the kernel graph.
        atom_positions (List[Tuple[float, float]]): List of atom positions in kernel.
        kernel_graph (nx.Graph): Reduced graph (kernel).
        original_positions (List[Tuple[float, float]]): Original list of atom positions.
        seed (int): Seed for reproducibility.
        k_size (int): Largest solution size to consider.
        num_nodes_frac (float): Fraction of nodes to consider.
        selection_algo (str): Node selection algorithm ("outset" or "inset").

    Returns:
        Tuple[List[Tuple[float, float]], List[Tuple[float, float]], List[Tuple[float, float]]]: 
            - selected_in_positions: Nodes selected to be part of the solution.
            - selected_out_positions: Nodes selected to be removed from the solution.
            - to_remove_positions: Positions of nodes to be removed from the kernel.
    """
    selected_in_positions = []
    selected_out_positions = []
    to_remove_positions = []

    random.seed(seed)

    if len(clean_counts) == 0 or len(atom_positions) == 0:
        logger.warning("Empty input provided to quantum select")
        return selected_in_positions, selected_out_positions, to_remove_positions

    solution_sizes = list(set([len(sol["nodes"]) for sol in clean_counts]))
    sizes_to_consider = sorted(solution_sizes, reverse=True)[:k_size]

    nodes_from_top_solutions = [sol["nodes"] for sol in clean_counts for _ in range(sol["count"]) if len(sol["nodes"]) in sizes_to_consider]
    node_counter = Counter(list(itertools.chain.from_iterable(nodes_from_top_solutions)))

    if selection_algo == "outset":
        num_nodes_to_select = max(1, int(num_nodes_frac * len(node_counter))) if node_counter else 1
        nodes_out_set = get_outset(node_counter, len(kernel_graph.nodes()), num_nodes_to_select)

        if nodes_out_set:
            removed_node = random.choice(nodes_out_set)
            removed_indices = [removed_node]
            selected_out_positions = [atom_positions[i] for i in removed_indices]
            to_remove_positions = [atom_positions[i] for i in removed_indices]

    elif selection_algo == "inset":
        num_nodes_to_select = max(1, int(num_nodes_frac * len(node_counter))) if node_counter else 1
        nodes_in_set = get_inset(node_counter, num_nodes_to_select)

        if nodes_in_set:
            selected_node = random.choice(nodes_in_set)

            atom_selected_pos = atom_positions[selected_node]
            selected_in_positions = [atom_selected_pos]
            to_remove_positions = [atom_selected_pos]
            selected_out_positions = []

            idx_node = original_positions.index(atom_selected_pos)

            if hasattr(kernel_graph, "neighbors"):
                neighbors = list(kernel_graph.neighbors(idx_node))

                for n in neighbors:
                    selected_out_positions.append(original_positions[n])
                    to_remove_positions.append(original_positions[n])

    return selected_in_positions, selected_out_positions, to_remove_positions