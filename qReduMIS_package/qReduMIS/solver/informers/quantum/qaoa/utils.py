###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################

import numpy as np
import networkx as nx
import os
import ast

from qReduMIS.solver.informers.quantum.qaoa.tuning import get_mis_parameter
from qReduMIS.solver.informers.corrector_strategies.fixer import (
    get_fixup_sol,
    remove_first,
)

# ---------------------------------------------------------------------------
# Conditional imports — only needed for specific qaoa_params strategies or
# the legacy external-emulator path.  Gracefully degrade when absent so that
# the default qaoa_params="new" + local-Aer path always works.
# ---------------------------------------------------------------------------
try:
    from qReduMIS.solver.informers.quantum.qaoa.tuning import (
        precompute_vectorized_cpu_parallel,
    )
except ImportError:
    precompute_vectorized_cpu_parallel = None  # only used with qaoa_params="sk"

try:
    import qokit  # noqa: F401
    from qokit.parameter_utils import get_fixed_gamma_beta, get_sk_gamma_beta
except ImportError:
    get_fixed_gamma_beta = None  # only used with qaoa_params="maxcut"
    get_sk_gamma_beta = None  # only used with qaoa_params="sk"

try:
    from pytket.extensions.qiskit import qiskit_to_tk
    from pytket.qasm import circuit_to_qasm

    _PYTKET_AVAILABLE = True
except ImportError:
    _PYTKET_AVAILABLE = False

# ---------------------------------------------------------------------------
# Local Aer simulation (replaces external qemu.py subprocess)
# ---------------------------------------------------------------------------
try:
    from qiskit_aer import AerSimulator

    _AER_AVAILABLE = True
except ImportError:
    try:  # legacy qiskit < 1.0 location
        from qiskit.providers.aer import AerSimulator  # type: ignore[attr-defined]

        _AER_AVAILABLE = True
    except ImportError:
        _AER_AVAILABLE = False

##--------------------for the emulator

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from typing import Sequence


def append_z_prod_term(qc: QuantumCircuit, term: Sequence, gamma: float) -> None:
    """Appends a  multi-body Pauli-Z interaction acting on qubits whose indices
    correspond to those in 'term'.

    Parameters:
        qc: QuantumCircuit
        term: iterable
            ordered iterable containing qubit indices to apply Pauli-Z interaction to
        gamma: float
            evolution time for interaction

    """
    term_weight = len(term)
    if term_weight == 4:
        # in labs, four-body terms appear two times more than two-body
        # there is also a global scaling factor of 2 for all terms (four and two), which is ignored here
        assert all(term[i] < term[i + 1] for i in range(len(term) - 1))
        _gamma = 2 * gamma
        qc.cx(term[0], term[1])
        qc.cx(term[3], term[2])
        qc.rzz(2 * _gamma, term[1], term[2])
        qc.cx(term[3], term[2])
        qc.cx(term[0], term[1])
    elif term_weight == 2:
        qc.rzz(2 * gamma, term[0], term[1])
    elif term_weight == 1:
        qc.rz(2 * gamma, term[0])
    else:
        # fallback to general case
        target = term[-1]
        for control in term[:-1]:
            qc.cx(control, target)
        qc.rz(2 * gamma, target)
        for control in term[:-1]:
            qc.cx(control, target)


def append_x_term(qc: QuantumCircuit, q1: int, beta: float) -> None:
    """Append a single-qubit mixer rotation ``Rx(2*beta)`` on qubit ``q1``."""
    qc.rx(2 * beta, q1)


def append_cost_operator_circuit(
    qc: QuantumCircuit, terms: Sequence, gamma: float
) -> None:
    """Append the QAOA cost-layer rotations for all Hamiltonian ``terms`` at angle ``gamma``."""
    for term in terms:
        if len(term) == 2 and isinstance(term[1], tuple):
            if len(term[1]) == 2:
                coeff, (i, j) = term
                append_z_prod_term(qc, (i, j), gamma * coeff / 2)
            elif len(term[1]) == 1:
                coeff, (i,) = term
                append_z_prod_term(qc, (i,), gamma * coeff / 2)
        elif any([isinstance(i, tuple) for i in term]):
            raise ValueError(f"Invalid term received: {term}")
        else:
            append_z_prod_term(qc, term, gamma)


def append_mixer_operator_circuit(qc: QuantumCircuit, beta: float) -> None:
    """Append the QAOA transverse-field mixer layer (``Rx(2*beta)`` on every qubit)."""
    for n in qc.qubits:
        append_x_term(qc, n, beta)


def get_qaoa_circuit_from_terms(
    N: int,
    terms: Sequence,
    gammas: Sequence,
    betas: Sequence,
    save_statevector: bool = True,
    qr: QuantumRegister = None,
    cr: ClassicalRegister = None,
):
    """Generates a Qiskit circuit from Hamiltonian terms

    Parameters
    ----------
    N : int
        Number of qubits
    terms : list-like
        A sequence of `term` or `(float, term)`, where `term` is a tuple of ints.
        Each term corresponds to a summand in the cost Hamiltonian
        and th float value is the coefficient of this term.
        e.g. if terms = [(0.5, (0,1)), (0.3, (0,1,2,3))]
        the Hamiltonian is 0.5*Z0Z1 + 0.3*Z0Z1Z2Z3
        Unweighted Hamiltonians are supported as well:
        e.g. if terms = [(0,1), (0,1,2,3)]
        the Hamiltonian is Z0Z1 + Z0Z1Z2Z3
    beta : list-like
        QAOA parameter beta
    gamma : list-like
        QAOA parameter gamma
    save_statevector : bool, default True
        Add save state instruction to the end of the circuit
    qr : qiskit.QuantumRegister, default None
        Registers to use for the circuit.
        Useful when one has to compose circuits in a complicated way
        By default, G.number_of_nodes() registers are used
    cr : qiskit.ClassicalRegister, default None
        Classical registers, useful if measuring
        By default, no classical registers are added
    Returns
    -------
    qc : qiskit.QuantumCircuit
        Quantum circuit implementing QAOA
    """
    assert len(betas) == len(gammas)
    p = len(betas)  # infering number of QAOA steps from the parameters passed
    if qr is not None:
        assert qr.size >= N
    else:
        qr = QuantumRegister(N)

    if cr is not None:
        qc = QuantumCircuit(qr, cr)
    else:
        qc = QuantumCircuit(qr)

    # first, apply a layer of Hadamards
    qc.h(range(N))
    # second, apply p alternating operators
    for i in range(p):
        append_cost_operator_circuit(qc, terms, gammas[i])
        append_mixer_operator_circuit(qc, betas[i])
    if save_statevector:
        qc.save_statevector()
    return qc


##--------------------for the emulator


def get_hamming_weights_list(probability_list):
    """Return parallel lists of Hamming weights and counts from ``{"nodes", "count"}`` dicts."""
    hamming_weights = []
    probabilities = []

    for item in probability_list:
        hamming_weight = len(item["nodes"])
        hamming_weights.append(hamming_weight)
        probabilities.append(item["count"])

    return hamming_weights, probabilities


import subprocess


def _run_aer_simulation(circuit, quantum_shots=1000):
    """Run a qiskit QuantumCircuit locally using Aer and return counts dict.

    This replaces the external ``qemu.py`` subprocess call so the pipeline
    can run on any machine without special infrastructure.

    Args:
        circuit: qiskit ``QuantumCircuit`` (must include measurement gates).
        quantum_shots: number of shots to sample.

    Returns:
        dict mapping bitstrings (str) → int counts, e.g. ``{'010': 42, …}``
    """
    if not _AER_AVAILABLE:
        raise RuntimeError(
            "qiskit-aer is not installed.  Install it with:\n"
            "  pip install qiskit-aer\n"
            "This is required for local Aer simulation."
        )
    backend = AerSimulator(method="automatic")
    job = backend.run(circuit, shots=quantum_shots)
    return job.result().get_counts()


def call_quantum_component(
    file_path, quantum_shots=1000, m_value="H2-1", nf_flag=False, s_value="state-vector"
):
    """
    Legacy function: calls the external quantum emulator script via subprocess.
    Kept for backward compatibility when running on AWS infrastructure.
    For local runs the pipeline now uses ``_run_aer_simulation`` instead.
    """
    qemu_path = os.environ.get("QEMU_SCRIPT_PATH")
    if not qemu_path:
        raise RuntimeError(
            "No quantum emulator script configured. This legacy backend shells "
            "out to an external 'qemu.py' that is not distributed with this "
            "package; set QEMU_SCRIPT_PATH to its location, or use the default "
            "local simulation backend (simulation_backend='local') instead."
        )
    cmd = [
        "python3",
        qemu_path,
        file_path,
        "-n",
        str(quantum_shots),
        "-m",
        m_value,
    ]
    if nf_flag:
        cmd.append("-nf")
    cmd += ["-s", s_value]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("Error:", result.stderr)
        raise RuntimeError(f"Quantum component failed with code {result.returncode}")
    return result.stdout


def get_fixed_probs(
    G,
    N,
    mapping_dict,
    seed_graph,
    p,
    cshot,
    it,
    name_store,
    quantum_shots=1000,
    d=3,
    folder_storing=None,
    top_sample=0,
    three_regular=False,
    qaoa_params="new",
    simulation_backend="local",
):
    """
    Args:
        top_sample (int): indicates if we sample from the 1(st), 2(nd), or 3(rd) solutions with largest probability. It is accumulative, if 2, it means that it includes the first and second largest probability, if 3, it contains the first, second and third largest probability. If 0, it means that it considers all the bitstrings
        mapping_dict (dict): dictionary whose keys refer to the new index of nodes in graph mapped and the values the real index (from original graph)
    """
    terms = get_mis_terms(G)
    N = len(G.nodes())
    degrees = [degree for node, degree in G.degree()]
    d = np.mean(degrees)  ## we use the average degree

    if (
        qaoa_params == "maxcut"
    ):  ##  the parameters for QAOA for MaxCut on regular graphs from arXiv:2107.00677
        gamma, beta = get_fixed_gamma_beta(d, p)

    if qaoa_params == "new":
        gamma, beta = get_mis_parameter(d, p)

    if qaoa_params == "sk":
        precomputed_objectives = precompute_vectorized_cpu_parallel(terms, 0.0, N)
        w_len1, w_len2 = [], []
        for term in terms:
            if len(term[1]) == 1:
                w_len1.append(term[0])
            elif len(term[1]) == 2:
                w_len2.append(term[0])
        w_len1 = np.asarray(w_len1)
        w_len2 = np.asarray(w_len2)

        gamma, beta = get_sk_gamma_beta(
            p
        )  ## we get the params for SK and then we do the scaling below
        scale = 1 / np.sqrt(np.mean(w_len1**2) + np.mean(w_len2**2))
        scaled_gamma = -gamma * scale
        gamma = scaled_gamma

    ## we solve MIS:
    # 1. we get the circuit
    circ = get_qaoa_circuit_from_terms(
        N, terms[:-1], gamma, beta, save_statevector=False
    )
    circ.measure_all()

    # -------------------------------------------------------------------
    # 2-4. Simulate the circuit
    # -------------------------------------------------------------------
    #  "local"    → statevector simulation via qiskit-aer (works anywhere)
    #  "external" → pytket compile → QASM → external qemu.py subprocess
    # -------------------------------------------------------------------
    if simulation_backend == "external" and _PYTKET_AVAILABLE:
        # --- Legacy path: pytket compile → QASM → external qemu.py ---
        circuit = qiskit_to_tk(circ)
        folder_name = f"{folder_storing}/intermediate_results_circuits"
        os.makedirs(folder_name, exist_ok=True)
        circuit_path = f"{folder_name}/{name_store}_seed{seed_graph}_cshot{cshot}_iteration{it}.qasm"
        circuit_to_qasm(circuit, circuit_path, header="hqslib1", maxwidth=128)
        result = call_quantum_component(circuit_path, quantum_shots=quantum_shots)
        dict_str = result.split(":", 1)[1].strip()
        basis_probs = ast.literal_eval(dict_str)
    else:
        # --- Local path: qiskit Aer statevector/automatic simulation ---
        basis_probs = _run_aer_simulation(circ, quantum_shots=quantum_shots)

    ## postprocesss
    counts = []
    for key, value in basis_probs.items():
        ## key should be reversed!
        key = key[::-1]
        nodes = tuple(i for i, bit in enumerate(key) if bit == "1")
        nodes_mapped = tuple(mapping_dict[n] for n in nodes)
        counts.append({"nodes": nodes_mapped, "count": value})

    ## we need to relabel back
    G_mapped = nx.relabel_nodes(G, mapping_dict)
    fixup_bitstring_probs = get_fixup_sol(counts, list(G_mapped.edges()), remove_first)

    ### if we want to benchmark by sampling from bitstrings with the highest probability

    if top_sample > 0:  ## we will sample from some bitstrings
        ## sample_from is like 1, 2, 3, indicating if we sample from the solutions with largest probability, or also include the second largest probability, or the third largest probability
        unique_nodes = set()
        cleaned_data = []

        # Iterate over the list and add unique dictionaries to cleaned_data
        for entry in fixup_bitstring_probs:
            nodes_tuple = tuple(
                entry["nodes"]
            )  # Convert list to tuple for set operations
            if nodes_tuple not in unique_nodes:
                unique_nodes.add(nodes_tuple)
                cleaned_data.append(entry)

        sorted_data = sorted(cleaned_data, key=lambda x: x["count"])
        values = list(set([elem["count"] for elem in sorted_data]))
        some_data = [
            elem for elem in sorted_data if elem["count"] in values[:top_sample]
        ]
        fixup_bitstring_probs = some_data

    return fixup_bitstring_probs  # terms, basis_probs,


def get_mis_terms(G: nx.Graph):
    """Get terms corresponding to cost function value
    Args:
        G: MIS problem graph (3-regular only)
    Returns:
        terms to be used in the simulation
    """
    terms = [(-(1 / 4), (int(e[0]), int(e[1]))) for e in G.edges()]
    terms += [((1 / 4), (int(e[0]),)) for e in G.edges()]
    terms += [((1 / 4), (int(e[1]),)) for e in G.edges()]
    terms += [((-1 / 2), (int(n),)) for n in G.nodes()]

    total_w = int(G.number_of_edges()) / 4
    terms.append((-total_w, tuple()))
    total_n = int(G.number_of_nodes()) / 2
    terms.append((+total_n, tuple()))

    aggregated_data = {}
    for value, key in terms:
        if key in aggregated_data:
            aggregated_data[key] += value
        else:
            aggregated_data[key] = value
    combined_terms = [(value, key) for key, value in aggregated_data.items()]
    return combined_terms


def get_basis_probability(probabilities):
    """Map a statevector probability array to a ``{bitstring: probability}`` dict."""
    res_dict = {}
    num_qubits = int(np.log2(len(probabilities)))
    format_string = f"{{:0{num_qubits}b}}"  # Format string for binary representation

    for i, prob in enumerate(probabilities):
        basis_state = format_string.format(i)  # Convert index to binary string
        res_dict[basis_state] = prob
    return res_dict


def get_qubit_probs(num_qubits, res_dict):
    """Return the marginal probability of measuring 1 on each of ``num_qubits`` qubits."""
    qubit_probabilities = np.zeros(num_qubits)

    for key in res_dict.keys():  ## for each basis state
        for qubit_index in range(num_qubits):
            if key[qubit_index] == "1":
                qubit_probabilities[qubit_index] += res_dict[key]

    return qubit_probabilities


def calculate_hamming_weight(binary_string):
    """Return the number of set bits ('1's) in ``binary_string``."""
    return sum(int(bit) for bit in binary_string)


def get_hamming_weights(probability_dict):
    """Return parallel lists of Hamming weights and probabilities from a bitstring dict."""
    hamming_weights = []
    probabilities = []

    for key, prob in probability_dict.items():
        hamming_weight = calculate_hamming_weight(key)
        hamming_weights.append(hamming_weight)
        probabilities.append(prob)

    return hamming_weights, probabilities


def get_inset_nodes(fixup_bitstring_probs, k_size=2, num_select=4):
    """Deprecated: use :func:`qReduMIS.solver.informers.selection.get_inset_nodes`.

    Kept as a thin re-export so existing imports keep working; the shared
    implementation is the single source of truth.
    """
    from qReduMIS.solver.informers.selection import get_inset_nodes as _shared

    return _shared(fixup_bitstring_probs, k_size=k_size, num_select=num_select)
