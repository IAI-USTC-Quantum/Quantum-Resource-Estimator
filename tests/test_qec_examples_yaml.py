"""Parity tests: pyqres YAML QEC examples vs QEC-Compiler benchmark builders.

Verifies that YAML composites compile into generated Python operation classes
and produce AbstractCircuit output matching the QEC-Compiler reference builders
at the gate level (gate names, count, order, qubit indices, params).

Covered:
  - QECExampleGHZ  vs  build_ghz_circuit(3)
  - QECExampleBV   vs  build_bv_circuit(3, secret=5)

Not covered (measurements and metadata are NOT compared).
"""

from __future__ import annotations

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

        _declare_reg("q0", 1)
        _declare_reg("q1", 1)
        _declare_reg("q2", 1)

        op = QECExampleGHZ(reg_list=["q0", "q1", "q2"], param_list=[3])
        circuit = to_abstract_circuit(op)

        assert circuit.num_qubits == 3
        assert len(circuit.gates) == 3
        assert [g.name for g in circuit.gates] == ["H", "CNOT", "CNOT"]

    def test_ghz_yaml_matches_qec_builder(self):
        """QECExampleGHZ gate sequence matches build_ghz_circuit(3)."""
        from qec_compiler.cases.benchmark_state_prep import build_ghz_circuit
        from pyqres.generated import QECExampleGHZ
        from pyqres.core.lowering import to_abstract_circuit

        _declare_reg("q0", 1)
        _declare_reg("q1", 1)
        _declare_reg("q2", 1)

        pyqres_op = QECExampleGHZ(reg_list=["q0", "q1", "q2"], param_list=[3])
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

        _declare_reg("q0", 1)
        _declare_reg("q1", 1)
        _declare_reg("q2", 1)
        _declare_reg("anc", 1)

        op = QECExampleBV(reg_list=["q0", "q1", "q2", "anc"], param_list=[3])
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

        _declare_reg("q0", 1)
        _declare_reg("q1", 1)
        _declare_reg("q2", 1)
        _declare_reg("anc", 1)

        pyqres_op = QECExampleBV(reg_list=["q0", "q1", "q2", "anc"], param_list=[3])
        pyqres_circuit = to_abstract_circuit(pyqres_op)
        # secret=5 = 0b101, measure_all=False for gate-only comparison
        qec_circuit = build_bv_circuit(3, secret=5, measure_all=False)

        pyqres_gates = _gates_summary(pyqres_circuit)
        qec_gates = _gates_summary(qec_circuit)

        assert pyqres_gates == qec_gates


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

        _declare_reg("q0", 1)
        _declare_reg("q1", 1)
        _declare_reg("q2", 1)

        op = QECExampleGHZ(reg_list=["q0", "q1", "q2"], param_list=[3])
        circuit = to_abstract_circuit(op)
        logical = lower_to_logical(circuit)

        assert logical.ccz_inject_count is not None

    def test_bv_through_qec_compiler_pipeline(self):
        """QECExampleBV compiles through the full QEC pipeline."""
        from pyqres.generated import QECExampleBV
        from pyqres.core.lowering import to_abstract_circuit
        from qec_compiler.decomposition import lower_to_logical

        _declare_reg("q0", 1)
        _declare_reg("q1", 1)
        _declare_reg("q2", 1)
        _declare_reg("anc", 1)

        op = QECExampleBV(reg_list=["q0", "q1", "q2", "anc"], param_list=[3])
        circuit = to_abstract_circuit(op)
        logical = lower_to_logical(circuit)

        assert logical.ccz_inject_count is not None
