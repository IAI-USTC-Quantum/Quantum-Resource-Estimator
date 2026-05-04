"""QDA tridiagonal workflow tests at multiple matrix sizes.

Covers main_bits = 1, 2, 3 (matrix sizes 2x2, 4x4, 8x8).
Each size must:
  1. Construct a QDALinearSolver with BlockEncodingTridiagonal
  2. Lower to QEC-Compiler AbstractCircuit
  3. Compile through QEC-Compiler lower_to_logical
  4. Record gate counts and qubit counts

This is the QDA tridiagonal work package (WP-A) from stage-execution-plan.
"""

from __future__ import annotations

import pytest

pytest.importorskip(
    "qec_compiler",
    reason="qec_compiler is required for QDA tridiagonal tests",
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


def _make_qda_tridiagonal(main_bits, alpha=0.5, beta=0.3, kappa=2.0, epsilon=0.1):
    """Construct a QDALinearSolver with BlockEncodingTridiagonal."""
    from pyqres.algorithms.block_encoding import BlockEncodingTridiagonal
    from pyqres.generated import QDALinearSolver

    # Register layout: main + anc_UA + 4 boolean ancillas
    main_reg = "main_reg"
    anc_UA = "anc_UA"
    anc_1, anc_2, anc_3, anc_4 = "anc_1", "anc_2", "anc_3", "anc_4"

    _declare_reg(main_reg, main_bits, "UnsignedInteger")
    # anc_UA is always 4: after SplitRegister takes 2 qubits
    # (_overflow=1, _other=1), the remaining 2 qubits hold the 4-element
    # state-preparation vector for BlockEncodingTridiagonal.
    _declare_reg(anc_UA, 4, "UnsignedInteger")
    _declare_reg(anc_1, 1, "Boolean")
    _declare_reg(anc_2, 1, "Boolean")
    _declare_reg(anc_3, 1, "Boolean")
    _declare_reg(anc_4, 1, "Boolean")

    def encode_a(reg_list=None, param_list=None):
        return BlockEncodingTridiagonal(
            main_reg=reg_list[0],
            anc_UA=reg_list[1],
            alpha=alpha,
            beta=beta,
        )

    return QDALinearSolver(
        reg_list=[main_reg, anc_UA, anc_1, anc_2, anc_3, anc_4],
        param_list=[kappa, epsilon],
        operations=[encode_a, None],  # encode_A, encode_b=None
    )


# ---------------------------------------------------------------------------
# QDA tridiagonal at multiple sizes
# ---------------------------------------------------------------------------

class TestQDATridiagonalSizes:
    @pytest.mark.parametrize("main_bits", [1, 2, 3])
    def test_qda_tridiagonal_lowers_to_abstract_circuit(self, main_bits):
        """QDA tridiagonal lowers to AbstractCircuit for given main_bits."""
        from pyqres.core.lowering import to_abstract_circuit

        op = _make_qda_tridiagonal(main_bits)
        circuit = to_abstract_circuit(op)

        assert circuit.num_qubits > 0
        assert len(circuit.gates) > 0

    @pytest.mark.parametrize("main_bits", [1, 2, 3])
    def test_qda_tridiagonal_compiles_through_qec(self, main_bits):
        """QDA tridiagonal compiles through QEC-Compiler pipeline."""
        from pyqres.core.lowering import to_abstract_circuit
        from qec_compiler.decomposition import lower_to_logical

        op = _make_qda_tridiagonal(main_bits)
        circuit = to_abstract_circuit(op)
        logical = lower_to_logical(circuit)

        assert logical.ccz_inject_count is not None

    @pytest.mark.parametrize("main_bits", [1, 2, 3])
    def test_qda_tridiagonal_gate_names_recognized(self, main_bits):
        """All gate names in QDA tridiagonal output are recognized by QEC."""
        from pyqres.core.lowering import to_abstract_circuit

        op = _make_qda_tridiagonal(main_bits)
        circuit = to_abstract_circuit(op)

        gate_names = {g.name for g in circuit.gates}
        recognized = {
            "H", "X", "Y", "Z", "S", "S_DAG", "T", "T_DAG",
            "CNOT", "CCX", "MCX", "SWAP", "RZ", "RY", "RX",
            "PHASE", "CPHASE", "REFLECT",
            "PLUS_ONE", "CPLUS_ONE", "PLUS_ONE_DAG", "CPLUS_ONE_DAG",
            "ADD", "ADD_DAG", "CADD", "CADD_DAG",
            "MOD_ADD", "MOD_SUB", "CMOD_ADD", "CMOD_SUB",
        }
        unknown = gate_names - recognized
        assert not unknown, f"Unknown gate names at main_bits={main_bits}: {unknown}"


# ---------------------------------------------------------------------------
# Resource reporting (gate/qubit counts for documentation)
# ---------------------------------------------------------------------------

class TestQDATridiagonalResourceReport:
    def test_record_resource_counts(self, capsys):
        """Record gate counts and qubit counts for all sizes."""
        from pyqres.core.lowering import to_abstract_circuit
        from collections import Counter

        results = []
        for main_bits in [1, 2, 3]:
            # Reset metadata between sizes so registers can be redeclared
            while len(RegisterMetadata.register_metadata_stack) > 0:
                RegisterMetadata.pop_register_metadata()
            RegisterMetadata.push_register_metadata()

            op = _make_qda_tridiagonal(main_bits)
            circuit = to_abstract_circuit(op)
            gate_counts = Counter(g.name for g in circuit.gates)

            results.append({
                "main_bits": main_bits,
                "matrix_size": f"{2**main_bits}x{2**main_bits}",
                "num_qubits": circuit.num_qubits,
                "total_gates": len(circuit.gates),
                "gate_counts": dict(sorted(gate_counts.items())),
            })

        # Print for documentation
        for r in results:
            print(f"\n--- {r['matrix_size']} (main_bits={r['main_bits']}) ---")
            print(f"  Qubits: {r['num_qubits']}")
            print(f"  Total gates: {r['total_gates']}")
            for name, count in r["gate_counts"].items():
                print(f"    {name}: {count}")

        # Basic sanity: larger sizes should have more qubits and gates
        assert results[0]["num_qubits"] < results[1]["num_qubits"]
        assert results[1]["num_qubits"] < results[2]["num_qubits"]
        assert results[0]["total_gates"] < results[2]["total_gates"]
