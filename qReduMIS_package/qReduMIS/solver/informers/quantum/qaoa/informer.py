###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################

"""
QAOA-based informer for the qReduMIS algorithm.

The canonical implementation lives here as ``QAOAInformer``.  The older class
name ``QuantumStatevector`` is preserved as an alias for backward compatibility.
"""
from qReduMIS.solver.informers.quantum.qaoa.utils import get_fixed_probs
from qReduMIS.solver.informers.selection import (
    find_maximum_independent_set,
    select_frozen_nodes,
)
from qReduMIS.solver.utils.config_helper import read_config
from typing import List, Tuple
import networkx as nx


class QAOAInformer:
    """
    QAOA-based informer for the Maximum Independent Set (MIS) problem.

    Builds a depth-``p`` QAOA circuit for the kernel graph and samples it on a
    local Qiskit Aer simulator to produce candidate independent sets.

    Args:
        selection_strategy (str): Strategy for selecting frozen nodes
            ("inset" or "outset").
        num_shots (int, optional): Measurement shots per circuit. Falls back to
            ``[qaoa] num_shots`` in ``configurations.ini`` when ``None``.
        p (int, optional): Number of QAOA layers (circuit depth). Falls back to
            ``[qaoa] p`` when ``None``.
        simulation_backend (str): Which simulator path to use; ``"local"`` runs
            the Qiskit Aer statevector/shot simulation.
        qaoa_params (str, optional): Angle strategy ("new" MIS params, "maxcut"
            or "sk"). Falls back to ``[qaoa] qaoa_params`` when ``None``.
    """

    def __init__(
        self,
        selection_strategy: str,
        num_shots: int = None,
        p: int = None,
        simulation_backend: str = "local",
        qaoa_params: str = None,
    ):
        """Initialise the informer, filling unset values from configurations.ini."""
        # Values fall back to configurations.ini ([qaoa] section) when not
        # explicitly provided, mirroring how the annealing informer reads its
        # schedule from the same config file.
        cfg = read_config()
        self.selection_strategy = selection_strategy
        self.num_shots = (
            num_shots
            if num_shots is not None
            else cfg.getint("qaoa", "num_shots", fallback=1000)
        )
        self.p = p if p is not None else cfg.getint("qaoa", "p", fallback=10)
        self.qaoa_params = (
            qaoa_params
            if qaoa_params is not None
            else cfg.get("qaoa", "qaoa_params", fallback="new")
        )
        self.simulation_backend = simulation_backend
        self.clean_counts = None

    def get_clean_counts(
        self,
        K,
        N,
        mapping,
        seed_graph,
        cshot,
        current_iteration,
        name_store=None,
        folder_storing=None,
        top_sample=0,
        three_regular=False,
    ):
        """
        Args:
            K (nx.graph): the kernel graph
            N (nx.grpah): the number of nodes in graph
            mapping (dict): dictionary whose keys refer to the new index of nodes in graph mapped and the values the real index (from original graph)
            top_sample: top_sample (int): indicates if we sample from the 1(st), 2(nd), or 3(rd) solutions with largest probability. It is accumulative, if 2, it means that it includes the first and second largest probability, if 3, it contains the first, second and third largest probability. If 0, it means that it considers all the bitstrings
        """
        return get_fixed_probs(
            K,
            N,
            mapping,
            seed_graph,
            self.p,
            cshot,
            current_iteration,
            name_store,
            quantum_shots=self.num_shots,
            folder_storing=folder_storing,
            top_sample=top_sample,
            three_regular=three_regular,
            qaoa_params=self.qaoa_params,
            simulation_backend=self.simulation_backend,
        )

    def find_maximum_independent_set(
        self,
        clean_counts: List[dict],
        seed: int,
    ) -> List[int]:
        """
        Finds the largest solution measured, representing the MIS given by the backend.

        Args:
            clean_counts (List[dict]): The clean counts from the quantum backend.
            seed (int): Random seed for reproducibility.

        Returns:
            List[int]: set list of index of node in the maximum independent set.
        """
        return find_maximum_independent_set(clean_counts, seed)

    def select_nodes(
        self,
        clean_counts: List[dict],
        kernel_graph: nx.Graph,
        seed: int,
        k_size: int = 2,
        num_nodes_frac: float = 0.4,
    ) -> Tuple[List[int], List[int], List[int]]:
        """
        Selects nodes to be included in or removed from the solution based on the selection strategy.

        Args:
            clean_counts (List[dict]): Processed results from quantum computation.
            kernel_graph (nx.Graph): Reduced graph (kernel).
            seed (int): Random seed for reproducibility.
            k_size (int): Largest solution size to consider.
            num_nodes_frac (float): Fraction of nodes to consider.

        Returns:
            Tuple[List[int], List[int], List[int]]:
                - selected_in_positions: Nodes selected to be part of the solution.
                - selected_out_positions: Nodes selected to be removed from the solution.
                - to_remove_positions: Positions of nodes to be removed from the kernel.
        """
        return select_frozen_nodes(
            clean_counts,
            kernel_graph,
            seed,
            strategy=self.selection_strategy,
            k_size=k_size,
            num_nodes_frac=num_nodes_frac,
        )


# ---------------------------------------------------------------------------
# Backward-compatible alias kept so older notebooks that import
# ``QuantumStatevector`` keep working.
# ---------------------------------------------------------------------------
QuantumStatevector = QAOAInformer
