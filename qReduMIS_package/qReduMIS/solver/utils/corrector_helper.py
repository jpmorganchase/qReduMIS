###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################

from typing import List, Tuple


def get_conflicting_edges(
    graph: List[Tuple[int, int]], mis: List[int]
) -> List[Tuple[int, int]]:
    """
    Identifies conflicting edges in a graph based on a given maximal independent set (MIS).

    Args:
        graph (List[Tuple[int, int]]): A list of tuples representing the edges of the graph.
        mis (List[int]): A list of nodes representing the maximal independent set.

    Returns:
        List[Tuple[int, int]]: A list of edges that are conflicting, where both nodes of the edge are in the MIS.
    """
    return [e for e in graph if e[0] in mis and e[1] in mis]
