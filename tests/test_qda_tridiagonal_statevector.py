"""Statevector parity for the tridiagonal QDA block-encoding path."""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("qiskit", reason="qiskit is required for statevector parity")
pytest.importorskip("pysparq", reason="pysparq is required for reference simulation")

import pysparq
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

from pyqres.algorithms.block_encoding import BlockEncodingTridiagonal
from pyqres.core.metadata import RegisterMetadata
from pyqres.core.qec_lowering import QECLoweringVisitor


MAX_STATEVECTOR_QUBITS = 25


@pytest.fixture(autouse=True)
def clean_systems():
    while len(RegisterMetadata.register_metadata_stack):
        RegisterMetadata.pop_register_metadata()
    RegisterMetadata.push_register_metadata()
    pysparq.System.clear()
    yield
    while len(RegisterMetadata.register_metadata_stack):
        RegisterMetadata.pop_register_metadata()
    RegisterMetadata.push_register_metadata()
    pysparq.System.clear()


def _declare_pyqres_registers():
    rm = RegisterMetadata.get_register_metadata()
    rm.declare_register("main", 2, "UnsignedInteger")
    rm.declare_register("anc_UA", 4, "UnsignedInteger")


def _make_qec_circuit():
    _declare_pyqres_registers()
    op = BlockEncodingTridiagonal(
        main_reg="main",
        anc_UA="anc_UA",
        alpha=0.5,
        beta=0.3,
    )
    return QECLoweringVisitor().build_circuit(op)


def _append_plus_one(qc: QuantumCircuit, qubits, controls=(), inverse=False):
    qs = list(qubits)
    cs = list(controls)
    if inverse:
        qc.mcx(cs, qs[0]) if cs else qc.x(qs[0])
        for k in range(1, len(qs)):
            qc.mcx(cs + qs[:k], qs[k])
        return

    for k in range(len(qs) - 1, 0, -1):
        qc.mcx(cs + qs[:k], qs[k])
    qc.mcx(cs, qs[0]) if cs else qc.x(qs[0])


def _append_abstract_gate(qc: QuantumCircuit, gate):
    name = gate.name
    qubits = list(gate.qubits)
    params = list(gate.params)

    if name == "X":
        qc.x(qubits[0])
    elif name == "H":
        qc.h(qubits[0])
    elif name == "S":
        qc.s(qubits[0])
    elif name == "S_DAG":
        qc.sdg(qubits[0])
    elif name == "CNOT":
        qc.cx(qubits[0], qubits[1])
    elif name == "MCX":
        qc.x(qubits[0]) if len(qubits) == 1 else qc.mcx(qubits[:-1], qubits[-1])
    elif name == "RY":
        qc.ry(float(params[0]), qubits[0])
    elif name == "RZ":
        qc.rz(float(params[0]), qubits[0])
    elif name == "PLUS_ONE":
        _append_plus_one(qc, qubits)
    elif name == "PLUS_ONE_DAG":
        _append_plus_one(qc, qubits, inverse=True)
    elif name in ("CPLUS_ONE", "CPLUS_ONE_DAG"):
        n_bits, n_controls = int(params[0]), int(params[1])
        target = qubits[n_controls:n_controls + n_bits + 1]
        controls = qubits[:n_controls]
        _append_plus_one(qc, target, controls, inverse=name.endswith("_DAG"))
    elif name == "REFLECT":
        target = qubits[-1]
        qc.h(target)
        qc.mcx(qubits[:-1], target) if len(qubits) > 1 else qc.x(target)
        qc.h(target)
    else:
        raise AssertionError(f"Unsupported qiskit parity gate: {gate}")


def _qiskit_statevector(circuit):
    qc = QuantumCircuit(circuit.num_qubits)
    for gate in circuit.gates:
        _append_abstract_gate(qc, gate)
    return np.asarray(Statevector.from_instruction(qc).data)


def _pysparq_statevector(num_qubits: int):
    from pysparq.algorithms.block_encoding import (
        BlockEncodingTridiagonal as PySparqBlockEncodingTridiagonal,
    )

    pysparq.System.clear()
    pysparq.System.add_register("main", pysparq.UnsignedInteger, 2)
    pysparq.System.add_register("anc_UA", pysparq.UnsignedInteger, 4)

    state = pysparq.SparseState()
    PySparqBlockEncodingTridiagonal("main", "anc_UA", 0.5, 0.3)(state)

    dense = np.zeros(1 << num_qubits, dtype=complex)
    main_id = pysparq.System.get_id("main")
    anc_id = pysparq.System.get_id("anc_UA")
    for basis_state in state.basis_states:
        main = basis_state.registers[main_id].value
        anc = basis_state.registers[anc_id].value
        dense[main | (anc << 2)] += complex(basis_state.amplitude)
    return dense


def test_block_encoding_tridiagonal_qec_statevector_matches_pysparq():
    circuit = _make_qec_circuit()
    assert circuit.num_qubits <= MAX_STATEVECTOR_QUBITS
    assert circuit.num_qubits == 6

    qiskit_state = _qiskit_statevector(circuit)
    pysparq_state = _pysparq_statevector(circuit.num_qubits)

    inner = np.vdot(pysparq_state, qiskit_state)
    phase = inner / abs(inner) if abs(inner) > 1e-12 else 1
    np.testing.assert_allclose(qiskit_state, phase * pysparq_state, atol=1e-10)
