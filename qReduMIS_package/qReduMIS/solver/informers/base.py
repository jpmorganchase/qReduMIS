###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################
"""
Informer abstract base class.

An *informer* is a node-selection backend for the qReduMIS loop.  It is queried
once per iteration on the current reduced kernel graph and returns a list of
candidate solutions (``clean_counts``) that the solver uses to:

  - find a candidate maximum independent set (``find_maximum_independent_set``)
  - pick frozen nodes for the next reduction (``select_nodes``)

Concrete implementations:

  - :class:`qReduMIS.solver.informers.quantum.qaoa.informer.QAOAInformer` — QAOA on a local Qiskit Aer simulator
  - :class:`qReduMIS.solver.informers.classical.sa.informer.SAInformer` — compiled C++ SA solver
  - :class:`qReduMIS.solver.informers.quantum.quantumannealing.informer.QuantumAnnealingInformer`
    — Rydberg-atom backends (positions-based; queried directly rather than through MISSolver)
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple

import networkx as nx


class Informer(ABC):
    """Abstract interface every graph-based informer must implement."""

    selection_strategy: str
    clean_counts: List[dict] | None

    @abstractmethod
    def get_clean_counts(
        self,
        K: nx.Graph,
        N: int,
        reversed_mapping: Dict[int, int],
        seed_graph: int,
        cshot: int,
        current_iteration: int,
        name_store: str | None = None,
        folder_storing: str | None = None,
        **kwargs,
    ) -> List[dict]:
        """Run the informer on kernel *K* and return ``clean_counts``."""

    @abstractmethod
    def find_maximum_independent_set(self, clean_counts: List[dict], seed: int) -> list:
        """Return the largest IS measured across the returned candidates."""

    @abstractmethod
    def select_nodes(
        self,
        clean_counts: List[dict],
        kernel_graph: nx.Graph,
        seed: int,
        k_size: int = 2,
        num_nodes_frac: float = 0.4,
    ) -> Tuple[list, list, list]:
        """Return ``(selected_in, selected_out, to_remove)`` node lists."""
