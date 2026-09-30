# qReduMIS — Library Overview

`qReduMIS` is a hybrid classical–quantum algorithm for the **Maximum Independent
Set (MIS)** problem. The library exposes a single generic solver,
[MISSolver](mis_solver.py), that alternates between

1. a **classical reducer** that simplifies the graph using exact reduction
   rules, and
2. a pluggable **informer** that picks one (or a few) frozen nodes on the
   remaining *kernel* graph.

The informer can be a QAOA simulator, a C++ simulated-annealing solver, a
Rydberg-atom backend, or any object implementing the
[Informer](solver/informers/base.py) ABC.

---

## Public API

```python
from qReduMIS import MISSolver
```

That's it. Pair `MISSolver` with whichever informer you want:

| Informer                                                                       | Where it runs                            | Extra dependencies |
| ------------------------------------------------------------------------------ | ---------------------------------------- | ------------------ |
| [QAOAInformer](solver/informers/quantum/qaoa/informer.py)                      | local QAOA statevector / Qiskit Aer      | `qiskit`, `qiskit-aer` |
| [SAInformer](solver/informers/classical/sa/informer.py)                        | wrapped C++ simulated-annealing binary   | C++ compiler       |
| [QuantumAnnealingInformer](solver/informers/quantum/quantumannealing/informer.py) | Braket `LocalSimulator` or QuEra Aquila  | `amazon-braket-sdk`|

All of these run with the **main** package dependencies (`poetry install`);
none requires an optional extra. A runnable end-to-end script lives at
[examples/script.py](../examples/script.py), an annotated walkthrough of every
informer at [examples/example.ipynb](../examples/example.ipynb), and a minimal
notebook at [example.ipynb](example.ipynb).

---

## Layout

```
qReduMIS/
├── __init__.py            # exports `MISSolver`
├── mis_solver.py          # canonical informer-pluggable solver
├── configurations.ini     # default hyperparameters
├── README.md              # this file
├── example.ipynb          # minimal usage notebook
├── input_data/            # bundled inputs (e.g. schedules/ for the Rydberg drive)
│
└── solver/
    ├── classical_reducer/ # exact graph-reduction rules
    ├── utils/             # shared graph + config + schedule helpers
    └── informers/         # ← all node-selection backends
        ├── base.py        #   Informer ABC
        ├── selection.py   #   shared frozen-node selection logic
        ├── quantum/       #   quantum informers
        │   ├── qaoa/              #   QAOAInformer + utils + tuning
        │   └── quantumannealing/ #   QuantumAnnealingInformer + backend_system
        ├── classical/     #   classical informers
        │   └── sa/                #   SAInformer + C++ binary
        └── corrector_strategies/ #   fix-up heuristics to repair infeasible samples
```

> Note: running the QAOA / quantum-annealing informers writes per-iteration
> `result_backend_it*.json` files to the current working directory (raw backend
> output). These are git-ignored — delete them after a run if unwanted.

---

## Minimal usage

```python
import networkx as nx
from qReduMIS import MISSolver
from qReduMIS.solver.informers.quantum.qaoa import QAOAInformer

# 1. Build a graph
G = nx.erdos_renyi_graph(n=20, p=0.25, seed=42)

# 2. Pick an informer
#    p, num_shots and the angle strategy (qaoa_params) fall back to the
#    [qaoa] section of configurations.ini when omitted.
informer = QAOAInformer(selection_strategy="inset", num_shots=1000, p=2)

# 3. Solve
solver = MISSolver(
    informer=informer,
    top_k_solutions=2,
    max_iteration_limit=10,
)
solution, n_iter = solver.solve(G, seed_graph=0, cshot=0)

print(f"MIS size = {len(solution)} (after {n_iter} qReduMIS iterations)")
# validate: no two solution nodes share an edge
assert all(not G.has_edge(u, v) for u in solution for v in solution if u < v)
```

To swap in a different informer, replace the informer object — the solver code
is unchanged:

```python
# Simulated annealing (needs the compiled sa_solver binary)
from qReduMIS.solver.informers.classical.sa import SAInformer
informer = SAInformer(selection_strategy="inset", replicas=10_000, steps=32)
```

The **quantum-annealing** informer works on atom positions rather than a
`networkx.Graph`, so it is queried directly rather than through `MISSolver`;
see the corresponding section of
[examples/example.ipynb](../examples/example.ipynb)
for how to run `QuantumAnnealingInformer` and select a Braket backend via
`BackendFactory`.

---

## Configuration (`configurations.ini`)

Default hyperparameters live in [configurations.ini](configurations.ini) and are
read at runtime via `read_config()` in
[config_helper.py](solver/utils/config_helper.py). Two sections are used today:

```ini
[quantum]
# Pulse schedule for the quantum-annealing (Rydberg) informer
schedule = input_data/schedules/optimized_piecewise_linear_schedule_large_HP.json

[qaoa]
p = 10            # number of QAOA layers (circuit depth)
qaoa_params = new # angle strategy: "new" (MIS params), "maxcut", or "sk"
num_shots = 1000  # measurement shots per circuit
```

The `[qaoa]` values are **fallbacks**: any argument passed explicitly to
`QAOAInformer(...)` overrides the config, so existing call sites keep working
unchanged. Omit an argument to have it read from the config instead — mirroring
how the annealing informer loads its `schedule`.

---

## How the solver works

```
                       ┌────────────────────────────────────┐
                       │  MISSolver.solve(G, …)             │
                       └────────────────┬───────────────────┘
                                        │
                  ┌─────────────────────▼──────────────────────┐
                  │  classical reducer                         │
                  │  - applies exact reduction rules           │
                  │  - returns kernel K, frozen-in s, removed r│
                  └─────────────────────┬──────────────────────┘
                                        │
                       fully reducible? ├── yes ──▶ return W
                                        │
                                        ▼ no
                  ┌────────────────────────────────────────────┐
                  │  informer.get_clean_counts(K, …)           │
                  │  → list of candidate independent sets      │
                  └─────────────────────┬──────────────────────┘
                                        │
                  ┌─────────────────────▼──────────────────────┐
                  │  informer.find_maximum_independent_set     │
                  │  informer.select_nodes  → freeze + remove  │
                  └─────────────────────┬──────────────────────┘
                                        │
                                        ▼
                              recurse on smaller K
```

The solver tracks three sets across iterations:

- `S` — frozen nodes selected so far,
- `W` — incumbent (best) MIS found so far,
- `R` — removed nodes.

When the recursion bottoms out (empty kernel, fully reducible kernel, or
`max_iteration_limit` hit) `MISSolver` returns `W` and the iteration count.

---

## Implementing your own informer

Subclass [Informer](solver/informers/base.py) and implement three methods:

```python
from qReduMIS.solver.informers.base import Informer

class MyInformer(Informer):
    selection_strategy = "inset"
    clean_counts = None

    def get_clean_counts(self, K, N, reversed_mapping, seed_graph, cshot,
                         current_iteration, name_store=None, folder_storing=None,
                         **kwargs):
        # Return a list of dicts: [{"nodes": [...], "count": N}, ...]
        ...

    def find_maximum_independent_set(self, clean_counts, seed):
        # Return the best IS (list of node ids) seen in clean_counts.
        ...

    def select_nodes(self, clean_counts, kernel_graph, seed,
                     k_size=2, num_nodes_frac=0.4):
        # Return (selected_in, selected_out, to_remove) node lists.
        ...
```

Pass an instance to `MISSolver(informer=MyInformer(...))` and make sure to include new tests and run:

```
poetry run pytest tests/
```
