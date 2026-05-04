"""Intermediate primitives for QEC-compiler integration.

These Primitive subclasses map directly to QEC-compiler AbstractGate names.
Each implements:
- to_abstract_gates(): returns AbstractGate list for QEC lowering
- pyqsparse_object(): decomposed PySparQ simulation for verification
- t_count(): resource estimation
"""

from __future__ import annotations

from typing import Any

from ..core.operation import Primitive
from ..core.utils import get_control_qubit_count, merge_controllers, reg_sz, mcx_t_count
from ..core.simulator import PyQSparseOperationWrapper


def _lazy_abstract_gate(name: str, qubits: tuple[int, ...], params: tuple[float, ...] = ()):
    from qec_compiler.ir import AbstractGate
    return AbstractGate(name=name, qubits=qubits, params=params)


class MCX(Primitive):
    """Multi-controlled X gate. Maps directly to AbstractGate('MCX')."""

    def __init__(self, reg_list=None, param_list=None):
        super().__init__(reg_list=reg_list, param_list=param_list)
        self.control_regs = reg_list[:-1] if reg_list else []
        self.target_reg = reg_list[-1] if reg_list else None

    def pyqsparse_object(self, dagger_ctx=False, controllers_ctx=None):
        import pysparq as ps
        controllers_ctx = merge_controllers(self.controllers, controllers_ctx or {})
        obj = PyQSparseOperationWrapper(ps.FlipBools(self.target_reg))
        obj.set_controller(controllers_ctx)
        return obj

    def t_count(self, dagger_ctx=False, controllers_ctx=None):
        ncontrols = get_control_qubit_count(
            merge_controllers(self.controllers, controllers_ctx or {}))
        n_controls_intrinsic = sum(reg_sz(r) for r in self.control_regs)
        return mcx_t_count(n_controls_intrinsic + ncontrols)

    def to_abstract_gates(self, qubit_map):
        ctrl_qubits = []
        for reg in self.control_regs:
            ctrl_qubits.extend(qubit_map[reg])
        tgt_qubits = qubit_map[self.target_reg]
        return [_lazy_abstract_gate("MCX", tuple(ctrl_qubits) + (tgt_qubits[0],))]


class ADD(Primitive):
    """N-bit ripple-carry adder. Maps to AbstractGate('ADD', (n_bits,))."""

    def __init__(self, reg_list=None, param_list=None):
        super().__init__(reg_list=reg_list, param_list=param_list)
        self.input_reg1 = reg_list[0] if reg_list else None
        self.input_reg2 = reg_list[1] if len(reg_list) > 1 else None
        self.n_bits = param_list[0] if param_list else reg_sz(self.input_reg1) if self.input_reg1 else 1

    def pyqsparse_object(self, dagger_ctx=False, controllers_ctx=None):
        import pysparq as ps
        controllers_ctx = merge_controllers(self.controllers, controllers_ctx or {})
        obj = PyQSparseOperationWrapper(
            ps.Add_UInt_UInt_InPlace(self.input_reg1, self.input_reg2))
        obj.set_dagger(dagger_ctx)
        obj.set_controller(controllers_ctx)
        return obj

    def t_count(self, dagger_ctx=False, controllers_ctx=None):
        ncontrols = get_control_qubit_count(
            merge_controllers(self.controllers, controllers_ctx or {}))
        n = self.n_bits
        return 2 * (n - 1) * mcx_t_count(ncontrols + 2)

    def to_abstract_gates(self, qubit_map):
        a_qubits = qubit_map[self.input_reg1]
        b_qubits = qubit_map[self.input_reg2]
        return [_lazy_abstract_gate("ADD", tuple(a_qubits) + tuple(b_qubits), (self.n_bits,))]


class PLUS_ONE(Primitive):
    """Increment circuit. Maps to AbstractGate('PLUS_ONE', (n_bits,))."""

    def __init__(self, reg_list=None, param_list=None):
        super().__init__(reg_list=reg_list, param_list=param_list)
        self.main_reg = reg_list[0] if reg_list else None
        self.overflow_reg = reg_list[1] if len(reg_list) > 1 else None
        self.n_bits = param_list[0] if param_list else reg_sz(self.main_reg) if self.main_reg else 1

    __self_conjugate__ = False

    def pyqsparse_object(self, dagger_ctx=False, controllers_ctx=None):
        import pysparq as ps
        controllers_ctx = merge_controllers(self.controllers, controllers_ctx or {})
        if self.overflow_reg:
            obj = PyQSparseOperationWrapper(
                ps.PlusOneAndOverflow(self.main_reg, self.overflow_reg))
        else:
            obj = PyQSparseOperationWrapper(
                ps.PlusOneAndOverflow(self.main_reg, "_overflow"))
        obj.set_dagger(dagger_ctx ^ self.dagger_flag)
        obj.set_controller(controllers_ctx)
        return obj

    def t_count(self, dagger_ctx=False, controllers_ctx=None):
        ncontrols = get_control_qubit_count(
            merge_controllers(self.controllers, controllers_ctx or {}))
        n = self.n_bits
        return 4 * n + ncontrols * 4

    def to_abstract_gates(self, qubit_map):
        qubits = list(qubit_map[self.main_reg])
        if self.overflow_reg and self.overflow_reg in qubit_map:
            qubits.extend(qubit_map[self.overflow_reg])
        return [_lazy_abstract_gate("PLUS_ONE", tuple(qubits), (self.n_bits,))]


class REFLECT(Primitive):
    """Multi-controlled Z (reflection). Maps to AbstractGate('REFLECT', (n_bits,))."""

    __self_conjugate__ = True

    def __init__(self, reg_list=None, param_list=None):
        super().__init__(reg_list=reg_list, param_list=param_list)
        self.target_regs = reg_list

    def pyqsparse_object(self, dagger_ctx=False, controllers_ctx=None):
        import pysparq as ps
        controllers_ctx = merge_controllers(self.controllers, controllers_ctx or {})
        inverse = param_list[0] if (param_list := self.param_list) else True
        obj = PyQSparseOperationWrapper(
            ps.Reflection_Bool(self.target_regs, inverse))
        obj.set_controller(controllers_ctx)
        return obj

    def t_count(self, dagger_ctx=False, controllers_ctx=None):
        ncontrols = get_control_qubit_count(
            merge_controllers(self.controllers, controllers_ctx or {}))
        n = sum(reg_sz(r) for r in self.target_regs)
        return mcx_t_count(n + ncontrols)

    def to_abstract_gates(self, qubit_map):
        qubits = []
        for reg in self.target_regs:
            qubits.extend(qubit_map[reg])
        n_bits = len(qubits)
        return [_lazy_abstract_gate("REFLECT", tuple(qubits), (n_bits,))]


class MOD_ADD(Primitive):
    """Modular addition a+b mod N. Maps to AbstractGate('MOD_ADD', (modulus,))."""

    def __init__(self, reg_list=None, param_list=None):
        super().__init__(reg_list=reg_list, param_list=param_list)
        self.a_reg = reg_list[0] if reg_list else None
        self.b_reg = reg_list[1] if len(reg_list) > 1 else None
        self.modulus = param_list[0] if param_list else 2

    def pyqsparse_object(self, dagger_ctx=False, controllers_ctx=None):
        raise NotImplementedError(
            "MOD_ADD has no matching PySparQ reference primitive yet. "
            "Using Add_UInt_UInt_InPlace would violate the modular-add contract."
        )

    def t_count(self, dagger_ctx=False, controllers_ctx=None):
        n = reg_sz(self.a_reg) if self.a_reg else 1
        return 4 * n * 2  # Approximate: add + compare + conditional sub

    def to_abstract_gates(self, qubit_map):
        qubits = list(qubit_map[self.a_reg]) + list(qubit_map[self.b_reg])
        return [_lazy_abstract_gate("MOD_ADD", tuple(qubits), (self.modulus,))]


class MOD_MUL(Primitive):
    """Modular multiplication a*c mod N. Maps to AbstractGate('MOD_MUL', (multiplier, modulus))."""

    def __init__(self, reg_list=None, param_list=None):
        super().__init__(reg_list=reg_list, param_list=param_list)
        self.reg = reg_list[0] if reg_list else None
        self.multiplier = param_list[0] if param_list else 1
        self.modulus = param_list[1] if len(param_list) > 1 else 2

    def pyqsparse_object(self, dagger_ctx=False, controllers_ctx=None):
        import pysparq as ps
        import math
        controllers_ctx = merge_controllers(self.controllers, controllers_ctx or {})
        multiplier = int(self.multiplier)
        modulus = int(self.modulus)
        if math.gcd(multiplier, modulus) != 1:
            raise ValueError(
                f"MOD_MUL requires multiplier coprime to modulus, got "
                f"multiplier={multiplier}, modulus={modulus}"
            )
        if dagger_ctx ^ self.dagger_flag:
            multiplier = pow(multiplier, -1, modulus)
        op_cls = getattr(ps, "Mod_Mult_UInt_ConstUInt_InPlace", None)
        if op_cls is None:
            op_cls = getattr(ps, "Mod_Mult_UInt_ConstUInt")
        # PySparQ's primitive computes reg *= a^(2^x) mod N.  Use x=0 so
        # the multiplier is exactly the intermediate-layer constant c.
        obj = PyQSparseOperationWrapper(
            op_cls(self.reg, multiplier, 0, modulus))
        obj.set_controller(controllers_ctx)
        return obj

    def t_count(self, dagger_ctx=False, controllers_ctx=None):
        n = reg_sz(self.reg) if self.reg else 1
        ncontrols = get_control_qubit_count(
            merge_controllers(self.controllers, controllers_ctx or {}))
        return 4 * n * mcx_t_count(ncontrols + 2)

    def to_abstract_gates(self, qubit_map):
        qubits = list(qubit_map[self.reg])
        return [_lazy_abstract_gate("MOD_MUL", tuple(qubits),
                                    (self.multiplier, self.modulus))]


class QECGate(Primitive):
    """Compiler-only adapter for exact QEC-Compiler example mirroring.

    ``QECGate`` is intentionally not a portable algorithm primitive. It exists
    so YAML-defined pyqres examples can emit the same gate-level
    ``AbstractCircuit`` as QEC-Compiler's curated benchmark builders while
    still flowing through the normal pyqres DSL/generated Operation path.

    ``param_list`` shape:
        ``[gate_name: str, qubits: list[int], params: list[float]]``
    """

    def __init__(self, reg_list=None, param_list=None):
        super().__init__(reg_list=reg_list, param_list=param_list or [])
        self.register = reg_list[0] if reg_list else None
        self.gate_name = str(self.param_list[0])
        self.bit_indices = tuple(int(q) for q in self.param_list[1])
        raw_params = self.param_list[2] if len(self.param_list) > 2 else []
        self.gate_params = tuple(float(p) for p in raw_params)

    def pyqsparse_object(self, dagger_ctx=False, controllers_ctx=None):
        raise NotImplementedError(
            "QECGate is a compiler-only adapter for AbstractCircuit emission; "
            "it has no PySparQ reference implementation."
        )

    def t_count(self, dagger_ctx=False, controllers_ctx=None):
        raise NotImplementedError(
            "QECGate does not define pyqres resource semantics. Use the emitted "
            "AbstractCircuit/QEC-Compiler pipeline for resource computation."
        )

    def to_abstract_gates(self, qubit_map):
        if self.register not in qubit_map:
            raise ValueError(f"Register {self.register!r} is not allocated for QECGate")
        reg_qubits = qubit_map[self.register]
        qubits = tuple(reg_qubits[index] for index in self.bit_indices)
        return [_lazy_abstract_gate(self.gate_name, qubits, self.gate_params)]
