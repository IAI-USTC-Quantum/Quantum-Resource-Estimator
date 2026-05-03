"""Generate QDA-Tridiagonal visualization HTML files.

Run from the repository root:

    python examples/qda_tridiagonal_visualization.py

The generated files are written to ``visualizations/``.
"""

from __future__ import annotations

from pathlib import Path

from pyqres.algorithms.block_encoding import BlockEncodingTridiagonal
from pyqres.core.metadata import RegisterMetadata
from pyqres.generated import QDALinearSolver
from pyqres.primitives import Hadamard
from pyqres.visualization import write_call_tree_html, write_circuit_html


def reset_metadata() -> None:
    while len(RegisterMetadata.register_metadata_stack):
        RegisterMetadata.pop_register_metadata()
    RegisterMetadata.push_register_metadata()


def declare_registers() -> None:
    rm = RegisterMetadata.get_register_metadata()
    rm.declare_register("main_reg", 2, "UnsignedInteger")
    rm.declare_register("anc_UA", 4, "UnsignedInteger")
    rm.declare_register("anc_1", 1, "Boolean")
    rm.declare_register("anc_2", 1, "Boolean")
    rm.declare_register("anc_3", 1, "Boolean")
    rm.declare_register("anc_4", 1, "Boolean")


def make_encode_a(reg_list=None, param_list=None):
    return BlockEncodingTridiagonal(
        main_reg=reg_list[0],
        anc_UA=reg_list[1],
        alpha=0.5,
        beta=0.3,
    )


def make_qda_tridiagonal():
    return QDALinearSolver(
        reg_list=["main_reg", "anc_UA", "anc_1", "anc_2", "anc_3", "anc_4"],
        param_list=[2.0, 0.5],
        operations=[make_encode_a, Hadamard],
    )


def main() -> int:
    reset_metadata()
    declare_registers()
    op = make_qda_tridiagonal()

    output_dir = Path("visualizations")
    output_dir.mkdir(exist_ok=True)
    tree_path = write_call_tree_html(op, output_dir / "qda_tridiagonal_tree.html")
    circuit_path = write_circuit_html(op, output_dir / "qda_tridiagonal_circuit.html")
    print(tree_path)
    print(circuit_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
