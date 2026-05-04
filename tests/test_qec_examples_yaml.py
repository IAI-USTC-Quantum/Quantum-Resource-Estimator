"""Parity tests: pyqres YAML QEC examples vs QEC-Compiler benchmark builders.

Verifies that YAML composites compile into generated Python operation classes
and produce AbstractCircuit output matching the QEC-Compiler reference builders
at the gate level (gate names, count, order, qubit indices, params).

Covered:
  - GHZ, W, BV, DJ, Grover
  - QFT, QPE, QAOA, VQE, Ising
  - SWAP-test and small-Shor fixture

Not covered (measurements and metadata are NOT compared).
"""

from __future__ import annotations

import math

import pytest

pytest.importorskip(
    "qec_compiler",
    reason="qec_compiler is required for QEC example parity tests",
)

from pyqres.core.metadata import RegisterMetadata


@pytest.fixture(autouse=True)
def fresh_metadata():
    while len(RegisterMetadata.register_metadata_stack) > 1:
        RegisterMetadata.pop_register_metadata()
    RegisterMetadata.register_metadata_stack.clear()
    RegisterMetadata.push_register_metadata()
    yield
    while len(RegisterMetadata.register_metadata_stack) > 0:
        RegisterMetadata.pop_register_metadata()
    RegisterMetadata.push_register_metadata()


def _declare_reg(name, size, reg_type="General"):
    RegisterMetadata.get_register_metadata().declare_register(name, size, reg_type)


def _gates_summary(circuit):
    """Return list of (name, qubits, params) for comparison."""
    return [(g.name, g.qubits, g.params) for g in circuit.gates]


# ---------------------------------------------------------------------------
# GHZ parity
# ---------------------------------------------------------------------------

class TestGHZParity:
    def test_ghz_yaml_compiles_to_abstract_circuit(self):
        """QECExampleGHZ YAML composite lowers to AbstractCircuit."""
        from pyqres.generated import QECExampleGHZ
        from pyqres.core.lowering import to_abstract_circuit

        _declare_reg("q", 3)

        op = QECExampleGHZ(reg_list=["q"], param_list=[3])
        circuit = to_abstract_circuit(op)

        assert circuit.num_qubits == 3
        assert len(circuit.gates) == 3
        assert [g.name for g in circuit.gates] == ["H", "CNOT", "CNOT"]

    def test_ghz_yaml_matches_qec_builder(self):
        """QECExampleGHZ gate sequence matches build_ghz_circuit(3)."""
        from qec_compiler.cases.benchmark_state_prep import build_ghz_circuit
        from pyqres.generated import QECExampleGHZ
        from pyqres.core.lowering import to_abstract_circuit

        _declare_reg("q", 3)

        pyqres_op = QECExampleGHZ(reg_list=["q"], param_list=[3])
        pyqres_circuit = to_abstract_circuit(pyqres_op)
        qec_circuit = build_ghz_circuit(3, measure=False)

        pyqres_gates = _gates_summary(pyqres_circuit)
        qec_gates = _gates_summary(qec_circuit)

        assert pyqres_gates == qec_gates


# ---------------------------------------------------------------------------
# BV parity
# ---------------------------------------------------------------------------

class TestBVParity:
    def test_bv_yaml_compiles_to_abstract_circuit(self):
        """QECExampleBV YAML composite lowers to AbstractCircuit."""
        from pyqres.generated import QECExampleBV
        from pyqres.core.lowering import to_abstract_circuit

        _declare_reg("q", 4)

        op = QECExampleBV(reg_list=["q"], param_list=[3, 5])
        circuit = to_abstract_circuit(op)

        assert circuit.num_qubits == 4
        gate_names = [g.name for g in circuit.gates]
        # H, H, H, CNOT, CNOT, H, H, H
        assert gate_names.count("H") == 6
        assert gate_names.count("CNOT") == 2

    def test_bv_yaml_matches_qec_builder(self):
        """QECExampleBV gate sequence matches build_bv_circuit(3, secret=5)."""
        from qec_compiler.cases.benchmark_bv import build_bv_circuit
        from pyqres.generated import QECExampleBV
        from pyqres.core.lowering import to_abstract_circuit

        _declare_reg("q", 4)

        pyqres_op = QECExampleBV(reg_list=["q"], param_list=[3, 5])
        pyqres_circuit = to_abstract_circuit(pyqres_op)
        # secret=5 = 0b101, measure_all=False for gate-only comparison
        qec_circuit = build_bv_circuit(3, secret=5, measure_all=False)

        pyqres_gates = _gates_summary(pyqres_circuit)
        qec_gates = _gates_summary(qec_circuit)

        assert pyqres_gates == qec_gates


class TestAdditionalExampleParity:
    @pytest.mark.parametrize(
        ("case_name", "op_name", "num_qubits", "params", "builder_path", "builder_kwargs"),
        [
            (
                "w",
                "QECExampleW",
                3,
                [3],
                "qec_compiler.cases.benchmark_state_prep:build_w_circuit",
                {"n": 3, "measure": False},
            ),
            (
                "dj",
                "QECExampleDJ",
                4,
                [3, True],
                "qec_compiler.cases.benchmark_dj:build_dj_circuit",
                {"n": 3, "balanced": True, "measure_all": True},
            ),
            (
                "grover",
                "QECExampleGrover",
                3,
                [3, (5,), 1],
                "qec_compiler.cases.benchmark_grover:build_grover_circuit",
                {"n": 3, "marked_states": (5,), "iterations": 1},
            ),
            (
                "qft",
                "QECExampleQFT",
                4,
                [4],
                "qec_compiler.cases.benchmark_qft:build_qft_circuit",
                {"n": 4, "measure": False},
            ),
            (
                "qpe",
                "QECExampleQPE",
                5,
                [3, 2, 0.5],
                "qec_compiler.cases.benchmark_qpe:build_qpe_circuit",
                {"n_counting": 3, "n_system": 2, "unitary_eigenvalue": 0.5},
            ),
            (
                "qaoa",
                "QECExampleQAOA",
                4,
                [4, [(0, 1), (1, 2), (2, 3)], 1, math.pi / 4, math.pi / 8],
                "qec_compiler.cases.benchmark_qaoa:build_qaoa_circuit",
                {"n_vertices": 4, "edges": [(0, 1), (1, 2), (2, 3)], "p": 1},
            ),
            (
                "vqe",
                "QECExampleVQE",
                4,
                [4, 2, False],
                "qec_compiler.cases.benchmark_vqe:build_vqe_circuit",
                {"n_qubits": 4, "layers": 2, "ring_entanglement": False},
            ),
            (
                "ising",
                "QECExampleIsing",
                4,
                [4, [1.0, 1.0, 1.0], 1, 1.0],
                "qec_compiler.cases.benchmark_ising:build_ising_circuit",
                {"n_spins": 4, "couplings": [1.0, 1.0, 1.0], "p_level": 1},
            ),
            (
                "swap_test",
                "QECExampleSwapTest",
                5,
                [5],
                "qec_compiler.cases.benchmark_swap_test:build_swap_test_circuit",
                {"total_qubits": 5, "measure_all": False},
            ),
            (
                "small_shor",
                "QECExampleSmallShor",
                8,
                [15, 2],
                "qec_compiler.cases.benchmark_shor:build_stage5_small_shor_fixture",
                {"modulus": 15, "base": 2},
            ),
        ],
    )
    def test_yaml_algorithm_matches_qec_builder(
        self, case_name, op_name, num_qubits, params, builder_path, builder_kwargs
    ):
        """YAML algorithm definitions match QEC-Compiler reference gates."""
        import importlib
        from pyqres.core.lowering import to_abstract_circuit
        import pyqres.generated as generated

        module_name, function_name = builder_path.split(":")
        builder = getattr(importlib.import_module(module_name), function_name)
        op_cls = getattr(generated, op_name)

        _declare_reg("q", num_qubits)
        pyqres_circuit = to_abstract_circuit(op_cls(reg_list=["q"], param_list=params))
        qec_circuit = builder(**builder_kwargs)

        assert _gates_summary(pyqres_circuit) == _gates_summary(qec_circuit), case_name


# ---------------------------------------------------------------------------
# Structural: generated classes are importable and recognizable
# ---------------------------------------------------------------------------

class TestGeneratedExamplesImportable:
    def test_ghz_class_importable(self):
        from pyqres.generated import QECExampleGHZ
        assert QECExampleGHZ.__name__ == "QECExampleGHZ"

    def test_bv_class_importable(self):
        from pyqres.generated import QECExampleBV
        assert QECExampleBV.__name__ == "QECExampleBV"

    def test_ghz_through_qec_compiler_pipeline(self):
        """QECExampleGHZ compiles through the full QEC pipeline."""
        from pyqres.generated import QECExampleGHZ
        from pyqres.core.lowering import to_abstract_circuit
        from qec_compiler.decomposition import lower_to_logical

        _declare_reg("q", 3)

        op = QECExampleGHZ(reg_list=["q"], param_list=[3])
        circuit = to_abstract_circuit(op)
        logical = lower_to_logical(circuit)

        assert logical.ccz_inject_count is not None

    def test_bv_through_qec_compiler_pipeline(self):
        """QECExampleBV compiles through the full QEC pipeline."""
        from pyqres.generated import QECExampleBV
        from pyqres.core.lowering import to_abstract_circuit
        from qec_compiler.decomposition import lower_to_logical

        _declare_reg("q", 4)

        op = QECExampleBV(reg_list=["q"], param_list=[3, 5])
        circuit = to_abstract_circuit(op)
        logical = lower_to_logical(circuit)

        assert logical.ccz_inject_count is not None
