"""Tests for interactive HTML visualizations."""

from __future__ import annotations

import pytest

from pyqres.core.metadata import RegisterMetadata
from pyqres.core.operation import StandardComposite
from pyqres.algorithms.block_encoding import BlockEncodingTridiagonal
from pyqres.generated import QDALinearSolver
from pyqres.primitives import CNOT, Hadamard, X
from pyqres.visualization import (
    operation_to_tree_data,
    render_call_tree_html,
    render_circuit_html,
    write_call_tree_html,
    write_circuit_html,
)


@pytest.fixture(autouse=True)
def clean_metadata():
    while len(RegisterMetadata.register_metadata_stack):
        RegisterMetadata.pop_register_metadata()
    RegisterMetadata.push_register_metadata()
    yield
    while len(RegisterMetadata.register_metadata_stack):
        RegisterMetadata.pop_register_metadata()
    RegisterMetadata.push_register_metadata()


class BellPair(StandardComposite):
    def __init__(self):
        super().__init__(reg_list=["ctrl", "target"])
        self.program_list = [
            Hadamard(["ctrl"]),
            CNOT(["ctrl", "target"], [0, 0]),
            X(["target"], [0]).control_by_all_ones("ctrl"),
        ]
        self.declare_program_list()


def _declare_regs():
    rm = RegisterMetadata.get_register_metadata()
    rm.declare_register("ctrl", 1)
    rm.declare_register("target", 1)


def _declare_qda_regs():
    rm = RegisterMetadata.get_register_metadata()
    rm.declare_register("main_reg", 2, "UnsignedInteger")
    rm.declare_register("anc_UA", 4, "UnsignedInteger")
    rm.declare_register("anc_1", 1, "Boolean")
    rm.declare_register("anc_2", 1, "Boolean")
    rm.declare_register("anc_3", 1, "Boolean")
    rm.declare_register("anc_4", 1, "Boolean")


def _make_tridiagonal_qda():
    def encode_a(reg_list=None, param_list=None):
        return BlockEncodingTridiagonal(
            main_reg=reg_list[0],
            anc_UA=reg_list[1],
            alpha=0.5,
            beta=0.3,
        )

    return QDALinearSolver(
        reg_list=["main_reg", "anc_UA", "anc_1", "anc_2", "anc_3", "anc_4"],
        param_list=[2.0, 0.5],
        operations=[encode_a, Hadamard],
    )


def test_operation_to_tree_data_contains_children_and_controls():
    _declare_regs()
    data = operation_to_tree_data(BellPair())

    assert data["root"]["name"] == "BellPair"
    assert [child["name"] for child in data["root"]["children"]] == [
        "Hadamard",
        "CNOT",
        "X",
    ]
    assert data["root"]["children"][2]["controllerRegisters"] == ["ctrl"]


def test_render_call_tree_html_is_standalone_and_expandable():
    _declare_regs()
    html = render_call_tree_html(BellPair())

    assert "<!doctype html>" in html
    assert "window.PYQRES_TREE_DATA" in html
    assert "<details" in html
    assert "BellPair" in html
    assert "Hadamard" in html


def test_render_circuit_html_has_sidebar_and_circuit_renderer():
    _declare_regs()
    html = render_circuit_html(BellPair())

    assert "Register circuit" in html
    assert "module-toggle" in html
    assert "circuit-grid" in html
    assert "flattenCircuit" in html
    assert "depth < maxDepth" in html
    assert "depth === 0" not in html


def test_write_visualization_files(tmp_path):
    _declare_regs()
    op = BellPair()

    call_tree_path = write_call_tree_html(op, tmp_path / "tree.html")
    circuit_path = write_circuit_html(op, tmp_path / "circuit.html")

    assert call_tree_path.exists()
    assert circuit_path.exists()
    assert "BellPair" in call_tree_path.read_text()
    assert "BellPair" in circuit_path.read_text()


def test_qda_visualization_has_expandable_nested_modules_and_split_sizes():
    _declare_qda_regs()
    data = operation_to_tree_data(_make_tridiagonal_qda())

    modules = []

    def collect(node):
        if node["kind"] == "composite":
            modules.append((node["path"], node["name"]))
        for child in node["children"]:
            collect(child)

    collect(data["root"])

    assert ("0", "QDALinearSolver") in modules
    assert any(name == "WalkS_Primitive" for _path, name in modules)
    assert any(name == "BlockEncodingTridiagonal" for _path, name in modules)
    assert {"name": "_overflow", "size": "1", "type": "General"} in data["registers"]
    assert {"name": "_other", "size": "1", "type": "General"} in data["registers"]


def test_qda_circuit_html_lists_root_and_nested_module_toggles():
    _declare_qda_regs()
    html = render_circuit_html(_make_tridiagonal_qda())

    assert '"name": "QDALinearSolver"' in html
    assert "WalkS_Primitive" in html
    assert "BlockEncodingTridiagonal" in html
    assert "${escapeHtml(node.name)} (root)" in html
