from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from sympy import Symbol, latex


@dataclass
class QReg:
    name: str
    size: Any
    reg_type: str = "General"

    def __hash__(self):
        return hash((self.name, str(self.size), self.reg_type))

    def __str__(self):
        return f"{self.name}[{self.size}]"

    def __repr__(self):
        return str(self)


@dataclass
class Controller:
    qreg: str
    control_type: str
    control_info: Any = None


@dataclass
class OpCode:
    name: str
    targets: list[str]
    params: list[Any] = field(default_factory=list)
    controls: list[Controller] = field(default_factory=list)
    dagger: bool = False


class QuantumCircuit:
    """Register-level circuit model consumed by the Quantikz generator.

    The model is intentionally small: rows are named registers, columns are
    semantic operations.  It keeps the old public class name while avoiding the
    previous register-permutation based renderer, which was fragile once
    pyqres grew dynamic registers and nested operation trees.
    """

    def __init__(self, registers: Mapping[str, Any] | None = None):
        if registers is None:
            from pyqres.core.metadata import RegisterMetadata

            registers = RegisterMetadata.get_registers()
        self.registers: dict[str, QReg] = {}
        self.timeline: list[OpCode] = []
        for name, size in registers.items():
            self.ensure_register(str(name), size)

    def ensure_register(self, name: str, size: Any = "?", reg_type: str = "General") -> None:
        if name in self.registers:
            reg = self.registers[name]
            if size not in (None, "?"):
                reg.size = size
            if reg_type != "General":
                reg.reg_type = reg_type
            return
        self.registers[name] = QReg(name, size, reg_type)

    def add_op(self, op: OpCode) -> None:
        for reg in op.targets:
            self.ensure_register(str(reg))
        for control in op.controls:
            self.ensure_register(str(control.qreg))
        self.timeline.append(op)

    def split_registers(self, reg_list, param_list) -> None:
        if not reg_list:
            return
        parent = str(reg_list[0])
        self.ensure_register(parent)
        remaining = self.registers[parent].size
        if isinstance(remaining, int) and all(isinstance(size, int) for size in param_list):
            remaining -= sum(param_list)
        for reg, size in zip(reg_list[1:], param_list):
            self.ensure_register(str(reg), size)
        self.registers[parent].size = remaining

    def merge_registers(self, reg_list, param_list=None) -> None:
        if not reg_list:
            return
        parent = str(reg_list[0])
        self.ensure_register(parent)
        total = self.registers[parent].size
        for reg in reg_list[1:]:
            name = str(reg)
            self.ensure_register(name)
            size = self.registers[name].size
            if isinstance(total, int) and isinstance(size, int):
                total += size
            self.registers[name].size = 0
        self.registers[parent].size = total


class LatexGenerator:
    @staticmethod
    def generate(circuit: QuantumCircuit) -> str:
        gen = LatexGenerator(circuit)
        return gen._build_full_document()

    @staticmethod
    def generate_as_figure(circuit: QuantumCircuit, figure_caption: str) -> str:
        gen = LatexGenerator(circuit)
        return gen._build_as_figure(figure_caption)

    @staticmethod
    def generate_body(circuit: QuantumCircuit) -> str:
        gen = LatexGenerator(circuit)
        return gen._build_body()

    def __init__(self, circuit: QuantumCircuit):
        self.circuit = circuit
        self.register_order = list(circuit.registers.keys())

    def _build_full_document(self) -> str:
        return "\n".join(
            [
                r"\documentclass{standalone}",
                r"\usepackage{tikz}",
                r"\usetikzlibrary{quantikz2}",
                r"\begin{document}",
                self._build_body(),
                r"\end{document}",
            ]
        )

    def _build_as_figure(self, figure_caption: str) -> str:
        return "\n".join(
            [
                r"\begin{figure}",
                r"\centering",
                self._build_body(),
                r"\caption{" + self._latex_text(figure_caption) + r"}",
                r"\end{figure}",
            ]
        )

    def _build_body(self) -> str:
        lines = self._initial_lines()
        for layer in self._process_into_layers(self.circuit.timeline):
            self._append_layer(lines, layer)
        for row in self.register_order:
            lines[row].append(r"\qw")

        body = [" & ".join(lines[row]) + r" \\" for row in self.register_order]
        return "\n".join(
            [
                r"\begin{quantikz}",
                *body,
                r"\end{quantikz}",
            ]
        )

    def _initial_lines(self) -> dict[str, list[str]]:
        lines = {}
        for reg in self.circuit.registers.values():
            label = self._latex_register_name(reg.name)
            lines[reg.name] = [rf"\lstick{{$ {label} $}}", rf"\qwbundle{{{self._format_size(reg.size)}}}"]
        return lines

    def _append_layer(self, lines: dict[str, list[str]], ops: list[OpCode]) -> None:
        row_index = {reg: idx for idx, reg in enumerate(self.register_order)}
        cells = {reg: r"\qw" for reg in self.register_order}

        for op in ops:
            targets = [str(reg) for reg in op.targets if str(reg) in row_index]
            controls = [
                control
                for control in op.controls
                if str(control.qreg) in row_index and str(control.qreg) not in targets
            ]
            involved = [str(control.qreg) for control in controls] + targets
            if not involved:
                continue

            anchor = targets[0] if targets else involved[0]
            anchor_idx = row_index[anchor]
            gate = self._format_gate(op)

            for control in controls:
                control_reg = str(control.qreg)
                delta = anchor_idx - row_index[control_reg]
                cells[control_reg] = self._format_control(control, delta)

            if targets:
                for target in targets:
                    cells[target] = rf"\gate{{{gate}}}"
            else:
                cells[anchor] = rf"\gate{{{gate}}}"

        for reg in self.register_order:
            lines[reg].append(cells[reg])

    @staticmethod
    def _process_into_layers(ops: list[OpCode]) -> list[list[OpCode]]:
        layers: list[tuple[list[OpCode], set[str]]] = []
        for op in ops:
            op_regs = set(op.targets)
            op_regs.update(control.qreg for control in op.controls)
            for layer, used_regs in layers:
                if not op_regs.intersection(used_regs):
                    layer.append(op)
                    used_regs.update(op_regs)
                    break
            else:
                layers.append(([op], set(op_regs)))
        return [layer for layer, _used_regs in layers]

    @staticmethod
    def _format_gate(op: OpCode) -> str:
        params = LatexGenerator._format_params(op.params)
        dagger = r"^{\dagger}" if op.dagger else ""
        return rf"\mathrm{{{LatexGenerator._latex_text(op.name)}}}{dagger}{params}"

    @staticmethod
    def _format_control(control: Controller, delta: int) -> str:
        if control.control_type == "conditioned_by_all_ones":
            return rf"\ctrl{{{delta}}}"
        label = LatexGenerator._control_label(control)
        return rf"\ctrl[open]{{{delta}}}{label}"

    @staticmethod
    def _control_label(control: Controller) -> str:
        if control.control_type == "conditioned_by_nonzero":
            return r"\midstick[1,brackets=none]{$\neq 0$}"
        if control.control_type == "conditioned_by_value":
            return rf"\midstick[1,brackets=none]{{$={LatexGenerator._latex_value(control.control_info)}$}}"
        if control.control_type == "conditioned_by_bit":
            return rf"\midstick[1,brackets=none]{{$[{LatexGenerator._latex_value(control.control_info)}]$}}"
        raise ValueError(f"Unknown control type: {control.control_type}")

    @staticmethod
    def _format_params(params) -> str:
        if not params:
            return ""
        return "(" + ", ".join(LatexGenerator._latex_value(param) for param in params) + ")"

    @staticmethod
    def _latex_value(value: Any) -> str:
        if isinstance(value, Symbol):
            return latex(value)
        if isinstance(value, float):
            return f"{value:.6g}"
        if isinstance(value, (list, tuple)):
            return "(" + ", ".join(LatexGenerator._latex_value(item) for item in value) + ")"
        return LatexGenerator._latex_text(str(value))

    @staticmethod
    def _format_size(size: Any) -> str:
        if isinstance(size, Symbol):
            return latex(size)
        return LatexGenerator._latex_text(str(size))

    @staticmethod
    def _latex_register_name(name: str) -> str:
        return LatexGenerator._latex_text(str(name))

    @staticmethod
    def _latex_text(text: str) -> str:
        replacements = {
            "\\": r"\textbackslash{}",
            "_": r"\_",
            "&": r"\&",
            "%": r"\%",
            "$": r"\$",
            "#": r"\#",
            "{": r"\{",
            "}": r"\}",
            "~": r"\textasciitilde{}",
            "^": r"\textasciicircum{}",
        }
        return "".join(replacements.get(char, char) for char in text)


class Compiler:
    @staticmethod
    def compile(
        latex_code: str,
        filename,
        tex_path="tex_outputs",
        pdf_path="pdf_outputs",
        engine="pdflatex",
    ) -> Path:
        """Compile Quantikz LaTeX to PDF and return the generated PDF path."""

        os.makedirs(tex_path, exist_ok=True)
        os.makedirs(pdf_path, exist_ok=True)

        tex_dir = Path(tex_path)
        pdf_dir = Path(pdf_path)
        tex_file = Path(filename)
        if tex_file.suffix != ".tex":
            tex_file = tex_file.with_suffix(".tex")
        tex_file = tex_dir / tex_file.name
        tex_file.write_text(latex_code, encoding="utf-8")

        result = subprocess.run(
            [
                engine,
                f"-output-directory={str(pdf_dir).replace(os.sep, '/')}",
                str(tex_file).replace(os.sep, "/"),
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                "LaTeX compilation failed:\n"
                + result.stdout
                + ("\n" + result.stderr if result.stderr else "")
            )

        pdf_file = pdf_dir / tex_file.with_suffix(".pdf").name
        for suffix in (".aux", ".log"):
            aux_file = pdf_dir / tex_file.with_suffix(suffix).name
            if aux_file.exists():
                aux_file.unlink()
        return pdf_file
