"""Integration tests for pyqres → QEC-compiler pipeline.

Tests the full flow:
  pyqres Operation → QECLoweringVisitor → AbstractCircuit → QECCompiler → LogicalCircuit
"""

from __future__ import annotations

import pytest

pytest.importorskip(
    "qec_compiler",
    reason="qec_compiler is required for QEC integration tests",
)

from pyqres.core.metadata import RegisterMetadata, program_metadata


@pytest.fixture(autouse=True)
def fresh_metadata():
    """Reset register metadata for each test."""
    from pyqres.core.metadata import RegisterMetadata
    while len(RegisterMetadata.register_metadata_stack) > 1:
        RegisterMetadata.pop_register_metadata()
    RegisterMetadata.register_metadata_stack.clear()
    RegisterMetadata.push_register_metadata()
    yield
    while len(RegisterMetadata.register_metadata_stack) > 0:
        RegisterMetadata.pop_register_metadata()
    RegisterMetadata.push_register_metadata()


def _declare_reg(name, size, reg_type="General"):
    from pyqres.core.metadata import RegisterMetadata
    RegisterMetadata.get_register_metadata().declare_register(name, size, reg_type)


def _make_visitor():
    from pyqres.core.qec_lowering import QECLoweringVisitor
    return QECLoweringVisitor()


def _to_circuit(op):
    from pyqres.core.qec_lowering import QECLoweringVisitor
    v = QECLoweringVisitor()
    return v.build_circuit(op)


# ---------------------------------------------------------------------------
# Unit tests for individual lowering rules
# ---------------------------------------------------------------------------

class TestBasicGateLowering:
    def test_public_to_abstract_circuit_entrypoint(self):
        from pyqres.core.lowering import to_abstract_circuit
        from pyqres.primitives.gates import Hadamard

        _declare_reg("q", 1)
        circuit = to_abstract_circuit(Hadamard(reg_list=["q"]))

        assert circuit.num_qubits == 1
        assert [g.name for g in circuit.gates] == ["H"]

    def test_intermediate_primitives_exported(self):
        from pyqres.primitives import MCX

        _declare_reg("c", 1)
        _declare_reg("t", 1)
        circuit = _to_circuit(MCX(reg_list=["c", "t"]))

        assert [g.name for g in circuit.gates] == ["MCX"]

    def test_unsupported_core_primitive_fails_closed(self):
        from pyqres.core.qec_lowering import UnsupportedQECPrimitive
        from pyqres.primitives.arithmetic import CustomArithmetic

        _declare_reg("x", 1)
        op = CustomArithmetic(
            reg_list=["x"],
            param_list=[lambda value: value, 1, 1],
        )

        with pytest.raises(UnsupportedQECPrimitive, match="CustomArithmetic"):
            _to_circuit(op)

    def test_hadamard_lowering(self):
        from pyqres.primitives.gates import Hadamard
        _declare_reg("q", 2)
        op = Hadamard(reg_list=["q"])
        circuit = _to_circuit(op)
        assert circuit.num_qubits == 2
        h_gates = [g for g in circuit.gates if g.name == "H"]
        assert len(h_gates) == 2  # Hadamard on full register

    def test_x_gate_lowering(self):
        from pyqres.primitives.gates import X
        _declare_reg("q", 3)
        op = X(reg_list=["q"], param_list=[1])
        circuit = _to_circuit(op)
        x_gates = [g for g in circuit.gates if g.name == "X"]
        assert len(x_gates) == 1

    def test_primitive_own_controller_is_applied(self):
        from pyqres.primitives.gates import X

        _declare_reg("ctrl", 1)
        _declare_reg("target", 1)
        op = X(reg_list=["target"], param_list=[0]).control_by_all_ones("ctrl")
        circuit = _to_circuit(op)

        assert [g.name for g in circuit.gates] == ["MCX"]
        assert circuit.gates[0].qubits == (0, 1)

    def test_reflection_lowering(self):
        from pyqres.primitives.transform import Reflection_Bool
        _declare_reg("q", 3)
        op = Reflection_Bool(reg_list=["q"], param_list=[True])
        circuit = _to_circuit(op)
        reflect_gates = [g for g in circuit.gates if g.name == "REFLECT"]
        assert len(reflect_gates) == 1
        assert len(reflect_gates[0].qubits) == 3

    def test_plus_one_lowering(self):
        from pyqres.algorithms.block_encoding import PlusOneOverflow
        _declare_reg("main", 3, "UnsignedInteger")
        _declare_reg("overflow", 1, "Boolean")
        op = PlusOneOverflow(reg_list=["main", "overflow"], param_list=[1])
        circuit = _to_circuit(op)
        gate_names = {g.name for g in circuit.gates}
        assert "PLUS_ONE" in gate_names or "MCX" in gate_names or "X" in gate_names

    def test_qft_lowering(self):
        from pyqres.primitives.transform import QFT
        _declare_reg("q", 3)
        op = QFT(reg_list=["q"])
        circuit = _to_circuit(op)
        gate_names = {g.name for g in circuit.gates}
        assert "H" in gate_names
        assert "CPHASE" in gate_names


# ---------------------------------------------------------------------------
# End-to-end: pyqres → QEC-compiler
# ---------------------------------------------------------------------------

class TestEndToEndCompilation:
    def test_simple_circuit_compiles(self):
        """H + CNOT circuit compiles through QEC-compiler."""
        from pyqres.primitives.gates import Hadamard, CNOT
        from qec_compiler.decomposition import lower_to_logical
        _declare_reg("q0", 1)
        _declare_reg("q1", 1)

        # Build a simple circuit using manual gate emission
        v = _make_visitor()
        v.alloc.allocate("q0", 1)
        v.alloc.allocate("q1", 1)

        v._emit_gate("H", (0,))
        v._emit_gate("CNOT", (0, 1))

        circuit = v.build_circuit()
        assert circuit.num_qubits == 2
        assert len(circuit.gates) == 2

        logical = lower_to_logical(circuit)
        assert logical.ccz_inject_count is not None

    def test_reflect_compiles(self):
        """REFLECT gate compiles to LogicalCircuit with CCZ gates."""
        from qec_compiler.decomposition import lower_to_logical
        from qec_compiler.ir import AbstractCircuit, AbstractGate

        circuit = AbstractCircuit(
            num_qubits=3,
            gates=(AbstractGate(name="REFLECT", params=(3,), qubits=(0, 1, 2)),),
        )
        logical = lower_to_logical(circuit)
        assert logical.ccz_inject_count > 0

    def test_plus_one_compiles(self):
        """PLUS_ONE gate compiles to LogicalCircuit."""
        from qec_compiler.decomposition import lower_to_logical
        from qec_compiler.ir import AbstractCircuit, AbstractGate

        circuit = AbstractCircuit(
            num_qubits=4,
            gates=(AbstractGate(name="PLUS_ONE", params=(4,), qubits=(0, 1, 2, 3)),),
        )
        logical = lower_to_logical(circuit)
        assert logical.ccz_inject_count > 0

    def test_add_compiles(self):
        """ADD gate compiles to LogicalCircuit."""
        from qec_compiler.decomposition import lower_to_logical
        from qec_compiler.ir import AbstractCircuit, AbstractGate

        circuit = AbstractCircuit(
            num_qubits=4,
            gates=(AbstractGate(name="ADD", params=(2,), qubits=(0, 1, 2, 3)),),
        )
        logical = lower_to_logical(circuit)
        assert logical.ccz_inject_count > 0

    def test_pyqres_modular_intermediate_primitives_compile(self):
        """pyqres MOD_ADD/MOD_MUL primitives lower and compile through QEC."""
        from pyqres.primitives import MOD_ADD, MOD_MUL
        from qec_compiler.decomposition import lower_to_logical

        _declare_reg("a", 2, "UnsignedInteger")
        _declare_reg("b", 2, "UnsignedInteger")
        mod_add_circuit = _to_circuit(MOD_ADD(reg_list=["a", "b"], param_list=[3]))
        assert [g.name for g in mod_add_circuit.gates] == ["MOD_ADD"]
        assert lower_to_logical(mod_add_circuit).ccz_inject_count > 0

        _declare_reg("x", 4, "UnsignedInteger")
        mod_mul_circuit = _to_circuit(MOD_MUL(reg_list=["x"], param_list=[2, 15]))
        assert [g.name for g in mod_mul_circuit.gates] == ["MOD_MUL"]
        assert lower_to_logical(mod_mul_circuit).ccz_inject_count > 0

    def test_intermediate_dagger_gate_names(self):
        """Intermediate arithmetic dagger lowers to inverse QEC gate names."""
        from pyqres.primitives import ADD, MOD_ADD, MOD_MUL, PLUS_ONE

        _declare_reg("a", 2, "UnsignedInteger")
        _declare_reg("b", 2, "UnsignedInteger")
        _declare_reg("x", 4, "UnsignedInteger")

        add_circuit = _to_circuit(ADD(reg_list=["a", "b"], param_list=[2]).dagger())
        assert [g.name for g in add_circuit.gates] == ["ADD_DAG"]

        inc_circuit = _to_circuit(PLUS_ONE(reg_list=["a"], param_list=[2]).dagger())
        assert [g.name for g in inc_circuit.gates] == ["PLUS_ONE_DAG"]

        mod_add_circuit = _to_circuit(MOD_ADD(reg_list=["a", "b"], param_list=[3]).dagger())
        assert [g.name for g in mod_add_circuit.gates] == ["MOD_SUB"]

        mod_mul_circuit = _to_circuit(MOD_MUL(reg_list=["x"], param_list=[2, 15]).dagger())
        assert [g.name for g in mod_mul_circuit.gates] == ["MOD_MUL"]
        assert mod_mul_circuit.gates[0].params == (8.0, 15.0)

    def test_controlled_mod_mul_lowers_to_controlled_intermediate(self):
        """Controlled MOD_MUL remains explicit for QEC arithmetic lowering."""
        from pyqres.primitives import MOD_MUL
        from qec_compiler.decomposition import lower_to_logical

        _declare_reg("ctrl", 1, "Boolean")
        _declare_reg("x", 4, "UnsignedInteger")
        op = MOD_MUL(reg_list=["x"], param_list=[2, 15]).control_by_all_ones("ctrl")
        circuit = _to_circuit(op)

        assert [g.name for g in circuit.gates] == ["CMOD_MUL"]
        assert circuit.gates[0].params == (2.0, 15.0, 1.0)
        assert lower_to_logical(circuit).ccz_inject_count > 0

    def test_control_by_value_zero_bit_uses_x_sandwich(self):
        """Value controls on zero bits are preserved with X sandwiches."""
        from pyqres.primitives import MOD_MUL

        _declare_reg("ctrl", 1, "Boolean")
        _declare_reg("x", 4, "UnsignedInteger")
        op = MOD_MUL(reg_list=["x"], param_list=[2, 15]).control_by_value({"ctrl": 0})
        circuit = _to_circuit(op)

        assert [g.name for g in circuit.gates] == ["X", "CMOD_MUL", "X"]
        assert circuit.gates[0].qubits == circuit.gates[2].qubits == (0,)

    def test_mcx_4_controls_compiles(self):
        """MCX with 4 controls compiles with ancilla."""
        from qec_compiler.decomposition import lower_to_logical
        from qec_compiler.ir import AbstractCircuit, AbstractGate

        circuit = AbstractCircuit(
            num_qubits=5,
            gates=(AbstractGate(name="MCX", qubits=(0, 1, 2, 3, 4)),),
        )
        logical = lower_to_logical(circuit)
        assert logical.ccz_inject_count > 0


# ---------------------------------------------------------------------------
# BlockEncodingTridiagonal lowering test
# ---------------------------------------------------------------------------

class TestBlockEncodingLowering:
    def test_block_encoding_tridiagonal_produces_gates(self):
        """BlockEncodingTridiagonal lowers to recognized gate types."""
        from pyqres.algorithms.block_encoding import BlockEncodingTridiagonal
        _declare_reg("main", 2, "UnsignedInteger")
        _declare_reg("anc_UA", 4)

        op = BlockEncodingTridiagonal(
            main_reg="main", anc_UA="anc_UA", alpha=0.5, beta=0.3)

        circuit = _to_circuit(op)

        assert circuit.num_qubits > 0
        assert len(circuit.gates) > 0
        gate_names = {g.name for g in circuit.gates}
        # Should only contain recognized gate names
        recognized = {
            "H", "X", "Y", "Z", "S", "S_DAG", "T", "T_DAG",
            "CNOT", "CCX", "MCX", "SWAP", "RZ", "RY", "RX",
            "PHASE", "CPHASE", "REFLECT", "PLUS_ONE", "CPLUS_ONE",
            "PLUS_ONE_DAG", "CPLUS_ONE_DAG",
        }
        unknown = gate_names - recognized
        assert not unknown, f"Unknown gate names: {unknown}"


# ---------------------------------------------------------------------------
# QDA WalkS lowering test
# ---------------------------------------------------------------------------

class TestWalkSLowering:
    def test_walks_primitive_lowers(self):
        """WalkS_Primitive with Hadamard fallback lowers to recognized gates."""
        from pyqres.algorithms.qda_solver import WalkS_Primitive
        _declare_reg("main", 2, "UnsignedInteger")
        _declare_reg("anc_UA", 2)
        _declare_reg("anc_1", 1)
        _declare_reg("anc_2", 1)
        _declare_reg("anc_3", 1)
        _declare_reg("anc_4", 1)

        op = WalkS_Primitive(
            reg_list=["main", "anc_UA", "anc_1", "anc_2", "anc_3", "anc_4"],
            param_list=[0.5])

        circuit = _to_circuit(op)

        assert circuit.num_qubits > 0
        assert len(circuit.gates) > 0
        gate_names = {g.name for g in circuit.gates}
        recognized = {
            "H", "X", "Y", "Z", "S", "S_DAG", "T", "T_DAG",
            "CNOT", "CCX", "MCX", "SWAP", "RZ", "RY", "RX",
            "PHASE", "CPHASE", "REFLECT",
        }
        unknown = gate_names - recognized
        assert not unknown, f"Unknown gate names: {unknown}"

    def test_walks_primitive_compiles(self):
        """WalkS_Primitive compiles through the full QEC pipeline."""
        from pyqres.algorithms.qda_solver import WalkS_Primitive
        from qec_compiler.decomposition import lower_to_logical
        _declare_reg("main", 2, "UnsignedInteger")
        _declare_reg("anc_UA", 2)
        _declare_reg("anc_1", 1)
        _declare_reg("anc_2", 1)
        _declare_reg("anc_3", 1)
        _declare_reg("anc_4", 1)

        op = WalkS_Primitive(
            reg_list=["main", "anc_UA", "anc_1", "anc_2", "anc_3", "anc_4"],
            param_list=[0.5])

        circuit = _to_circuit(op)
        logical = lower_to_logical(circuit)
        assert logical.ccz_inject_count > 0

    def test_walks_with_tridiagonal_compiles(self):
        """WalkS_Primitive with BlockEncodingTridiagonal compiles through pipeline."""
        from pyqres.algorithms.qda_solver import WalkS_Primitive
        from pyqres.algorithms.block_encoding import BlockEncodingTridiagonal
        from qec_compiler.decomposition import lower_to_logical
        _declare_reg("main", 2, "UnsignedInteger")
        _declare_reg("anc_UA", 4)
        _declare_reg("anc_1", 1)
        _declare_reg("anc_2", 1)
        _declare_reg("anc_3", 1)
        _declare_reg("anc_4", 1)

        def make_enc_A(reg_list=None, param_list=None):
            return BlockEncodingTridiagonal(
                main_reg="main", anc_UA="anc_UA", alpha=0.5, beta=0.3)

        op = WalkS_Primitive(
            reg_list=["main", "anc_UA", "anc_1", "anc_2", "anc_3", "anc_4"],
            param_list=[0.5],
            submodules=[make_enc_A])

        circuit = _to_circuit(op)
        logical = lower_to_logical(circuit)
        assert logical.ccz_inject_count > 0
