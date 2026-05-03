from __future__ import annotations

from ..core.metadata import RegisterMetadata
from ..core.operation import Primitive
from ..core.utils import merge_controllers
from .generator import Controller, LatexGenerator, OpCode, QuantumCircuit


class QuantikzVisitor:
    """Visitor that converts a pyqres Operation tree to Quantikz LaTeX.

    Traversal still comes from ``Operation.traverse`` so dagger propagation,
    reversed dagger traversal, controller contexts, and temporary register
    scopes stay aligned with the rest of pyqres.
    """

    _CONTROL_TYPES = (
        "conditioned_by_all_ones",
        "conditioned_by_nonzero",
        "conditioned_by_bit",
        "conditioned_by_value",
    )

    def __init__(self, registers=None):
        self.circuit = QuantumCircuit(registers or RegisterMetadata.get_registers())

    def enter(self, node):
        self._sync_register_metadata()

    def exit(self, node):
        pass

    def visit(self, node, dagger_ctx=False, controllers_ctx=None):
        if not isinstance(node, Primitive):
            return

        controllers_ctx = controllers_ctx or {}
        self._sync_register_metadata()
        if self._handle_register_primitive(node, dagger_ctx, controllers_ctx):
            return

        self.circuit.add_op(self._primitive_to_opcode(node, dagger_ctx, controllers_ctx))

    def _sync_register_metadata(self) -> None:
        metadata = RegisterMetadata.get_register_metadata()
        reg_types = metadata.register_types
        for name, size in metadata.registers.items():
            self.circuit.ensure_register(str(name), size, reg_types.get(name, "General"))

    def _primitive_to_opcode(self, node, dagger_ctx=False, controllers_ctx=None) -> OpCode:
        merged = merge_controllers(controllers_ctx or {}, node.controllers)
        dagger = bool(dagger_ctx ^ node.dagger_flag)
        return OpCode(
            name=node.name,
            targets=[str(reg) for reg in node.reg_list],
            params=list(node.param_list),
            controls=self._build_controls(merged),
            dagger=dagger,
        )

    def _handle_register_primitive(self, node, dagger_ctx=False, controllers_ctx=None) -> bool:
        name = node.__class__.__name__
        effective_dagger = bool(dagger_ctx ^ getattr(node, "dagger_flag", False))
        merged = merge_controllers(controllers_ctx or {}, node.controllers)
        controls = self._build_controls(merged)

        if name == "SplitRegister":
            op_name = "CombineRegister" if effective_dagger else "SplitRegister"
            self.circuit.add_op(
                OpCode(
                    name=op_name,
                    targets=[str(reg) for reg in node.reg_list],
                    params=list(node.param_list),
                    controls=controls,
                )
            )
            return True

        if name == "CombineRegister":
            op_name = "SplitRegister" if effective_dagger else "CombineRegister"
            self.circuit.add_op(
                OpCode(
                    name=op_name,
                    targets=[str(reg) for reg in node.reg_list],
                    params=list(node.param_list),
                    controls=controls,
                )
            )
            return True

        if name in ("AddRegister", "AddRegisterWithHadamard"):
            reg_name = str(node.param_list[0])
            reg_type = str(node.param_list[1])
            size = node.param_list[2]
            self.circuit.ensure_register(reg_name, size, reg_type)
            self.circuit.add_op(
                OpCode(
                    name=name,
                    targets=[reg_name],
                    params=[reg_type, size],
                    controls=controls,
                )
            )
            return True

        if name == "RemoveRegister":
            reg_name = str(node.param_list[0])
            self.circuit.ensure_register(reg_name)
            self.circuit.add_op(OpCode(name=name, targets=[reg_name], controls=controls))
            return True

        return False

    def _build_controls(self, controllers_ctx):
        controls = []
        for ctype in self._CONTROL_TYPES:
            for entry in controllers_ctx.get(ctype, []):
                if isinstance(entry, tuple):
                    reg, info = entry[0], entry[1]
                    controls.append(Controller(str(reg), ctype, info))
                else:
                    controls.append(Controller(str(entry), ctype))
        return controls

    def to_latex(self):
        return LatexGenerator.generate(self.circuit)

    def to_latex_figure(self, caption=""):
        return LatexGenerator.generate_as_figure(self.circuit, caption)
