"""YAML-defined mirrors of QEC-Compiler benchmark examples."""

from __future__ import annotations

import math

import pytest

pytest.importorskip("qec_compiler")

from pyqres.core.lowering import to_abstract_circuit
from pyqres.core.metadata import RegisterMetadata


def _declare_q(size: int) -> None:
    RegisterMetadata.get_register_metadata().declare_register("q", size, "General")


def _assert_same_gate_circuit(actual, expected) -> None:
    assert actual.num_qubits == expected.num_qubits
    assert len(actual.gates) == len(expected.gates)
    for got, want in zip(actual.gates, expected.gates, strict=True):
        assert got.name == want.name
        assert got.qubits == want.qubits
        assert len(got.params) == len(want.params)
        for got_param, want_param in zip(got.params, want.params, strict=True):
            assert math.isclose(got_param, want_param, rel_tol=1e-12, abs_tol=1e-12)


def _lower(op, num_qubits: int):
    _declare_q(num_qubits)
    return to_abstract_circuit(op)


def test_yaml_ghz_matches_qec_compiler_builder():
    from pyqres.generated import QECExampleGHZ
    from qec_compiler.cases.benchmark_state_prep import build_ghz_circuit

    expected = build_ghz_circuit(4, measure=False)
    actual = _lower(QECExampleGHZ(["q"], [4]), expected.num_qubits)
    _assert_same_gate_circuit(actual, expected)


def test_yaml_w_matches_qec_compiler_builder():
    from pyqres.generated import QECExampleW
    from qec_compiler.cases.benchmark_state_prep import build_w_circuit

    expected = build_w_circuit(4, measure=False)
    actual = _lower(QECExampleW(["q"], [4]), expected.num_qubits)
    _assert_same_gate_circuit(actual, expected)


def test_yaml_bv_matches_qec_compiler_builder():
    from pyqres.generated import QECExampleBV
    from qec_compiler.cases.benchmark_bv import build_bv_circuit

    expected = build_bv_circuit(4, secret=0b1010)
    actual = _lower(QECExampleBV(["q"], [4, 0b1010]), expected.num_qubits)
    _assert_same_gate_circuit(actual, expected)


def test_yaml_dj_matches_qec_compiler_builder():
    from pyqres.generated import QECExampleDJ
    from qec_compiler.cases.benchmark_dj import build_dj_circuit

    expected = build_dj_circuit(4, balanced=True)
    actual = _lower(QECExampleDJ(["q"], [4, True]), expected.num_qubits)
    _assert_same_gate_circuit(actual, expected)


def test_yaml_grover_matches_qec_compiler_builder():
    from pyqres.generated import QECExampleGrover
    from qec_compiler.cases.benchmark_grover import build_grover_circuit

    expected = build_grover_circuit(3, marked_states=(0,), iterations=1)
    actual = _lower(QECExampleGrover(["q"], [3, [0], 1]), expected.num_qubits)
    _assert_same_gate_circuit(actual, expected)


def test_yaml_qft_matches_qec_compiler_builder():
    from pyqres.generated import QECExampleQFT
    from qec_compiler.cases.benchmark_qft import build_qft_circuit

    expected = build_qft_circuit(4, measure=False)
    actual = _lower(QECExampleQFT(["q"], [4]), expected.num_qubits)
    _assert_same_gate_circuit(actual, expected)


def test_yaml_qpe_matches_qec_compiler_builder():
    from pyqres.generated import QECExampleQPE
    from qec_compiler.cases.benchmark_qpe import build_qpe_circuit

    expected = build_qpe_circuit(4, 2, unitary_eigenvalue=0.5)
    actual = _lower(QECExampleQPE(["q"], [4, 2, 0.5]), expected.num_qubits)
    _assert_same_gate_circuit(actual, expected)


def test_yaml_qaoa_matches_qec_compiler_builder():
    from pyqres.generated import QECExampleQAOA
    from qec_compiler.cases.benchmark_qaoa import build_qaoa_circuit

    edges = [(0, 1), (1, 2), (2, 3)]
    expected = build_qaoa_circuit(4, edges, 1, gamma=math.pi / 4, beta=math.pi / 8)
    actual = _lower(
        QECExampleQAOA(["q"], [4, edges, 1, math.pi / 4, math.pi / 8]),
        expected.num_qubits,
    )
    _assert_same_gate_circuit(actual, expected)


def test_yaml_vqe_matches_qec_compiler_builder():
    from pyqres.generated import QECExampleVQE
    from qec_compiler.cases.benchmark_vqe import build_vqe_circuit

    expected = build_vqe_circuit(4, layers=2, ring_entanglement=True)
    actual = _lower(QECExampleVQE(["q"], [4, 2, True]), expected.num_qubits)
    _assert_same_gate_circuit(actual, expected)


def test_yaml_ising_matches_qec_compiler_builder():
    from pyqres.generated import QECExampleIsing
    from qec_compiler.cases.benchmark_ising import build_ising_circuit

    couplings = [1.0, 1.0, 1.0]
    expected = build_ising_circuit(4, couplings, p_level=1, h_transverse=1.0)
    actual = _lower(QECExampleIsing(["q"], [4, couplings, 1, 1.0]), expected.num_qubits)
    _assert_same_gate_circuit(actual, expected)


def test_yaml_swap_test_matches_qec_compiler_builder():
    from pyqres.generated import QECExampleSwapTest
    from qec_compiler.cases.benchmark_swap_test import build_swap_test_circuit

    expected = build_swap_test_circuit(5)
    actual = _lower(QECExampleSwapTest(["q"], [5]), expected.num_qubits)
    _assert_same_gate_circuit(actual, expected)


def test_yaml_small_shor_matches_qec_compiler_builder():
    from pyqres.generated import QECExampleSmallShor
    from qec_compiler.cases.benchmark_shor import build_stage5_small_shor_fixture

    expected = build_stage5_small_shor_fixture(modulus=15, base=2)
    actual = _lower(QECExampleSmallShor(["q"], [15, 2]), expected.num_qubits)
    _assert_same_gate_circuit(actual, expected)
