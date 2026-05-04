"""Compiler-only QEC gate primitive.

QECGate wraps QEC-compiler AbstractGate objects for direct emission during
QEC lowering. It does NOT support PySparQ simulation or resource estimation.

Use cases:
  - YAML DSL composites that need exact gate-level parity with QEC-compiler
    benchmark builders.
  - Pass-through of arbitrary AbstractGate sequences without going through
    the register-level pyqres primitive lowering.

QECGate is a Primitive so it can appear in Composite program_lists and be
dispatched by the OperationRegistry. The QECLoweringVisitor handles it via
the to_abstract_gates() hook.
"""

from __future__ import annotations

from ..core.operation import Primitive


class QECGate(Primitive):
    """A compiler-only primitive that emits pre-built AbstractGate objects.

    Parameters
    ----------
    reg_list : list[str]
        Register names (used for qubit index resolution during lowering).
    param_list : list
        ``param_list[0]`` must be a list of gate-definition dicts, each with:

        - ``"name"``: gate name string (e.g. ``"H"``, ``"CNOT"``)
        - ``"qubits"``: tuple of absolute qubit indices
        - ``"params"``: optional tuple of float parameters
    """

    def __init__(self, reg_list, param_list):
        super().__init__(reg_list=reg_list, param_list=param_list)
        self._gate_defs = param_list[0] if param_list else []

    def pyqsparse_object(self, dagger_ctx=False, controllers_ctx=None):
        raise NotImplementedError(
            "QECGate is a compiler-only primitive. "
            "It does not support PySparQ simulation."
        )

    def t_count(self, dagger_ctx=False, controllers_ctx=None):
        raise NotImplementedError(
            "QECGate is a compiler-only primitive. "
            "Resource estimation is not available."
        )

    def to_abstract_gates(self, qubit_map):
        """Return pre-built AbstractGate objects for QEC lowering.

        The qubit_map is accepted for API compatibility but not used,
        because QECGate carries absolute qubit indices in its gate defs.
        """
        from qec_compiler.ir import AbstractGate

        gates = []
        for gdef in self._gate_defs:
            gates.append(AbstractGate(
                name=gdef["name"],
                qubits=tuple(gdef["qubits"]),
                params=tuple(gdef.get("params", ())),
            ))
        return gates
