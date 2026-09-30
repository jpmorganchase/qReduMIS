###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################

import os
import numpy as np
import json
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


def get_mis_parameter(degree, p):
    """Return pre-fit QAOA ``(gammas, betas)`` for a node ``degree`` and depth ``p``.

    Reads ``qaoa_fixed_params.json`` and evaluates the stored degree-dependent
    fit for each of the ``p`` layers.
    """
    _data_path = os.path.join(os.path.dirname(__file__), "qaoa_fixed_params.json")
    with open(_data_path, "rb") as json_file:
        loaded_mis_data = json.load(json_file)
    gammas = np.zeros(p)
    betas = np.zeros(p)
    for i in range(p):
        gamma_para = loaded_mis_data[f"{p}"][f"{i+1}"]["gammas_fit_params"]
        gammas[i] = gamma_para[2] + gamma_para[0] / (
            degree ** gamma_para[1] + gamma_para[3]
        )

        beta_para = loaded_mis_data[f"{p}"][f"{i+1}"]["betas_fit_params"]
        betas[i] = beta_para[2] + beta_para[0] / (degree ** beta_para[1] + beta_para[3])
    return gammas * 2, -betas / 2
