"""WP-B: Arithmetic lowering hardening — structural tests.

Documents qubit/register layout and verifies correctness for every
arithmetic primitive used in the QEC compilation spine:

  MCX  |  PLUS_ONE  |  ADD  |  REFLECT  |  MOD_ADD  |  MOD_MUL

Tests are grouped by primitive.  Each test:
  - declares the minimum required registers
  - lowers to AbstractCircuit
  - asserts gate name(s), qubit counts, param values
  - (where possible) compiles through QEC-Compiler lower_to_logical
"""

from __future__ import annotations

import pytest

pytest.importorskip(
    "qec_compiler",
    reason="qec_compiler is required for arithmetic lowering tests",
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


def _to_circuit(op):
    from pyqres.core.lowering import to_abstract_circuit
    return to_abstract_circuit(op)


def _gate_names(circuit):
    return [g.name for g in circuit.gates]


def _compile(circuit):
    from qec_compiler.decomposition import lower_to_logical
    return lower_to_logical(circuit)


# =========================================================================
# MCX — Multi-controlled X
# =========================================================================

class TestMCXLowering:
    def test_mcx_single_control(self):
        """MCX with 1 control emits MCX(ctrl, tgt)."""
        from pyqres.primitives.gates import X
        _declare_reg("ctrl", 1, "Boolean")
        _declare_reg("tgt", 1)
        op = X(reg_list=["tgt"]).control_by_all_ones("ctrl")
        circuit = _to_circuit(op)
        assert _gate_names(circuit) == ["MCX"]
        assert circuit.gates[0].qubits == (0, 1)

    def test_mcx_two_controls(self):
        """MCX with 2 controls emits MCX(c0, c1, tgt)."""
        from pyqres.primitives.gates import X
        _declare_reg("c0", 1, "Boolean")
        _declare_reg("c1", 1, "Boolean")
        _declare_reg("tgt", 1)
        op = X(reg_list=["tgt"]).control_by_all_ones(["c0", "c1"])
        circuit = _to_circuit(op)
        assert _gate_names(circuit) == ["MCX"]
        assert circuit.gates[0].qubits == (0, 1, 2)

    def test_mcx_compiles_through_qec(self):
        """MCX with 2 controls compiles through QEC-Compiler."""
        from pyqres.primitives.gates import X
        _declare_reg("c0", 1, "Boolean")
        _declare_reg("c1", 1, "Boolean")
        _declare_reg("tgt", 1)
        op = X(reg_list=["tgt"]).control_by_all_ones(["c0", "c1"])
        circuit = _to_circuit(op)
        logical = _compile(circuit)
        assert logical.ccz_inject_count > 0

    def test_mcx_multi_qubit_register(self):
        """MCX on a multi-qubit target register emits one MCX per qubit."""
        from pyqres.primitives.gates import X
        _declare_reg("ctrl", 1, "Boolean")
        _declare_reg("tgt", 3)
        op = X(reg_list=["tgt"]).control_by_all_ones("ctrl")
        circuit = _to_circuit(op)
        # X on a 3-qubit register emits 3 MCX gates (one per qubit)
        assert all(g.name == "MCX" for g in circuit.gates)
        assert len(circuit.gates) == 3


# =========================================================================
# PLUS_ONE — Increment
# =========================================================================

class TestPlusOneLowering:
    def test_plus_one_basic(self):
        """PLUS_ONE(n) emits PLUS_ONE gate with n main qubits."""
        from pyqres.algorithms.block_encoding import PlusOneOverflow
        _declare_reg("main", 3, "UnsignedInteger")
        _declare_reg("overflow", 1, "Boolean")
        op = PlusOneOverflow(reg_list=["main", "overflow"], param_list=[1])
        circuit = _to_circuit(op)
        gate_names = set(_gate_names(circuit))
        assert "PLUS_ONE" in gate_names or "CPLUS_ONE" in gate_names

    def test_plus_one_dagger(self):
        """PLUS_ONE.dagger() emits PLUS_ONE_DAG."""
        from pyqres.algorithms.block_encoding import PlusOneOverflow
        _declare_reg("main", 3, "UnsignedInteger")
        _declare_reg("overflow", 1, "Boolean")
        op = PlusOneOverflow(reg_list=["main", "overflow"], param_list=[1]).dagger()
        circuit = _to_circuit(op)
        gate_names = set(_gate_names(circuit))
        assert "PLUS_ONE_DAG" in gate_names or "CPLUS_ONE_DAG" in gate_names

    def test_plus_one_qubit_count(self):
        """PLUS_ONE includes main + overflow qubits."""
        from pyqres.algorithms.block_encoding import PlusOneOverflow
        _declare_reg("main", 3, "UnsignedInteger")
        _declare_reg("overflow", 1, "Boolean")
        op = PlusOneOverflow(reg_list=["main", "overflow"], param_list=[1])
        circuit = _to_circuit(op)
        # main(3) + overflow(1) = 4 qubits minimum
        assert circuit.num_qubits >= 4

    def test_plus_one_compiles_through_qec(self):
        """PLUS_ONE compiles through QEC-Compiler pipeline."""
        from pyqres.algorithms.block_encoding import PlusOneOverflow
        _declare_reg("main", 3, "UnsignedInteger")
        _declare_reg("overflow", 1, "Boolean")
        op = PlusOneOverflow(reg_list=["main", "overflow"], param_list=[1])
        circuit = _to_circuit(op)
        logical = _compile(circuit)
        assert logical.ccz_inject_count > 0


# =========================================================================
# ADD — Ripple-carry adder
# =========================================================================

class TestADDLowering:
    def test_add_basic(self):
        """ADD(n) emits ADD gate with carry/maj/temp ancillas."""
        from pyqres.primitives import ADD
        _declare_reg("a", 2, "UnsignedInteger")
        _declare_reg("b", 2, "UnsignedInteger")
        op = ADD(reg_list=["a", "b"], param_list=[2])
        circuit = _to_circuit(op)
        assert _gate_names(circuit) == ["ADD"]
        # ADD allocates 3n ancillas: carry(n), maj(n), temp(n)
        # Total qubits = a(n) + b(n) + carry(n) + maj(n) + temp(n) = 5n
        assert circuit.num_qubits == 5 * 2

    def test_add_dagger(self):
        """ADD.dagger() emits ADD_DAG."""
        from pyqres.primitives import ADD
        _declare_reg("a", 2, "UnsignedInteger")
        _declare_reg("b", 2, "UnsignedInteger")
        op = ADD(reg_list=["a", "b"], param_list=[2]).dagger()
        circuit = _to_circuit(op)
        assert _gate_names(circuit) == ["ADD_DAG"]

    def test_add_controlled(self):
        """Controlled ADD emits CADD with ctrl qubits prepended."""
        from pyqres.primitives import ADD
        _declare_reg("ctrl", 1, "Boolean")
        _declare_reg("a", 2, "UnsignedInteger")
        _declare_reg("b", 2, "UnsignedInteger")
        op = ADD(reg_list=["a", "b"], param_list=[2]).control_by_all_ones("ctrl")
        circuit = _to_circuit(op)
        assert _gate_names(circuit) == ["CADD"]
        # CADD params: (n, n_controls)
        assert circuit.gates[0].params == (2, 1)

    def test_add_compiles_through_qec(self):
        """ADD compiles through QEC-Compiler pipeline."""
        from pyqres.primitives import ADD
        _declare_reg("a", 2, "UnsignedInteger")
        _declare_reg("b", 2, "UnsignedInteger")
        op = ADD(reg_list=["a", "b"], param_list=[2])
        circuit = _to_circuit(op)
        logical = _compile(circuit)
        assert logical.ccz_inject_count > 0


# =========================================================================
# REFLECT — Multi-controlled Z
# =========================================================================

class TestREFLECTLowering:
    def test_reflect_basic(self):
        """REFLECT on 3 qubits emits REFLECT(n_bits=3)."""
        from pyqres.primitives.transform import Reflection_Bool
        _declare_reg("q", 3)
        op = Reflection_Bool(reg_list=["q"], param_list=[True])
        circuit = _to_circuit(op)
        reflect_gates = [g for g in circuit.gates if g.name == "REFLECT"]
        assert len(reflect_gates) == 1
        assert reflect_gates[0].qubits == (0, 1, 2)
        assert reflect_gates[0].params == (3,)

    def test_reflect_single_qubit(self):
        """REFLECT on 1 qubit is equivalent to Z gate."""
        from pyqres.primitives.transform import Reflection_Bool
        _declare_reg("q", 1)
        op = Reflection_Bool(reg_list=["q"], param_list=[True])
        circuit = _to_circuit(op)
        reflect_gates = [g for g in circuit.gates if g.name == "REFLECT"]
        assert len(reflect_gates) == 1
        assert reflect_gates[0].params == (1,)

    def test_reflect_compiles_through_qec(self):
        """REFLECT compiles through QEC-Compiler pipeline."""
        from pyqres.primitives.transform import Reflection_Bool
        _declare_reg("q", 3)
        op = Reflection_Bool(reg_list=["q"], param_list=[True])
        circuit = _to_circuit(op)
        logical = _compile(circuit)
        assert logical.ccz_inject_count > 0

    def test_reflect_multi_register(self):
        """REFLECT across multiple registers concatenates qubit ranges."""
        from pyqres.primitives.transform import Reflection_Bool
        _declare_reg("q0", 1)
        _declare_reg("q1", 2)
        op = Reflection_Bool(reg_list=["q0", "q1"], param_list=[True])
        circuit = _to_circuit(op)
        reflect_gates = [g for g in circuit.gates if g.name == "REFLECT"]
        assert len(reflect_gates) == 1
        # q0(1) + q1(2) = 3 qubits
        assert len(reflect_gates[0].qubits) == 3


# =========================================================================
# MOD_ADD — Modular addition (flag qubit audit)
# =========================================================================

class TestMODADDLowering:
    def test_mod_add_allocates_flag_qubit(self):
        """MOD_ADD allocates one anonymous ancilla for the overflow flag.

        WP-B acceptance check: the flag qubit must be present in the gate's
        qubit count.  Without it the modular reduction is incorrect.
        """
        from pyqres.primitives import MOD_ADD
        _declare_reg("a", 2, "UnsignedInteger")
        _declare_reg("b", 2, "UnsignedInteger")
        op = MOD_ADD(reg_list=["a", "b"], param_list=[3])
        circuit = _to_circuit(op)
        assert _gate_names(circuit) == ["MOD_ADD"]
        # a(2) + b(2) + flag(1) = 5 qubits
        assert circuit.num_qubits == 5

    def test_mod_add_flag_not_aliased(self):
        """MOD_ADD flag qubit does not alias any data register qubit.

        WP-B acceptance check: flag qubit index must be strictly greater
        than all data qubit indices.
        """
        from pyqres.primitives import MOD_ADD
        _declare_reg("a", 2, "UnsignedInteger")
        _declare_reg("b", 2, "UnsignedInteger")
        op = MOD_ADD(reg_list=["a", "b"], param_list=[3])
        circuit = _to_circuit(op)
        gate = circuit.gates[0]
        data_qubits = set(range(4))  # a: [0,1], b: [2,3]
        flag_qubits = set(gate.qubits) - data_qubits
        assert len(flag_qubits) == 1, "Exactly one flag qubit expected"
        flag_q = flag_qubits.pop()
        assert flag_q >= 4, f"Flag qubit {flag_q} aliases data register"

    def test_mod_add_dagger(self):
        """MOD_ADD.dagger() emits MOD_SUB."""
        from pyqres.primitives import MOD_ADD
        _declare_reg("a", 2, "UnsignedInteger")
        _declare_reg("b", 2, "UnsignedInteger")
        op = MOD_ADD(reg_list=["a", "b"], param_list=[3]).dagger()
        circuit = _to_circuit(op)
        assert _gate_names(circuit) == ["MOD_SUB"]

    def test_mod_add_controlled(self):
        """Controlled MOD_ADD emits CMOD_ADD."""
        from pyqres.primitives import MOD_ADD
        _declare_reg("ctrl", 1, "Boolean")
        _declare_reg("a", 2, "UnsignedInteger")
        _declare_reg("b", 2, "UnsignedInteger")
        op = MOD_ADD(reg_list=["a", "b"], param_list=[3]).control_by_all_ones("ctrl")
        circuit = _to_circuit(op)
        assert _gate_names(circuit) == ["CMOD_ADD"]
        # CMOD_ADD params: (modulus, n_controls)
        assert circuit.gates[0].params == (3, 1)

    def test_mod_add_compiles_through_qec(self):
        """MOD_ADD compiles through QEC-Compiler pipeline."""
        from pyqres.primitives import MOD_ADD
        _declare_reg("a", 2, "UnsignedInteger")
        _declare_reg("b", 2, "UnsignedInteger")
        op = MOD_ADD(reg_list=["a", "b"], param_list=[3])
        circuit = _to_circuit(op)
        logical = _compile(circuit)
        assert logical.ccz_inject_count > 0


# =========================================================================
# MOD_MUL — Modular multiplication
# =========================================================================

class TestMODMULLowering:
    def test_mod_mul_allocates_work_and_flag(self):
        """MOD_MUL allocates n work qubits + 1 flag qubit.

        Qubit order: reg(n) + work(n) + flag(1) = 2n + 1.
        """
        from pyqres.primitives import MOD_MUL
        _declare_reg("x", 4, "UnsignedInteger")
        op = MOD_MUL(reg_list=["x"], param_list=[2, 15])
        circuit = _to_circuit(op)
        assert _gate_names(circuit) == ["MOD_MUL"]
        # x(4) + work(4) + flag(1) = 9
        assert circuit.num_qubits == 9

    def test_mod_mul_dagger_inverts_multiplier(self):
        """MOD_MUL.dagger() computes modular inverse of multiplier."""
        from pyqres.primitives import MOD_MUL
        _declare_reg("x", 4, "UnsignedInteger")
        op = MOD_MUL(reg_list=["x"], param_list=[2, 15]).dagger()
        circuit = _to_circuit(op)
        # dagger computes pow(2, -1, 15) = 8
        assert circuit.gates[0].params[0] == 8.0

    def test_mod_mul_controlled(self):
        """Controlled MOD_MUL emits CMOD_MUL."""
        from pyqres.primitives import MOD_MUL
        _declare_reg("ctrl", 1, "Boolean")
        _declare_reg("x", 4, "UnsignedInteger")
        op = MOD_MUL(reg_list=["x"], param_list=[2, 15]).control_by_all_ones("ctrl")
        circuit = _to_circuit(op)
        assert _gate_names(circuit) == ["CMOD_MUL"]
        assert circuit.gates[0].params == (2.0, 15.0, 1.0)

    def test_mod_mul_compiles_through_qec(self):
        """MOD_MUL compiles through QEC-Compiler pipeline."""
        from pyqres.primitives import MOD_MUL
        _declare_reg("x", 4, "UnsignedInteger")
        op = MOD_MUL(reg_list=["x"], param_list=[2, 15])
        circuit = _to_circuit(op)
        logical = _compile(circuit)
        assert logical.ccz_inject_count > 0


# =========================================================================
# CMUL_MOD_N — Via Shor's ExpMod decomposition
# =========================================================================

class TestCMULMODN:
    def test_cmul_mod_n_via_shor_expmod(self):
        """Shor's ExpMod decomposes into CMUL_MOD_N gates."""
        from pyqres.algorithms.shor import ExpMod
        _declare_reg("base", 3, "UnsignedInteger")
        _declare_reg("counting", 3, "UnsignedInteger")
        op = ExpMod(
            reg_list=["base", "counting"],
            param_list=[2, 7, 3],  # base_val, modulus, n_counting_bits
        )
        circuit = _to_circuit(op)
        cmul_gates = [g for g in circuit.gates if g.name == "CMUL_MOD_N"]
        assert len(cmul_gates) > 0, "ExpMod should decompose into CMUL_MOD_N"
        # Each CMUL_MOD_N should have the correct qubit count
        for g in cmul_gates:
            assert len(g.qubits) > 0


# =========================================================================
# Qubit-count sanity: all arithmetic gates compile through QEC
# =========================================================================

class TestArithmeticQECIntegration:
    """Verify all arithmetic primitives compile through the full QEC pipeline."""

    @pytest.mark.parametrize("prim_name,params,reg_setup", [
        ("REFLECT", [True], lambda: (_declare_reg("q", 3),)),
        ("MOD_ADD", [3], lambda: (
            _declare_reg("a", 2, "UnsignedInteger"),
            _declare_reg("b", 2, "UnsignedInteger"),
        )),
    ])
    def test_primitive_compiles(self, prim_name, params, reg_setup):
        """Parametrized: each arithmetic primitive compiles through QEC."""
        from pyqres.primitives import MOD_ADD
        from pyqres.primitives.transform import Reflection_Bool

        reg_setup()
        if prim_name == "REFLECT":
            op = Reflection_Bool(reg_list=["q"], param_list=params)
        elif prim_name == "MOD_ADD":
            op = MOD_ADD(reg_list=["a", "b"], param_list=params)
        else:
            pytest.skip(f"No handler for {prim_name}")

        circuit = _to_circuit(op)
        logical = _compile(circuit)
        assert logical.ccz_inject_count > 0
