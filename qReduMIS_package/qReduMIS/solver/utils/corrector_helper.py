###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################
from typing import List, Tuple


def get_conflicting_edges(
    graph: List[Tuple[int, int]], mis: List[int]
) -> List[Tuple[int, int]]:
    """
    Helper function to identify which edges are conflicting
    """

    return [e for e in graph if e[0] in mis and e[1] in mis]
