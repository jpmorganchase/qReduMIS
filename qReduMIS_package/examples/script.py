###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################
"""Minimal, runnable qReduMIS example.

Loads a Rydberg-atom problem instance, turns the atom register into its
unit-disk (blockade) graph, and solves the Maximum Independent Set problem on
it with ``MISSolver``.

Run it from anywhere:

    python script.py

For the annotated walkthrough — including the other informers and the Rydberg
backends — see ``example.ipynb`` next to this file.
"""

import json
from pathlib import Path

from qReduMIS.mis_solver import MISSolver
from qReduMIS.solver.informers.quantum.qaoa import QAOAInformer
from qReduMIS.solver.utils.graph_helper import (
    construct_graph_from_atom_positions,
    load_atoms,
)

# Resolve data/output locations relative to this file so the script behaves the
# same no matter which directory it is launched from.
HERE = Path(__file__).resolve().parent
INSTANCE = HERE / "input_data" / "problem_instances" / "atoms_L8_seed3559.json"
RESULTS_DIR = HERE / "results"

SEED = 3559


def main():
    """Solve one instance end to end and write the result to ``results/``."""
    # ``load_atoms`` returns a list of [x, y] pairs; the graph helper expects
    # hashable (x, y) tuples, which also become the node labels.
    atom_positions = [tuple(pos) for pos in load_atoms(str(INSTANCE))]
    graph = construct_graph_from_atom_positions(atom_positions)
    print(
        f"Instance {INSTANCE.name}: {len(atom_positions)} atoms -> blockade "
        f"graph with {graph.number_of_nodes()} nodes and "
        f"{graph.number_of_edges()} edges"
    )

    RESULTS_DIR.mkdir(exist_ok=True)

    # Any informer implementing the common contract can be dropped in here
    # (QAOAInformer, SAInformer, ...) without touching the loop.
    informer = QAOAInformer(
        selection_strategy="inset",
        num_shots=500,
        p=2,
        simulation_backend="local",
    )

    solver = MISSolver(
        informer=informer,
        top_k_solutions=2,
        max_iteration_limit=10,
    )

    solution, num_iterations = solver.solve(
        graph,
        seed_graph=SEED,
        cshot=0,
        folder_storing=str(RESULTS_DIR),
    )

    # A valid independent set contains no two adjacent nodes.
    is_independent = not any(
        graph.has_edge(u, v) for u in solution for v in solution if u != v
    )
    print(f"\nqReduMIS finished in {num_iterations} iteration(s)")
    print(f"MIS size: {len(solution)} (independent set: {is_independent})")
    if num_iterations == 0:
        print(
            "The classical reduction solved this instance on its own, so the "
            "informer was never queried."
        )

    final_result = {
        # ``construct_graph_from_atom_positions`` labels nodes 0..N-1 by their
        # index in ``atom_positions``, so map the solution back to coordinates.
        "mis_node_indices": sorted(solution),
        "atom_positions_mis": [list(atom_positions[node]) for node in sorted(solution)],
        "mis_size": len(solution),
        "num_iterations": num_iterations,
        "is_independent_set": is_independent,
    }

    out_file = RESULTS_DIR / "final_res.json"
    with open(out_file, "w") as f:
        json.dump(final_result, f, indent=2)
    print(f"Result written to {out_file}")


if __name__ == "__main__":
    main()
