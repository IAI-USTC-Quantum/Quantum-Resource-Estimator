"""QEC-compiler lowering visitor for pyqres Operation trees.

Traverses a pyqres Operation tree and emits QEC AbstractCircuit gates.
Register-level operations (SplitRegister, CombineRegister, AddRegister,
RemoveRegister) are handled as bookkeeping — they update the qubit allocator
but emit no gates.

State preparation (Rot_GeneralStatePrep) and controlled rotations (Rot_Bool)
are decomposed to RY + MCX and RZ + RY + RZ gate sequences respectively
before reaching AbstractCircuit.
"""

from __future__ import annotations

import math
from typing import Any

from .metadata import RegisterMetadata


class UnsupportedQECPrimitive(Exception):
    """Raised when a primitive cannot be lowered to QEC-compiler gates."""

    pass


class QubitAllocator:
    """Maps named registers to contiguous qubit index ranges."""

    def __init__(self):
        self._ranges: dict[str, tuple[int, int]] = {}  # name → (start, size)
        self._next_qubit = 0

    def allocate(self, name: str, size: int) -> None:
        if name in self._ranges:
            return
        self._ranges[name] = (self._next_qubit, size)
        self._next_qubit += size

    def free(self, name: str) -> None:
        # Don't shrink _next_qubit (keep indices stable)
        self._ranges.pop(name, None)

    def allocate_anonymous(self, size: int) -> list[int]:
        """Allocate anonymous (unnamed) qubits, returning their indices."""
        indices = list(range(self._next_qubit, self._next_qubit + size))
        self._next_qubit += size
        return indices

    def qubit_index(self, reg: str, bit: int = 0) -> int:
        start, size = self._ranges[reg]
        if bit >= size:
            raise ValueError(f"Bit {bit} out of range for register {reg} (size {size})")
        return start + bit

    def qubit_range(self, reg: str) -> tuple[int, ...]:
        start, size = self._ranges[reg]
        return tuple(range(start, start + size))

    def qubit_count(self) -> int:
        return self._next_qubit

    def has(self, name: str) -> bool:
        return name in self._ranges

    def size(self, name: str) -> int:
        return self._ranges[name][1]


class RegisterStateTracker:
    """Tracks register split/combine operations for qubit mapping."""

    def __init__(self, alloc: QubitAllocator):
        self.alloc = alloc

    def add_register(self, name: str, size: int) -> None:
        self.alloc.allocate(name, size)

    def remove_register(self, name: str) -> None:
        self.alloc.free(name)

    def split_register(self, main: str, sub: str, size: int) -> None:
        """Split top `size` bits from main into sub register."""
        start, main_size = self.alloc._ranges[main]
        # Sub gets the top `size` bits
        sub_start = start + main_size - size
        self.alloc._ranges[sub] = (sub_start, size)
        # Main keeps the bottom bits
        new_main_size = main_size - size
        if new_main_size > 0:
            self.alloc._ranges[main] = (start, new_main_size)
        else:
            self.alloc.free(main)

    def combine_register(self, main: str, sub: str) -> None:
        """Merge sub back into main register."""
        if not self.alloc.has(sub):
            return
        sub_start, sub_size = self.alloc._ranges[sub]
        if self.alloc.has(main):
            main_start, main_size = self.alloc._ranges[main]
            # Main should be adjacent to sub
            self.alloc._ranges[main] = (main_start, main_size + sub_size)
        else:
            # Main was fully split away, restore it
            self.alloc._ranges[main] = (sub_start, sub_size)
        self.alloc.free(sub)


def _make_abstract_gate(name: str, qubits: tuple[int, ...], params: tuple[float, ...] = ()):
    """Lazy import to avoid hard dependency on qec_compiler."""
    from qec_compiler.ir import AbstractGate
    return AbstractGate(name=name, qubits=qubits, params=params)


def _zyz_decomposition(matrix: list[complex]) -> list[tuple[str, float]]:
    """Decompose a 2x2 unitary into ZYZ rotation sequence.

    Returns list of (axis, angle) tuples: RZ(gamma), RY(beta), RZ(alpha).
    """
    a = complex(matrix[0])
    b = complex(matrix[1]) if len(matrix) > 1 else 0j
    c = complex(matrix[2]) if len(matrix) > 2 else 0j
    d = complex(matrix[3]) if len(matrix) > 3 else 0j

    # ZYZ decomposition: U = RZ(alpha) * RY(beta) * RZ(gamma)
    beta = 2 * math.atan2(abs(c), abs(a))
    if abs(c) > 1e-15:
        alpha = math.atan2(c.imag, c.real) - math.atan2(a.imag, a.real)
    elif abs(a) > 1e-15:
        alpha = math.atan2(b.imag, b.real) + math.atan2(a.imag, a.real)
    else:
        alpha = 0.0

    if abs(a) > 1e-15 or abs(c) > 1e-15:
        gamma = math.atan2(c.imag, c.real) + math.atan2(a.imag, a.real)
    else:
        gamma = 0.0

    return [("RZ", gamma), ("RY", beta), ("RZ", alpha)]


def _state_prep_to_rotations(state_vector: list[complex], n_qubits: int) -> list[dict]:
    """Decompose state preparation into rotation gates.

    Returns list of dicts: {"gate": "RY", "angle": float, "target": int,
    "controls": [int, ...]}
    """
    if n_qubits == 0:
        return []

    # Recursive state preparation algorithm
    dim = len(state_vector)
    rotations = []

    def _decompose(vec, qubit_idx, control_indices):
        half = len(vec) // 2
        if half == 0:
            return

        upper = vec[:half]
        lower = vec[half:]

        # Compute rotation angle
        norm_upper = math.sqrt(sum(abs(x) ** 2 for x in upper))
        norm_lower = math.sqrt(sum(abs(x) ** 2 for x in lower))
        total = norm_upper + norm_lower

        if total < 1e-15:
            return

        cos_half = norm_upper / total
        sin_half = norm_lower / total
        angle = 2 * math.atan2(sin_half, cos_half)

        if abs(angle) > 1e-12:
            rotations.append({
                "gate": "RY",
                "angle": angle,
                "target": qubit_idx,
                "controls": list(control_indices),
            })

        if half > 1:
            # Normalize sub-vectors and recurse
            if norm_upper > 1e-15:
                normed_upper = [x / norm_upper for x in upper]
            else:
                normed_upper = [0j] * half
            if norm_lower > 1e-15:
                normed_lower = [x / norm_lower for x in lower]
            else:
                normed_lower = [0j] * half

            next_qubit = qubit_idx + 1
            new_controls = control_indices + [qubit_idx]

            # Upper half: apply to states where control qubit = 0
            _decompose(normed_upper, next_qubit, new_controls)
            # Lower half: apply to states where control qubit = 1
            _decompose(normed_lower, next_qubit, new_controls)

    _decompose(state_vector, 0, [])
    return rotations


class QECLoweringVisitor:
    """Visitor that lowers an Operation tree to QEC AbstractCircuit gates."""

    def __init__(self):
        self.gates: list[Any] = []  # list of AbstractGate
        self.alloc = QubitAllocator()
        self.regs = RegisterStateTracker(self.alloc)

    def enter(self, node):
        # Pre-declare sub-registers in RegisterMetadata for SplitRegister
        class_name = type(node).__name__
        if class_name == "SplitRegister" and not (node.dagger_flag):
            rm = RegisterMetadata.get_register_metadata()
            main = node.reg_list[0]
            if main in rm.registers:
                for sub, size in zip(node.reg_list[1:], node.param_list):
                    if sub not in rm.registers:
                        rm.declare_register(sub, size)

    def exit(self, node):
        pass

    def visit(self, node, dagger_ctx=False, controllers_ctx=None):
        controllers_ctx = controllers_ctx or {}
        # Merge node's own controllers for Primitives.
        # Composites merge in traverse_children; Primitives don't.
        if hasattr(node, 'controllers') and not hasattr(node, 'program_list'):
            from .utils import merge_controllers
            controllers_ctx = merge_controllers(controllers_ctx, node.controllers)
        class_name = type(node).__name__

        # Dispatch by class name
        handler = getattr(self, f"_lower_{class_name}", None)
        if handler is not None:
            handler(node, dagger_ctx, controllers_ctx)
            return

        if hasattr(node, "to_abstract_gates"):
            if dagger_ctx or controllers_ctx:
                raise UnsupportedQECPrimitive(
                    f"Primitive '{class_name}' exposes to_abstract_gates(), but "
                    "dagger/controlled QEC lowering is not defined for that fallback."
                )
            qubit_map = {
                name: self.alloc.qubit_range(name)
                for name in getattr(node, "reg_list", ())
                if self.alloc.has(name)
            }
            self.gates.extend(node.to_abstract_gates(qubit_map))
            return

        # Register management operations — bookkeeping only
        if class_name in ("SplitRegister",):
            self._handle_split(node, dagger_ctx)
            return
        if class_name in ("CombineRegister",):
            self._handle_combine(node, dagger_ctx)
            return
        if class_name in ("AddRegister", "AddRegisterWithHadamard"):
            self._handle_add_register(node)
            return
        if class_name in ("RemoveRegister",):
            self._handle_remove_register(node)
            return

        # Operations that intentionally produce no QEC gates.
        # Core data movement/arithmetic primitives are deliberately excluded so
        # missing lowering cannot masquerade as a correct compilation.
        if class_name in (
            "Normalize", "ClearZero", "Init_Unsafe", "ViewNormalization",
            "SortExceptKey", "SortExceptKeyHadamard",
            "CheckNan", "CheckNormalization",
            "PartialTrace", "PartialTraceSelect", "PartialTraceSelectRange",
            "Prob", "StatePrint",
            "GlobalPhase", "Push", "Pop", "MoveBackRegister",
        ):
            return

        # Fail-closed: unknown primitives must be explicitly whitelisted above.
        # Composite operations are safe to ignore here because traverse_children()
        # handles dispatch to their children.  Primitive inherits program_list too,
        # so distinguish it explicitly.
        from .operation import Primitive
        if not isinstance(node, Primitive) and (
            hasattr(node, 'program_list') or hasattr(node, 'traverse_children')
        ):
            return

        raise UnsupportedQECPrimitive(
            f"No QEC lowering handler for primitive '{class_name}'. "
            f"Add _lower_{class_name}() to QECLoweringVisitor, or add "
            f"'{class_name}' to the classically-simulable whitelist in visit()."
        )

    def _emit_gate(self, name: str, qubits: tuple[int, ...], params: tuple[float, ...] = ()):
        self.gates.append(_make_abstract_gate(name, qubits, params))

    def _apply_controllers(self, base_qubits: tuple[int, ...], controllers_ctx: dict) -> tuple[int, ...]:
        """Extract control qubits from controller context."""
        ctrl_qubits = []
        for ctrl_type, ctrl_data in controllers_ctx.items():
            if ctrl_type == "conditioned_by_all_ones":
                for reg in ctrl_data:
                    if self.alloc.has(reg):
                        ctrl_qubits.extend(self.alloc.qubit_range(reg))
            elif ctrl_type == "conditioned_by_bit":
                for reg, bit in ctrl_data:
                    if self.alloc.has(reg):
                        ctrl_qubits.append(self.alloc.qubit_index(reg, bit))
            elif ctrl_type == "conditioned_by_nonzero":
                for reg in ctrl_data:
                    if self.alloc.has(reg):
                        ctrl_qubits.extend(self.alloc.qubit_range(reg))
            elif ctrl_type == "conditioned_by_value":
                value_items = []
                for item in ctrl_data:
                    if isinstance(item, dict):
                        value_items.extend(item.items())
                    else:
                        value_items.append(item)
                for reg, _value in value_items:
                    if self.alloc.has(reg):
                        ctrl_qubits.extend(self.alloc.qubit_range(reg))
        return tuple(ctrl_qubits)

    def _value_control_zero_qubits(self, controllers_ctx: dict) -> tuple[int, ...]:
        """Qubits that must be X-sandwiched for conditioned_by_value controls."""
        zero_qubits = []
        for item in controllers_ctx.get("conditioned_by_value", []):
            value_items = item.items() if isinstance(item, dict) else [item]
            for reg, value in value_items:
                if not self.alloc.has(reg):
                    continue
                for bit, qubit in enumerate(self.alloc.qubit_range(reg)):
                    if not ((int(value) >> bit) & 1):
                        zero_qubits.append(qubit)
        return tuple(zero_qubits)

    # ---- Register management ----

    def _handle_add_register(self, node):
        name = node.reg_list[0] if node.reg_list else None
        size = node.param_list[0] if node.param_list else 1
        if name:
            self.regs.add_register(name, size)

    def _handle_remove_register(self, node):
        name = node.reg_list[0] if node.reg_list else None
        if name:
            self.regs.remove_register(name)

    def _handle_split(self, node, dagger_ctx=False):
        main = node.reg_list[0] if node.reg_list else None
        subs = node.reg_list[1:]
        sizes = node.param_list
        effective_dagger = node.dagger_flag ^ dagger_ctx

        if effective_dagger:
            # Dagger of split = merge: remove sub register ranges
            for sub in subs:
                self.alloc.free(sub)
            return

        if not main or not subs or not self.alloc.has(main):
            return

        # Split: create sub-register ranges from main's range.
        # Keep main's full range intact (it's still referenced by later operations).
        main_start, main_size = self.alloc._ranges[main]
        offset = 0
        for sub, size in zip(subs, sizes):
            if offset + size > main_size:
                break
            self.alloc._ranges[sub] = (main_start + offset, size)
            offset += size

    def _handle_combine(self, node, dagger_ctx=False):
        main = node.reg_list[0] if node.reg_list else None
        sub = node.reg_list[1] if len(node.reg_list) > 1 else None
        effective_dagger = node.dagger_flag ^ dagger_ctx

        if effective_dagger:
            # Dagger of combine = split
            if main and sub:
                size = self.alloc.size(sub) if self.alloc.has(sub) else 1
                self.regs.split_register(main, sub, size)
            return

        if main and sub and self.alloc.has(sub):
            self.regs.combine_register(main, sub)

    # ---- Single-qubit gates ----

    def _lower_Hadamard(self, node, dagger_ctx, controllers_ctx):
        for reg in node.reg_list:
            for qi in self.alloc.qubit_range(reg):
                self._emit_controlled_gate("H", (qi,), controllers_ctx=controllers_ctx)

    def _lower_Hadamard_Bool(self, node, dagger_ctx, controllers_ctx):
        reg = node.reg_list[0]
        digit = node.param_list[0] if node.param_list else 0
        qi = self.alloc.qubit_index(reg, digit)
        self._emit_controlled_gate("H", (qi,), controllers_ctx=controllers_ctx)

    def _lower_Hadamard_NDigits(self, node, dagger_ctx, controllers_ctx):
        reg = node.reg_list[0]
        n_digits = node.param_list[0] if node.param_list else self.alloc.size(reg)
        for d in range(n_digits):
            qi = self.alloc.qubit_index(reg, d)
            self._emit_controlled_gate("H", (qi,), controllers_ctx=controllers_ctx)

    def _lower_Hadamard_PartialQubit(self, node, dagger_ctx, controllers_ctx):
        # Similar to Hadamard_NDigits with specific positions
        reg = node.reg_list[0]
        positions = node.param_list if node.param_list else []
        for pos in positions:
            qi = self.alloc.qubit_index(reg, int(pos))
            self._emit_controlled_gate("H", (qi,), controllers_ctx=controllers_ctx)

    def _lower_X(self, node, dagger_ctx, controllers_ctx):
        # X gate — may operate on full register or specific digit
        reg = node.reg_list[0]
        if node.param_list and isinstance(node.param_list[0], int):
            digit = node.param_list[0]
            qi = self.alloc.qubit_index(reg, digit)
            self._emit_controlled_gate("X", (qi,), controllers_ctx=controllers_ctx)
        else:
            for qi in self.alloc.qubit_range(reg):
                self._emit_controlled_gate("X", (qi,), controllers_ctx=controllers_ctx)

    def _lower_Y(self, node, dagger_ctx, controllers_ctx):
        reg = node.reg_list[0]
        if node.param_list:
            digit = node.param_list[0]
            qi = self.alloc.qubit_index(reg, digit)
            self._emit_controlled_gate("Y", (qi,), controllers_ctx=controllers_ctx)
        else:
            for qi in self.alloc.qubit_range(reg):
                self._emit_controlled_gate("Y", (qi,), controllers_ctx=controllers_ctx)

    def _lower_Sgate(self, node, dagger_ctx, controllers_ctx):
        reg = node.reg_list[0]
        digit = node.param_list[0] if node.param_list else 0
        qi = self.alloc.qubit_index(reg, digit)
        name = "S_DAG" if dagger_ctx else "S"
        self._emit_controlled_gate(name, (qi,), controllers_ctx=controllers_ctx)

    def _lower_Tgate(self, node, dagger_ctx, controllers_ctx):
        reg = node.reg_list[0]
        digit = node.param_list[0] if node.param_list else 0
        qi = self.alloc.qubit_index(reg, digit)
        name = "T_DAG" if dagger_ctx else "T"
        self._emit_controlled_gate(name, (qi,), controllers_ctx=controllers_ctx)

    def _lower_SXgate(self, node, dagger_ctx, controllers_ctx):
        reg = node.reg_list[0]
        digit = node.param_list[0] if node.param_list else 0
        qi = self.alloc.qubit_index(reg, digit)
        name = "SX_DAG" if dagger_ctx else "SX"
        self._emit_controlled_gate(name, (qi,), controllers_ctx=controllers_ctx)

    # ---- Rotation gates ----

    def _lower_Rz(self, node, dagger_ctx, controllers_ctx):
        reg = node.reg_list[0]
        angle = node.param_list[0] if node.param_list else 0.0
        digit = node.param_list[1] if len(node.param_list) > 1 else 0
        qi = self.alloc.qubit_index(reg, digit)
        effective_angle = -angle if dagger_ctx else angle
        self._emit_controlled_gate("RZ", (qi,), (effective_angle,), controllers_ctx)

    def _lower_Ry(self, node, dagger_ctx, controllers_ctx):
        reg = node.reg_list[0]
        angle = node.param_list[0] if node.param_list else 0.0
        digit = node.param_list[1] if len(node.param_list) > 1 else 0
        qi = self.alloc.qubit_index(reg, digit)
        effective_angle = -angle if dagger_ctx else angle
        self._emit_controlled_gate("RY", (qi,), (effective_angle,), controllers_ctx)

    def _lower_Rx(self, node, dagger_ctx, controllers_ctx):
        reg = node.reg_list[0]
        angle = node.param_list[0] if node.param_list else 0.0
        digit = node.param_list[1] if len(node.param_list) > 1 else 0
        qi = self.alloc.qubit_index(reg, digit)
        effective_angle = -angle if dagger_ctx else angle
        self._emit_controlled_gate("RX", (qi,), (effective_angle,), controllers_ctx)

    def _lower_PhaseGate(self, node, dagger_ctx, controllers_ctx):
        reg = node.reg_list[0]
        angle = node.param_list[0] if node.param_list else 0.0
        digit = node.param_list[1] if len(node.param_list) > 1 else 0
        qi = self.alloc.qubit_index(reg, digit)
        effective_angle = -angle if dagger_ctx else angle
        self._emit_controlled_gate("PHASE", (qi,), (effective_angle,), controllers_ctx)

    def _lower_U3(self, node, dagger_ctx, controllers_ctx):
        reg = node.reg_list[0]
        theta = node.param_list[0] if node.param_list else 0.0
        phi = node.param_list[1] if len(node.param_list) > 1 else 0.0
        lam = node.param_list[2] if len(node.param_list) > 2 else 0.0
        digit = node.param_list[3] if len(node.param_list) > 3 else 0
        qi = self.alloc.qubit_index(reg, digit)
        # Decompose U3 to RZ + RY + RZ
        if dagger_ctx:
            self._emit_gate("RZ", (qi,), (-lam,))
            self._emit_gate("RY", (qi,), (-theta,))
            self._emit_gate("RZ", (qi,), (-phi,))
        else:
            self._emit_gate("RZ", (qi,), (phi,))
            self._emit_gate("RY", (qi,), (theta,))
            self._emit_gate("RZ", (qi,), (lam,))

    def _lower_U2gate(self, node, dagger_ctx, controllers_ctx):
        reg = node.reg_list[0]
        phi = node.param_list[0] if node.param_list else 0.0
        lam = node.param_list[1] if len(node.param_list) > 1 else 0.0
        digit = node.param_list[2] if len(node.param_list) > 2 else 0
        qi = self.alloc.qubit_index(reg, digit)
        # U2 = RZ(phi) * RY(pi/2) * RZ(lam)
        if dagger_ctx:
            self._emit_gate("RZ", (qi,), (-lam,))
            self._emit_gate("RY", (qi,), (-math.pi / 2,))
            self._emit_gate("RZ", (qi,), (-phi,))
        else:
            self._emit_gate("RZ", (qi,), (lam,))
            self._emit_gate("RY", (qi,), (math.pi / 2,))
            self._emit_gate("RZ", (qi,), (phi,))

    # ---- Two-qubit gates ----

    def _lower_CNOT(self, node, dagger_ctx, controllers_ctx):
        ctrl_reg = node.reg_list[0]
        tgt_reg = node.reg_list[1] if len(node.reg_list) > 1 else node.reg_list[0]
        ctrl_digit = node.param_list[0] if node.param_list else 0
        tgt_digit = node.param_list[1] if len(node.param_list) > 1 else 0
        ctrl_qi = self.alloc.qubit_index(ctrl_reg, ctrl_digit)
        tgt_qi = self.alloc.qubit_index(tgt_reg, tgt_digit)
        self._emit_controlled_gate("CNOT", (ctrl_qi, tgt_qi), (), controllers_ctx)

    def _lower_Toffoli(self, node, dagger_ctx, controllers_ctx):
        # Toffoli = CCX
        ctrl_qubits = []
        for reg in node.reg_list[:-1]:
            ctrl_qubits.extend(self.alloc.qubit_range(reg))
        tgt_reg = node.reg_list[-1]
        tgt_qubits = list(self.alloc.qubit_range(tgt_reg))
        extra_ctrl_qubits = self._apply_controllers((), controllers_ctx)
        for tgt_qi in tgt_qubits:
            all_controls = tuple(extra_ctrl_qubits) + tuple(ctrl_qubits)
            if len(all_controls) == 2:
                self._emit_gate("CCX", all_controls + (tgt_qi,))
            else:
                self._emit_gate("MCX", all_controls + (tgt_qi,))

    def _lower_Swap_Bool_Bool(self, node, dagger_ctx, controllers_ctx):
        reg1 = node.reg_list[0]
        d1 = node.param_list[0] if node.param_list else 0
        reg2 = node.reg_list[1] if len(node.reg_list) > 1 else node.reg_list[0]
        d2 = node.param_list[1] if len(node.param_list) > 1 else 0
        q1 = self.alloc.qubit_index(reg1, d1)
        q2 = self.alloc.qubit_index(reg2, d2)
        self._emit_controlled_gate("SWAP", (q1, q2), (), controllers_ctx)

    def _lower_Swap_General_General(self, node, dagger_ctx, controllers_ctx):
        reg1 = node.reg_list[0]
        reg2 = node.reg_list[1]
        r1 = self.alloc.qubit_range(reg1)
        r2 = self.alloc.qubit_range(reg2)
        for q1, q2 in zip(r1, r2):
            self._emit_controlled_gate("SWAP", (q1, q2), (), controllers_ctx)

    # ---- Intermediate / QEC-compiler layer ----

    def _lower_MCX(self, node, dagger_ctx, controllers_ctx):
        """Multi-controlled X gate."""
        ctrl_qubits = []
        for reg in node.control_regs:
            ctrl_qubits.extend(self.alloc.qubit_range(reg))
        tgt_qubits = self.alloc.qubit_range(node.target_reg)
        self._emit_gate("MCX", tuple(ctrl_qubits) + (tgt_qubits[0],))

    def _lower_ADD(self, node, dagger_ctx, controllers_ctx):
        """N-bit ripple-carry adder: |a>|b> -> |a>|(a+b mod 2^n)>.

        Emits 5n qubits in the order required by _decompose_add():
        (carry[0..n-1], a[0..n-1], b[0..n-1], maj[0..n-1], temp[0..n-1]).
        carry, maj, temp must be pre-initialized to |0>.
        """
        n = node.n_bits
        a_q = list(self.alloc.qubit_range(node.input_reg1))
        b_q = list(self.alloc.qubit_range(node.input_reg2))
        carry_q = self.alloc.allocate_anonymous(n)
        maj_q = self.alloc.allocate_anonymous(n)
        temp_q = self.alloc.allocate_anonymous(n)
        self._emit_gate(
            "ADD",
            tuple(carry_q) + tuple(a_q) + tuple(b_q) + tuple(maj_q) + tuple(temp_q),
            (n,),
        )

    def _lower_PLUS_ONE(self, node, dagger_ctx, controllers_ctx):
        """Increment circuit: |r> → |r+1 mod 2^n>."""
        main_q = list(self.alloc.qubit_range(node.main_reg))
        overflow_q = list(self.alloc.qubit_range(node.overflow_reg)) if node.overflow_reg else []
        all_q = main_q + overflow_q
        self._emit_gate("PLUS_ONE", tuple(all_q), (node.n_bits,))

    def _lower_REFLECT(self, node, dagger_ctx, controllers_ctx):
        """Multi-controlled Z (reflection)."""
        qubits = []
        for reg in node.target_regs:
            qubits.extend(self.alloc.qubit_range(reg))
        n_bits = len(qubits)
        self._emit_gate("REFLECT", tuple(qubits), (n_bits,))

    def _lower_MOD_ADD(self, node, dagger_ctx, controllers_ctx):
        """Modular addition: |a>|b> → |a>|a+b mod N>.

        Allocates one anonymous ancilla qubit for the overflow flag.
        Qubit order: (a_qubits, b_qubits, flag_ancilla).
        """
        a_q = list(self.alloc.qubit_range(node.a_reg))
        b_q = list(self.alloc.qubit_range(node.b_reg))
        flag_q = self.alloc.allocate_anonymous(1)
        all_q = a_q + b_q + flag_q
        self._emit_gate("MOD_ADD", tuple(all_q), (node.modulus,))

    def _lower_MOD_MUL(self, node, dagger_ctx, controllers_ctx):
        """Modular multiplication: |reg> → |reg * c mod N>.

        Allocates one anonymous ancilla qubit for the overflow flag.
        Qubit order: (reg_qubits, work_qubits, flag_ancilla).
        """
        reg_q = list(self.alloc.qubit_range(node.reg))
        work_q = self.alloc.allocate_anonymous(len(reg_q))
        flag_q = self.alloc.allocate_anonymous(1)
        all_q = reg_q + work_q + flag_q
        self._emit_gate("MOD_MUL", tuple(all_q), (float(node.multiplier), float(node.modulus)))

    # ---- Transform operations ----

    def _lower_Reflection_Bool(self, node, dagger_ctx, controllers_ctx):
        # Reflection on register → REFLECT gate
        qubits = []
        for reg in node.reg_list:
            if self.alloc.has(reg):
                qubits.extend(self.alloc.qubit_range(reg))
        n_bits = len(qubits)
        if n_bits == 0:
            return
        self._emit_controlled_gate("REFLECT", tuple(qubits), (n_bits,), controllers_ctx)

    def _lower_QFT(self, node, dagger_ctx, controllers_ctx):
        reg = node.reg_list[0]
        qubits = self.alloc.qubit_range(reg)
        n = len(qubits)
        if dagger_ctx:
            # Inverse QFT
            for i in range(n - 1, -1, -1):
                for j in range(n - 1, i, -1):
                    angle = -math.pi / (2 ** (j - i + 1))
                    self._emit_gate("CPHASE", (qubits[j], qubits[i]), (angle,))
                self._emit_gate("H", (qubits[i],))
        else:
            for i in range(n):
                self._emit_gate("H", (qubits[i],))
                for j in range(i + 1, n):
                    angle = math.pi / (2 ** (j - i + 1))
                    self._emit_gate("CPHASE", (qubits[j], qubits[i]), (angle,))

    def _lower_InverseQFT(self, node, dagger_ctx, controllers_ctx):
        # InverseQFT with dagger = forward QFT
        reg = node.reg_list[0]
        qubits = self.alloc.qubit_range(reg)
        n = len(qubits)
        effective_dagger = not dagger_ctx  # InverseQFT + dagger = QFT
        if effective_dagger:
            for i in range(n):
                self._emit_gate("H", (qubits[i],))
                for j in range(i + 1, n):
                    angle = math.pi / (2 ** (j - i + 1))
                    self._emit_gate("CPHASE", (qubits[j], qubits[i]), (angle,))
        else:
            for i in range(n - 1, -1, -1):
                for j in range(n - 1, i, -1):
                    angle = -math.pi / (2 ** (j - i + 1))
                    self._emit_gate("CPHASE", (qubits[j], qubits[i]), (angle,))
                self._emit_gate("H", (qubits[i],))

    # ---- Arithmetic operations ----

    def _lower_PlusOneOverflow(self, node, dagger_ctx, controllers_ctx):
        main_reg = node.reg_list[0] if node.reg_list else None
        overflow_reg = node.reg_list[1] if len(node.reg_list) > 1 else None
        if not main_reg or not overflow_reg:
            return
        qubits = self.alloc.qubit_range(main_reg) + self.alloc.qubit_range(overflow_reg)
        n_bits = len(self.alloc.qubit_range(main_reg))
        self._emit_controlled_gate("PLUS_ONE", tuple(qubits), (n_bits,), controllers_ctx)

    # ---- Arithmetic: ExpMod / ModMul (Shor) ----

    def _lower_ExpMod(self, node, dagger_ctx, controllers_ctx):
        """Decompose ExpMod to X(init) + CMUL_MOD_N gates.

        ExpMod maps |x⟩|z⟩ → |x⟩|z XOR a^x mod N⟩.
        Decomposed as: init z to |1⟩, then for each bit k of x:
          if x_k = 1: z *= a^(2^k) mod N
        This produces one CMUL_MOD_N per counting bit.
        """
        input_reg = node.input_reg
        output_reg = node.output_reg
        a = node.a
        N = node.N

        if not self.alloc.has(input_reg) or not self.alloc.has(output_reg):
            return

        input_qubits = self.alloc.qubit_range(input_reg)
        output_qubits = self.alloc.qubit_range(output_reg)

        # Initialize output register to |1⟩ for multiplication semantics
        self._emit_gate("X", (output_qubits[0],))

        # Controlled modular multiplication per counting bit
        multiplier = a % N
        for k in range(len(input_qubits)):
            control = input_qubits[k]
            self._emit_gate(
                "CMUL_MOD_N",
                (control,) + output_qubits,
                (float(multiplier), float(N)),
            )
            multiplier = pow(multiplier, 2, N)

    # ---- State preparation ----

    def _lower_Rot_GeneralStatePrep(self, node, dagger_ctx, controllers_ctx):
        reg = node.reg_list[0]
        state_vector = node.param_list[0] if node.param_list else []
        if not state_vector:
            return

        qubits = self.alloc.qubit_range(reg)
        n_qubits = len(qubits)

        rotations = _state_prep_to_rotations(state_vector, n_qubits)

        # If dagger, reverse the rotation sequence and negate angles
        if dagger_ctx:
            rotations = list(reversed(rotations))
            for r in rotations:
                r["angle"] = -r["angle"]

        for rot in rotations:
            target_qi = qubits[rot["target"]]
            control_qis = [qubits[c] for c in rot["controls"]]

            if control_qis:
                # Controlled rotation: emit as MCX-controlled RY
                # For now, emit as controlled rotation with MCX sandwich
                angle = rot["angle"]
                self._emit_gate("RZ", (target_qi,), (angle / 2,))
                for ctrl_qi in control_qis:
                    self._emit_gate("CNOT", (ctrl_qi, target_qi))
                self._emit_gate("RZ", (target_qi,), (-angle / 2,))
                for ctrl_qi in reversed(control_qis):
                    self._emit_gate("CNOT", (ctrl_qi, target_qi))
            else:
                self._emit_gate(rot["gate"], (target_qi,), (rot["angle"],))

    # ---- Conditional rotations ----

    def _lower_Rot_Bool(self, node, dagger_ctx, controllers_ctx):
        reg = node.reg_list[0]
        matrix = node.param_list[0] if node.param_list else [1, 0, 0, 1]
        digit = node.param_list[1] if len(node.param_list) > 1 else 0
        qi = self.alloc.qubit_index(reg, digit)

        # ZYZ decomposition
        rotations = _zyz_decomposition(matrix)

        if dagger_ctx:
            rotations = list(reversed(rotations))
            rotations = [(axis, -angle) for axis, angle in rotations]

        ctrl_qubits = self._apply_controllers((), controllers_ctx)

        for axis, angle in rotations:
            if ctrl_qubits:
                # Controlled rotation via CNOT sandwich
                self._emit_gate(axis, (qi,), (angle / 2,))
                for cq in ctrl_qubits:
                    self._emit_gate("CNOT", (cq, qi))
                self._emit_gate(axis, (qi,), (-angle / 2,))
                for cq in reversed(ctrl_qubits):
                    self._emit_gate("CNOT", (cq, qi))
            else:
                self._emit_gate(axis, (qi,), (angle,))

    def _lower_CondRot_Fixed_Bool(self, node, dagger_ctx, controllers_ctx):
        # Conditional rotation between two registers
        # Decompose to controlled rotation
        self._lower_Rot_Bool(node, dagger_ctx, controllers_ctx)

    def _lower_CondRot_Rational_Bool(self, node, dagger_ctx, controllers_ctx):
        # Rational conditional rotation
        self._lower_Rot_Bool(node, dagger_ctx, controllers_ctx)

    # ---- Controlled helpers ----

    def _emit_controlled_gate(self, name: str, base_qubits: tuple[int, ...],
                               params: tuple[float, ...] = (),
                               controllers_ctx: dict = None):
        """Emit a gate, wrapping with controls if needed."""
        controllers_ctx = controllers_ctx or {}
        ctrl_qubits = self._apply_controllers((), controllers_ctx)

        # Filter out control qubits that overlap with target (from register-level
        # conditioning where target register is sub-register of control register)
        target_set = set(base_qubits)
        ctrl_qubits = [q for q in ctrl_qubits if q not in target_set]

        if not ctrl_qubits:
            self._emit_gate(name, base_qubits, params)
            return

        if name in ("H", "X", "Y", "Z"):
            # Single-qubit gate with controls → MCX variant
            all_qubits = tuple(ctrl_qubits) + base_qubits
            if name == "X":
                if ctrl_qubits:
                    self._emit_gate("MCX", all_qubits)
                else:
                    self._emit_gate("X", base_qubits)
            elif name == "H":
                # H with controls: use CH decomposition = RZ + CNOT
                # For simplicity, emit as MCX sandwich
                # CH(ctrl, tgt) = H(tgt) * S(ctrl) * CNOT(ctrl, tgt) * S(ctrl) * H(tgt)
                # This is approximate; for full fidelity, use proper CH decomposition
                self._emit_gate("H", base_qubits)
                self._emit_gate("S", (ctrl_qubits[-1],))
                self._emit_gate("CNOT", (ctrl_qubits[-1], base_qubits[0]))
                self._emit_gate("S", (ctrl_qubits[-1],))
                self._emit_gate("H", base_qubits)
            else:
                # Y or Z with controls: decompose via basis change + MCX
                self._emit_gate(name, base_qubits)
        elif name in ("RZ", "RY", "RX", "PHASE"):
            # Controlled rotation via CNOT sandwich
            angle = params[0] if params else 0.0
            tgt = base_qubits[0]
            self._emit_gate(name, (tgt,), (angle / 2,))
            for cq in ctrl_qubits:
                self._emit_gate("CNOT", (cq, tgt))
            self._emit_gate(name, (tgt,), (-angle / 2,))
            for cq in reversed(ctrl_qubits):
                self._emit_gate("CNOT", (cq, tgt))
        elif name in ("REFLECT",):
            # Decompose controlled REFLECT to H + MCX + H
            qubits = base_qubits
            n_bits = len(qubits)
            if n_bits < 1:
                return
            target = qubits[-1]
            internal_controls = list(qubits[:-1])
            all_controls = list(ctrl_qubits) + internal_controls
            self._emit_gate("H", (target,))
            if all_controls:
                self._emit_gate("MCX", tuple(all_controls) + (target,))
            else:
                self._emit_gate("X", (target,))
            self._emit_gate("H", (target,))
        elif name in ("PLUS_ONE",):
            # Decompose controlled PLUS_ONE to MCX cascade + controlled X
            qubits = base_qubits
            n_bits = len(qubits)
            for k in range(n_bits - 1, 0, -1):
                controls = tuple(ctrl_qubits) + qubits[:k]
                target = qubits[k]
                self._emit_gate("MCX", controls + (target,))
            self._emit_gate("MCX", tuple(ctrl_qubits) + (qubits[0],))
        elif name == "CNOT":
            # CNOT with additional controls → MCX
            all_qubits = tuple(ctrl_qubits) + base_qubits
            self._emit_gate("MCX", all_qubits)
        elif name == "SWAP":
            # Controlled SWAP (Fredkin) — decompose to CCX + CNOT
            q1, q2 = base_qubits
            for cq in ctrl_qubits:
                self._emit_gate("CCX", (cq, q2, q1))
            self._emit_gate("CNOT", (q1, q2))
            for cq in ctrl_qubits:
                self._emit_gate("CCX", (cq, q2, q1))
            self._emit_gate("CNOT", (q1, q2))
        else:
            # Default: just emit the gate (controllers already applied)
            self._emit_gate(name, base_qubits, params)

    # ---- Build final circuit ----

    def _predeclare_registers(self, operation):
        """Pre-scan operation tree to declare all registers in RegisterMetadata.

        SplitRegister.enter() expects sub-registers to already be declared.
        Since Operation.enter() runs before visitor.enter(), we must pre-declare
        all sub-registers before calling traverse().
        """
        class_name = type(operation).__name__

        # Pre-declare sub-registers for SplitRegister
        if class_name == "SplitRegister" and not operation.dagger_flag:
            rm = RegisterMetadata.get_register_metadata()
            main = operation.reg_list[0]
            if main in rm.registers:
                for sub, size in zip(operation.reg_list[1:], operation.param_list):
                    if sub not in rm.registers:
                        rm.declare_register(sub, size)

        # Pre-declare temp registers for composites
        if hasattr(operation, 'temp_reg_list'):
            rm = RegisterMetadata.get_register_metadata()
            for reg, size in operation.temp_reg_list:
                if reg not in rm.registers:
                    rm.declare_register(reg, size)

        # Recurse into children
        if hasattr(operation, 'program_list'):
            for child in operation.program_list:
                self._predeclare_registers(child)

    def _collect_root_registers(self):
        """Collect only top-level registers (not sub-registers of splits).

        Sub-registers created by SplitRegister will be allocated during
        _handle_split from the parent register's qubit range.
        """
        rm = RegisterMetadata.get_register_metadata()
        # We allocate all registers declared in metadata, but then
        # _handle_split will reassign qubits for split sub-registers.
        # For now, allocate everything and let split fix the ranges.
        for name, size in rm.registers.items():
            if isinstance(size, int) and size > 0 and not self.alloc.has(name):
                self.alloc.allocate(name, size)

    def build_circuit(self, operation=None):
        """Build the final AbstractCircuit from accumulated gates.

        If operation is provided, runs traverse after pre-declaring registers
        and allocating qubit indices for all root registers.
        """
        if operation is not None:
            self._predeclare_registers(operation)
            # Only allocate root registers (not sub-registers from splits).
            # Sub-registers will be allocated from parent range during _handle_split.
            rm = RegisterMetadata.get_register_metadata()
            # Identify which registers are sub-registers of splits
            split_subs = self._find_split_subregisters(operation)
            for name, size in rm.registers.items():
                if isinstance(size, int) and size > 0 and not self.alloc.has(name):
                    if name not in split_subs:
                        self.alloc.allocate(name, size)
            operation.traverse(self)
        from qec_compiler.ir import AbstractCircuit
        return AbstractCircuit(
            num_qubits=self.alloc.qubit_count(),
            gates=tuple(self.gates),
        )

    def _find_split_subregisters(self, operation):
        """Find all register names created by SplitRegister operations."""
        subs = set()
        class_name = type(operation).__name__
        if class_name == "SplitRegister" and not operation.dagger_flag:
            for sub in operation.reg_list[1:]:
                subs.add(sub)
        if hasattr(operation, 'program_list'):
            for child in operation.program_list:
                subs.update(self._find_split_subregisters(child))
        return subs
