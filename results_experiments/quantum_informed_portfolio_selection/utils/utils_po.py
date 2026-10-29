###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################
"""
utils_po — Portfolio optimization utilities
============================================

Helper functions for reading benchmark portfolio data from Beasley's
OR library and constructing market graphs via correlation thresholding.

SPDX-License-Identifier: Apache-2.0
"""

import numpy as np
from copy import deepcopy
import networkx as nx
import random


# read input data from Beasley's OR library
def read_port_data(file='problem_instances/port5.txt'):
    """
    Helper function to read in benchmark data for portfolio optimization taken from Beasley's OR library
    (https://people.brunel.ac.uk/~mastjjb/jeb/orlib/portinfo.html). The file is not shipped with this
    release: download it yourself and save it as ``problem_instances/port5.txt``.
    """

    lines = []
    with open(file, "rt") as myfile:
        for line in myfile:
            lines.append(line.rstrip('\n'))

    # get number of stocks
    n_stocks = int(lines[0])

    # get vector of expected returns
    returns = []
    deviations = []
    for ii in range(1, n_stocks+1):
        mu, std = float(lines[ii].split()[0]), float(lines[ii].split()[1])
        returns.append(mu)
        deviations.append(std)

    returns = np.array(returns)
    deviations = np.array(deviations)
    dev_matrix = np.diag(deviations) # matrix with std on diagonal

    # get correlation matrix
    Corr = np.zeros([n_stocks, n_stocks])

    for ll in range(n_stocks+1, len(lines)):
        line = lines[ll].split()
        idx1, idx2 = int(line[0]), int(line[1])
        correlation = float(line[2])
        Corr[idx1-1][idx2-1] = correlation
        Corr[idx2-1][idx1-1] = correlation

    # construct variance-covariance matrix
    Sigma = np.dot(dev_matrix, np.dot(Corr, dev_matrix))

    return n_stocks, returns, Corr, Sigma


def apply_thresholding(Corr, threshold, allow_anticorr=True):
    """
    Helper function to apply simple thresholding logic on correlation matrix
    Returns thresholded correlation matrix and corresponding unweighted adjacecny matrix. 
    """
    # get thresholded correlation matrix
    Corr_threshold = deepcopy(Corr)
    if allow_anticorr:
        ## we allow to keep anticorrelations in the graph
        #print('taking absolute value to apply threshold')
        Corr_threshold[np.abs(Corr_threshold) < threshold] = 0
    else: 
        ## we remove the anticorrelations
        #print('not taking absolute value to apply threshold')
        Corr_threshold[Corr_threshold < threshold] = 0

    # get undweighted adjacency matrix post thresholding
    adjaceny = deepcopy(Corr_threshold)
    #adjaceny[adjaceny > 0] = 1
    adjaceny[np.abs(adjaceny) > 0] = 1
    np.fill_diagonal(adjaceny, 0)

    return Corr_threshold, adjaceny


def get_asset_graph(adjaceny):
    """
    Helper function to generate asset graph from adjacency matrix.
    Returns graph as networkx object.
    """
    graph_corr = nx.from_numpy_array(adjaceny)
    return graph_corr