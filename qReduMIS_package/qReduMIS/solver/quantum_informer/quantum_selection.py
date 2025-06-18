###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################
import random
import itertools
import json
from collections import Counter


def get_outset(counter, num_nodes, num_select):
    """
    Method to get nodes with high probability to be out of the independent set given the counts from the backend.
    These counts are expressed with the input counter, which indicates the number of appearances among the quantum shots of each node

    Args:
        counter (Counter): counter of node occurences in solutions
        num_nodes (int): total number of nodes in the graph
        k (int): number of nodes to select

    Returns:
        list: list of node indices likely to be out of the set
    """

    # find nodes that never appeared in any solution
    counter_keys = set(counter.keys())
    nodes_out_set = [n for n in range(num_nodes) if n not in counter_keys]

    # if there are enough nodes that never appeared, return the requested number
    if len(nodes_out_set) >= num_select:
        return nodes_out_set[:num_select]

    # otherwise add nodes with lowest probability until num_selected is reached
    rem_needed = num_select - len(nodes_out_set)

    # get keys with lowest counts
    lowest_probability_nodes = [
        key for key, _ in counter.most_common()[::-1][:rem_needed]
    ]
    nodes_out_set.extend(lowest_probability_nodes)

    return nodes_out_set


def get_inset(counter, num_select):
    """
    Method to get nodes with high probability to be in the independent set

    Args:
        counter (Counter): counter of node occurences in solutions
        num_select (int): number of nodes to select

    Return:
        list: list of node indices likely to be in the set
    """

    # returns the nodes with the highest occurence counts
    return [key for key, _ in counter.most_common()[:num_select]]


def quantum_mis(clean_counts, atom_positions, seed, version="semi-greedy"):
    """
    Method to extract the largest solution measured by the backend given the counts

    Args:
        clean_counts (list): processed results from quantum computation
        atom_positions (list): list of atom positions
        seed (int): random seed for reproducibilty
        version (str): algorithm version to use

    Returns:
        list: list of atom positions in the selected solution
    """
    max_size = max([len(clean_counts[i]["nodes"]) for i in range(len(clean_counts))])
    sols_max_size = [
        clean_counts[i]
        for i in range(len(clean_counts))
        if len(clean_counts[i]["nodes"]) == max_size
    ]

    if version == "semi-greedy":
        random.seed(seed)

    a_sol_max_size = random.choice(sols_max_size)

    return [atom_positions[i] for i in a_sol_max_size["nodes"]]


def quantum_select(
    clean_counts,
    atom_positions,
    kernel_graph,
    original_positions,
    seed,
    k_size=2,
    num_nodes_frac=0.4,
    selection_algo="outset",
    version="semi-greedy",
):
    """
    Method to select nodes to be included in or removed from the solution based on selection algorithm.
    If "outset" is chosen, the method selects nodes to be removed from the graph.
    If "inset" is chosen, it selects nodes to be included in the solution and removes them along with their neighbors.

    Args:
        clean_counts (list[dict[str, list[int], str, int]]): processed results from quantum_computation after running for the kernel graph
        atom_positions (list): list of atom_positions in kernel
        kernel_graph (nx.Graph): reduced graph (kernel)
        original_positions (list): original list of atom positions
        seed (int): seed for reproducibilty
        k_size (int): largest solution size to consider
        num_nodes_frac (float): fraction of nodes to consider
        selection_algo (str): node selection algorithm ("outset" or "inset")

    Returns:
        tuple:
            - selected_in_positions: Nodes selected to be part of the solution.
            - selected_out_positions: Nodes selected to be removed from the solution.
            - to_remove_positions: Positions of nodes to be removed from the kernel


    """
    selected_in_positions = []
    selected_out_positions = []
    to_remove_positions = []

    # set random seed for reproducibility
    random.seed(seed)

    if len(clean_counts) == 0 or len(atom_positions) == 0:
        logger.warning("Empty input provided to quantum select")
        return selected_in_positions, selected_out_positions, to_remove_positions

    # get unique solution sizes from quantum results
    solution_sizes = list(set([len(sol["nodes"]) for sol in clean_counts]))

    # consider only the top k solution sizes
    sizes_to_consider = sorted(solution_sizes, reverse=True)[:k_size]

    # collect nodes from solutions with top sizes
    nodes_from_top_solutions = [
        sol["nodes"]
        for sol in clean_counts
        for _ in range(sol["count"])
        if len(sol["nodes"]) in sizes_to_consider
    ]
    node_counter = Counter(
        list(itertools.chain.from_iterable(nodes_from_top_solutions))
    )

    # apply selection strategy
    if selection_algo == "outset":
        # get nodes likely to be out of the set
        num_nodes_to_select = (
            max(1, int(num_nodes_frac * len(node_counter))) if node_counter else 1
        )
        nodes_out_set = get_outset(
            node_counter, len(kernel_graph.nodes()), num_nodes_to_select
        )

        # randomly select one node to remove
        if nodes_out_set:
            removed_node = random.choice(nodes_out_set)
            removed_indices = [removed_node]
            selected_out_positions = [atom_positions[i] for i in removed_indices]
            to_remove_positions = [atom_positions[i] for i in removed_indices]

    elif selection_algo == "inset":
        # get nodes likely to be in the set
        num_nodes_to_select = (
            max(1, int(num_nodes_frac * len(node_counter))) if node_counter else 1
        )
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
