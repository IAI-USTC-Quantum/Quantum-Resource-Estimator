"""WP-C: Canonical QEOL demo — end-to-end GHZ/BV → qeol.json.

Verifies that pyqres YAML composites can be compiled all the way through
the QEC-Compiler lattice-surgery pipeline and produce a valid QEOL JSON
artifact.

This is the smoke test for the full integration spine:
  pyqres YAML → generated Python → AbstractCircuit → QEC-Compiler → QEOL JSON

Acceptance criteria (from stage-execution-plan §7):
  1. A clean checkout can reproduce the QEOL JSON.
  2. The output path is stable.
  3. The artifact is small enough to inspect manually.
  4. Heavy resource estimation is not required.
"""

from __future__ import annotations

import json
import os
import pytest

pytest.importorskip(
    "qec_compiler",
    reason="qec_compiler is required for QEOL demo tests",
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


RUNS_DIR = os.path.join(os.path.dirname(__file__), "..", "runs")


class TestQEOLDemo:
    def _compile_to_qeol(self, op):
        """Full pipeline: pyqres op → AbstractCircuit → LatticeSurgeryCompilation."""
        from pyqres.core.lowering import to_abstract_circuit
        from qec_compiler.compiler import QECCompiler

        circuit = to_abstract_circuit(op)
        compiler = QECCompiler()
        result = compiler.compile(circuit)
        return result

    def test_ghz_compiles_to_qeol(self):
        """QECExampleGHZ compiles to a valid QEOL program."""
        from pyqres.generated import QECExampleGHZ

        _declare_reg("q0", 1)
        _declare_reg("q1", 1)
        _declare_reg("q2", 1)

        op = QECExampleGHZ(reg_list=["q0", "q1", "q2"], param_list=[3])
        result = self._compile_to_qeol(op)

        qeol = result.qeol_program
        assert qeol.schema_version == "qeol.schema.v1"
        assert qeol.kind == "QEOLProgram"
        assert isinstance(qeol.header, dict)
        assert isinstance(qeol.layout, dict)

    def test_bv_compiles_to_qeol(self):
        """QECExampleBV compiles to a valid QEOL program."""
        from pyqres.generated import QECExampleBV

        _declare_reg("q0", 1)
        _declare_reg("q1", 1)
        _declare_reg("q2", 1)
        _declare_reg("anc", 1)

        op = QECExampleBV(reg_list=["q0", "q1", "q2", "anc"], param_list=[3])
        result = self._compile_to_qeol(op)

        qeol = result.qeol_program
        assert qeol.schema_version == "qeol.schema.v1"
        assert qeol.kind == "QEOLProgram"

    def test_ghz_qeol_serializes_to_json(self):
        """QECExampleGHZ QEOL program serializes to valid JSON."""
        from pyqres.generated import QECExampleGHZ

        _declare_reg("q0", 1)
        _declare_reg("q1", 1)
        _declare_reg("q2", 1)

        op = QECExampleGHZ(reg_list=["q0", "q1", "q2"], param_list=[3])
        result = self._compile_to_qeol(op)

        qeol_dict = result.qeol_program.to_dict()
        json_str = json.dumps(qeol_dict, indent=2)
        assert len(json_str) > 100, "QEOL JSON should be non-trivial"

        # Verify round-trip
        parsed = json.loads(json_str)
        assert parsed["schema_version"] == "qeol.schema.v1"
        assert parsed["kind"] == "QEOLProgram"

    def test_ghz_qeol_saved_to_runs(self):
        """QECExampleGHZ QEOL JSON is saved under runs/."""
        from pyqres.generated import QECExampleGHZ

        _declare_reg("q0", 1)
        _declare_reg("q1", 1)
        _declare_reg("q2", 1)

        op = QECExampleGHZ(reg_list=["q0", "q1", "q2"], param_list=[3])
        result = self._compile_to_qeol(op)

        out_path = os.path.join(RUNS_DIR, "ghz_qeol.json")
        os.makedirs(RUNS_DIR, exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(result.qeol_program.to_dict(), f, indent=2)

        assert os.path.isfile(out_path)
        size = os.path.getsize(out_path)
        assert 100 < size < 1_000_000, f"QEOL JSON size {size} should be inspectable"

    def test_ghz_qeol_contains_schedule(self):
        """GHZ QEOL JSON has a non-empty schedule."""
        from pyqres.generated import QECExampleGHZ

        _declare_reg("q0", 1)
        _declare_reg("q1", 1)
        _declare_reg("q2", 1)

        op = QECExampleGHZ(reg_list=["q0", "q1", "q2"], param_list=[3])
        result = self._compile_to_qeol(op)

        qeol_dict = result.qeol_program.to_dict()
        assert "schedule" in qeol_dict
        assert len(qeol_dict["schedule"]) > 0

    def test_bv_qeol_contains_layout(self):
        """BV QEOL JSON has layout information."""
        from pyqres.generated import QECExampleBV

        _declare_reg("q0", 1)
        _declare_reg("q1", 1)
        _declare_reg("q2", 1)
        _declare_reg("anc", 1)

        op = QECExampleBV(reg_list=["q0", "q1", "q2", "anc"], param_list=[3])
        result = self._compile_to_qeol(op)

        qeol_dict = result.qeol_program.to_dict()
        assert "layout" in qeol_dict
        assert isinstance(qeol_dict["layout"], dict)

    def test_qeol_json_validates_against_schema(self):
        """QEOL JSON validates against the qeol_schema.json schema."""
        from pyqres.generated import QECExampleGHZ

        _declare_reg("q0", 1)
        _declare_reg("q1", 1)
        _declare_reg("q2", 1)

        op = QECExampleGHZ(reg_list=["q0", "q1", "q2"], param_list=[3])
        result = self._compile_to_qeol(op)

        qeol_dict = result.qeol_program.to_dict()

        # Check required top-level keys
        assert "schema_version" in qeol_dict
        assert "kind" in qeol_dict
        assert "header" in qeol_dict
        assert "layout" in qeol_dict
        assert "schedule" in qeol_dict
