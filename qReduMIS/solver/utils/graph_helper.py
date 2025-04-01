###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################
import json
import networkx as nx 


def load_atoms(filepath: str):
    with open(filepath, "r") as infile:
        input_atoms = json.load(infile)

    return input_atoms

    
def construct_graph_from_atom_positions(atom_positions): 

    if len(atom_positions) == 0:
        return None
        
    node_labels = range(len(atom_positions))

    edge_dict = {}
    for i in range(len(atom_positions)):
        x, y = atom_positions[i]
        edge_dict[node_labels[i]] = []
        for j in range(i+1,len(atom_positions)):
            u, v = atom_positions[j]
            if abs(x-u) <= 1 and abs(y-v) <=1:
                edge_dict[node_labels[i]] += [node_labels[j]]

    G = nx.from_dict_of_lists(edge_dict)
    return G


def get_out_set(counter, n_nodes, num_select): 
    ## they have very low probability in the counter. Note that nodes with occurence 0 do not appear in counter 
    nodes_out_set=[n for n in range(n_nodes) if n not in list(counter.keys())]
    if len(nodes_out_set)>=num_select:
        return nodes_out_set[:num_select]
    else:
        k=num_select - len(nodes_out_set)
        ## k must be dynamically checked as we could have less nodes than k possible to pick 
        ## k at least the number of nodes in kernels
        lowest_prob = [key for key, value in counter.most_common()[::-1][:k]]
        for p in lowest_prob:
            nodes_out_set.append(p)
        return nodes_out_set


def get_reduction_factor(original_graph, reduced_graph):
    """
    """
    n_pre = len(original_graph.nodes())
    n_post = len(reduced_graph.nodes())
    reduction_factor = (n_pre - n_post)/n_pre

    return reduction_factor



def separate_atom_positions(atom_positions_init, s, r):
    """
    Separates atom positions into three lists based on indices in s and r
    """
    s_set, r_set = set(s), set(r)

    # Use list comprehensions to separate the positions
    atom_positions_s = [atom_positions_init[i] for i in range(len(atom_positions_init)) if i in s]
    atom_positions_r = [atom_positions_init[i] for i in range(len(atom_positions_init)) if i in r]
    atom_positions_K = [atom_positions_init[i] for i in range(len(atom_positions_init)) if (i not in s) and (i not in r)] ## atoms of the kernel

    return atom_positions_s, atom_positions_r, atom_positions_K