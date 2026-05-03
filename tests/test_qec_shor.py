"""Integration tests for Shor N=15 through the pyqres -> QEC-compiler pipeline.

Tests two compilation paths:
  1. QEC-compiler's built-in Shor fixture -> lower_to_logical -> LogicalCircuit
  2. pyqres Shor(N=15) -> QECLoweringVisitor -> AbstractCircuit -> lower_to_logical

Also tests MOD_MUL and MOD_ADD intermediate primitives through the pipeline.
"""

from __future__ import annotations

import pytest

pytest.importorskip(
    "qec_compiler",
    reason="qec_compiler is required for QEC integration tests",
)

from pyqres.core.metadata import RegisterMetadata


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
    RegisterMetadata.get_register_metadata().declare_register(name, size, reg_type)


# ---------------------------------------------------------------------------
# QEC-compiler Shor fixture compilation
# ---------------------------------------------------------------------------

class TestShorFixtureCompilation:
    """Test QEC-compiler's built-in Shor fixture compiles through the pipeline."""

    def test_shor_n15_compiles(self):
        from qec_compiler.cases.benchmark_shor import build_stage5_small_shor_fixture
        from qec_compiler.decomposition import lower_to_logical

        circuit = build_stage5_small_shor_fixture(modulus=15, base=2)
        logical = lower_to_logical(circuit)

        assert logical.ccz_inject_count > 0

    def test_shor_n21_compiles(self):
        from qec_compiler.cases.benchmark_shor import build_stage5_small_shor_fixture
        from qec_compiler.decomposition import lower_to_logical

        circuit = build_stage5_small_shor_fixture(modulus=21, base=2)
        logical = lower_to_logical(circuit)

        assert logical.ccz_inject_count > 0

    def test_shor_n15_gate_structure(self):
        from qec_compiler.cases.benchmark_shor import build_stage5_small_shor_fixture

        circuit = build_stage5_small_shor_fixture(modulus=15, base=2)
        gate_names = {g.name for g in circuit.gates}

        assert "H" in gate_names
        assert "CMUL_MOD_N" in gate_names
        assert "X" in gate_names  # init work register to |1>

    def test_shor_n15_pipeline_decomposes_cmul(self):
        from qec_compiler.cases.benchmark_shor import build_stage5_small_shor_fixture
        from qec_compiler.decomposition.cmul_to_mcx_pass import lower_cmul_mod_n
        from qec_compiler.decomposition.mcx_to_ccx_pass import lower_mcx

        circuit = build_stage5_small_shor_fixture(modulus=15, base=2)

        # Pass 1: CMUL_MOD_N -> MCX
        after_cmul = lower_cmul_mod_n(circuit)
        gate_names = {g.name for g in after_cmul.gates}
        assert "CMUL_MOD_N" not in gate_names
        assert "MCX" in gate_names

        # Pass 2: MCX -> CCX
        after_mcx = lower_mcx(after_cmul)
        gate_names = {g.name for g in after_mcx.gates}
        assert "MCX" not in gate_names


# ---------------------------------------------------------------------------
# Intermediate primitive compilation (MOD_MUL, MOD_ADD)
# ---------------------------------------------------------------------------

class TestModularArithmeticCompilation:

    def test_mod_mul_compiles(self):
        from qec_compiler.ir import AbstractCircuit, AbstractGate
        from qec_compiler.decomposition import lower_to_logical

        circuit = AbstractCircuit(
            num_qubits=9,
            gates=(AbstractGate(name="MOD_MUL", qubits=tuple(range(9)), params=(2, 15)),),
        )
        logical = lower_to_logical(circuit)
        assert logical.ccz_inject_count > 0

    def test_mod_add_compiles(self):
        from qec_compiler.ir import AbstractCircuit, AbstractGate
        from qec_compiler.decomposition import lower_to_logical

        circuit = AbstractCircuit(
            num_qubits=5,
            gates=(AbstractGate(name="MOD_ADD", qubits=(0, 1, 2, 3, 4), params=(3,)),),
        )
        logical = lower_to_logical(circuit)
        assert logical.ccz_inject_count > 0


# ---------------------------------------------------------------------------
# pyqres Shor lowering -> QEC compilation
# ---------------------------------------------------------------------------

class TestPyqresShorLowering:

    def test_expmod_lowers_to_cmul(self):
        """ExpMod lowers to X(init) + CMUL_MOD_N gates."""
        from pyqres.algorithms.shor import ExpMod
        from pyqres.core.qec_lowering import QECLoweringVisitor

        _declare_reg("work", 8, "UnsignedInteger")
        _declare_reg("anc", 4, "UnsignedInteger")

        expmod = ExpMod(
            reg_list=["work", "anc"],
            param_list=[2, 15, 4])

        v = QECLoweringVisitor()
        circuit = v.build_circuit(expmod)

        gate_names = [g.name for g in circuit.gates]
        assert "X" in gate_names  # init anc to |1>
        assert "CMUL_MOD_N" in gate_names
        cmul_count = gate_names.count("CMUL_MOD_N")
        assert cmul_count == 8  # one per counting bit (2n = 8)

    def test_expmod_cmul_multipliers(self):
        """CMUL_MOD_N gates have correct multiplier sequence."""
        from pyqres.algorithms.shor import ExpMod
        from pyqres.core.qec_lowering import QECLoweringVisitor

        _declare_reg("work", 8, "UnsignedInteger")
        _declare_reg("anc", 4, "UnsignedInteger")

        expmod = ExpMod(
            reg_list=["work", "anc"],
            param_list=[2, 15, 4])

        v = QECLoweringVisitor()
        circuit = v.build_circuit(expmod)

        cmul_gates = [g for g in circuit.gates if g.name == "CMUL_MOD_N"]
        multipliers = [g.params[0] for g in cmul_gates]
        # a=2, N=15: multipliers should be 2, 4, 8, 1, 2, 4, 8, 1
        expected = [pow(2, 2**k, 15) for k in range(8)]
        assert multipliers == expected

    def test_shor_full_quantum_lowers(self):
        """Full quantum Shor(N=15) lowers to AbstractCircuit."""
        from pyqres.algorithms.shor import Shor
        from pyqres.core.qec_lowering import QECLoweringVisitor

        _declare_reg("work", 8, "UnsignedInteger")
        _declare_reg("anc", 4, "UnsignedInteger")

        shor = Shor(reg_list=["work", "anc"], param_list=[2, 15, 4])

        v = QECLoweringVisitor()
        circuit = v.build_circuit(shor)

        assert circuit.num_qubits == 12  # 8 + 4
        assert len(circuit.gates) > 0
        gate_names = {g.name for g in circuit.gates}
        assert "H" in gate_names
        assert "CMUL_MOD_N" in gate_names

    def test_shor_compiles_through_pipeline(self):
        """Full quantum Shor(N=15) compiles through QEC pipeline."""
        from pyqres.algorithms.shor import Shor
        from pyqres.core.qec_lowering import QECLoweringVisitor
        from qec_compiler.decomposition import lower_to_logical

        _declare_reg("work", 8, "UnsignedInteger")
        _declare_reg("anc", 4, "UnsignedInteger")

        shor = Shor(reg_list=["work", "anc"], param_list=[2, 15, 4])

        v = QECLoweringVisitor()
        circuit = v.build_circuit(shor)
        logical = lower_to_logical(circuit)

        assert logical.ccz_inject_count > 0
