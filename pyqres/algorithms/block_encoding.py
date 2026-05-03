"""
Block encoding algorithms for pyqres.

Implements block encoding of matrices as quantum unitary operators:
- **Tridiagonal**: compact encoding for alpha*I + beta*T matrices
- **QRAM-based**: arbitrary sparse matrices via U_L / U_R decomposition

Reference:
    - SparQ Paper: https://arxiv.org/abs/2503.15118
    - pysparq/algorithms/block_encoding.py
"""

from __future__ import annotations

import math
from typing import Optional

import numpy as np

import pysparq as ps

from ..core.operation import AbstractComposite, Primitive, StandardComposite
from ..core.registry import OperationRegistry
from ..core.metadata import RegisterMetadata
from ..core.utils import merge_controllers, get_control_qubit_count, reg_sz
from ..core.simulator import PyQSparseOperationWrapper
from ..primitives.arithmetic import (
    Add_Mult_UInt_ConstUInt, Add_UInt_UInt_InPlace,
    ShiftLeft, ShiftRight, GetRotateAngle_Int_Int,
    Div_Sqrt_Arccos_Int_Int,
)
from ..primitives.gates import X as XGate
from ..primitives.qram import QRAMFast
from ..primitives.cond_rot import CondRot_General_Bool
from ..primitives.register_ops import SplitRegister, CombineRegister
from ..primitives.state_prep import Rot_GeneralStatePrep, Normalize, ClearZero
from ..algorithms.state_prep import make_func, make_func_inv
from ..primitives.transform import Reflection_Bool


# ==============================================================================
# Utility matrix functions (pure numpy)
# ==============================================================================

def get_tridiagonal_matrix(alpha: float, beta: float, dim: int) -> np.ndarray:
    """Return the dim×dim tridiagonal matrix alpha*I + beta*T.

    The off-diagonal matrix T has ones on the first sub- and super-diagonal.
    """
    mat = np.full((dim, dim), 0.0)
    for i in range(dim):
        mat[i, i] = alpha
        if i > 0:
            mat[i - 1, i] = beta
        if i < dim - 1:
            mat[i + 1, i] = beta
    return mat


def get_u_plus(size: int) -> np.ndarray:
    """Return the size×size shift-down (sub-diagonal) matrix."""
    mat = np.zeros((size, size))
    for i in range(1, size):
        mat[i, i - 1] = 1
    return mat


def get_u_minus(size: int) -> np.ndarray:
    """Return the size×size shift-up (super-diagonal) matrix."""
    mat = np.zeros((size, size))
    for i in range(size - 1):
        mat[i, i + 1] = 1
    return mat


# ==============================================================================
# BlockEncodingTridiagonal
# ==============================================================================

class BlockEncodingTridiagonal(StandardComposite):
    """Block encoding of a tridiagonal matrix alpha*I + beta*T.

    Uses a 4-element ancilla state for state preparation, then applies
    conditional increment/decrement on the main register.
    Self-adjoint when beta >= 0.

    Attributes:
        main_reg: Main index register
        anc_UA: Ancilla register for unitary encoding (4-element)
        alpha: Diagonal coefficient
        beta: Off-diagonal coefficient
    """

    def __init__(
        self,
        reg_list=None,
        param_list=None,
        submodules=None,
        main_reg: str = "main",
        anc_UA: str = "anc_UA",
        alpha: float = 0.0,
        beta: float = 0.0,
    ):
        if reg_list is None:
            reg_list = [main_reg, anc_UA]
        super().__init__(reg_list=reg_list, param_list=param_list, submodules=submodules or [])

        self.main_reg = main_reg
        self.anc_UA = anc_UA
        self.alpha = alpha
        self.beta = beta

        # Compute 4-element state preparation vector
        n = 2 ** reg_sz(main_reg)
        sum_val = n * abs(alpha) ** 2 + 2 * (n - 1) * abs(beta) ** 2
        norm_f = math.sqrt(sum_val) if sum_val > 0 else 1.0

        abs_alpha = abs(alpha)
        abs_beta = abs(beta)

        p0 = math.sqrt(abs_alpha) / math.sqrt(norm_f) if norm_f > 0 else 0.0
        p1 = math.sqrt(abs_beta) / math.sqrt(norm_f) if norm_f > 0 else 0.0
        p3_sq = max(0.0, 1.0 - (abs_alpha + 2 * abs_beta) / norm_f) if norm_f > 0 else 1.0

        self.prep_state: list[complex] = [
            complex(p0, 0), complex(p1, 0),
            complex(p1, 0), complex(math.sqrt(p3_sq), 0),
        ]

        self._build_program_list()

    def _build_program_list(self):
        self.program_list = []

        # Split ancilla register
        self.program_list.append(
            SplitRegister(reg_list=[self.anc_UA, "_overflow", "_other"], param_list=[1, 1]))

        # State preparation on ancilla
        self.program_list.append(
            Rot_GeneralStatePrep(reg_list=[self.anc_UA], param_list=[self.prep_state]))

        # Conditional increment
        self.program_list.append(
            PlusOneOverflow(reg_list=[self.main_reg, "_overflow"], param_list=[1])
                .control_by_value({self.anc_UA: 1}))

        # Reflections if beta < 0
        if self.beta < 0:
            self.program_list.append(
                Reflection_Bool(reg_list=[self.main_reg, "_overflow"], param_list=[False])
                    .control_by_value({self.anc_UA: 1}))
            self.program_list.append(
                Reflection_Bool(reg_list=[self.main_reg, "_overflow"], param_list=[False])
                    .control_by_value({self.anc_UA: 2}))

        # Uncompute increment (dagger uses anc_UA=2, the complement of forward's anc_UA=1)
        self.program_list.append(
            PlusOneOverflow(reg_list=[self.main_reg, "_overflow"], param_list=[1])
                .control_by_value({self.anc_UA: 2})
                .dagger())

        # X gate on "other" qubit
        self.program_list.append(
            XGate(reg_list=["_other"], param_list=[0]).control_by_all_ones(self.anc_UA))

        # Uncompute state preparation
        self.program_list.append(
            Rot_GeneralStatePrep(reg_list=[self.anc_UA], param_list=[self.prep_state]).dagger())

        # Recombine ancilla
        self.program_list.append(
            CombineRegister(reg_list=[self.anc_UA, "_other"]))
        self.program_list.append(
            CombineRegister(reg_list=[self.anc_UA, "_overflow"]))

        self.declare_program_list()

    def t_count(self, dagger_ctx=False, controllers_ctx=None):
        # Delegates to visitor pattern via children
        return None

    def pyqsparse_object(self, dagger_ctx=False, controllers_ctx=None):
        raise NotImplementedError(
            "BlockEncodingTridiagonal uses pysparq-level SplitRegister/CombineRegister; "
            "use pysparq directly for simulation")


# ==============================================================================
# UR (Right-multiplication operator)
# ==============================================================================

class UR(StandardComposite):
    """Right-multiplication operator for QRAM-based block encoding.

    Encodes column norms of the target matrix. Iterates over address bits,
    performing QRAM loads, division, conditional rotation, and uncomputation.
    """

    def __init__(
        self,
        reg_list=None,
        param_list=None,
        submodules=None,
        qram=None,
        column_index: str = "col",
        data_size: int = 32,
        rational_size: int = 16,
    ):
        if reg_list is None:
            reg_list = [column_index]
        super().__init__(reg_list=reg_list, param_list=param_list, submodules=submodules or [])
        self.qram = qram
        self.column_index = column_index
        self.data_size = data_size
        self.rational_size = rational_size
        self.addr_size = reg_sz(column_index)
        self._build_program_list()

    def _build_program_list(self):
        from ..primitives.arithmetic import (
            Add_ConstUInt, Mult_UInt_ConstUInt,
            ShiftLeft, ShiftRight,
            Div_Sqrt_Arccos_Int_Int,
        )
        from ..primitives.gates import X as XGate
        from ..primitives.qram import QRAMFast
        from ..primitives.cond_rot import CondRot_General_Bool
        from ..primitives.state_prep import ClearZero

        def pow2(n: int) -> int:
            return 1 << n

        self.program_list = []

        # Create angle-function closure capturing rational_size (n_digit).
        # pysparq CondRot_General_Bool calls angle_function(value, n_digit).
        n_digit = self.rational_size
        func = lambda value, _n=n_digit: make_func(value, _n)

        for k in range(self.addr_size):
            # Split one bit from column_index
            self.program_list.append(
                SplitRegister(reg_list=[self.column_index, "_rot"], param_list=[1]))

            self.program_list.append(
                CombineRegister(reg_list=[self.column_index, "_tmp_bit"]))

            self.program_list.append(
                ShiftRight(reg_list=[self.column_index], param_list=[1]))

            # In-place: column_index += pow2(k) - 1
            self.program_list.append(
                Add_ConstUInt(reg_list=[self.column_index, self.column_index], param_list=[pow2(k) - 1]))

            # Multiply: _addr_child = column_index * 2
            self.program_list.append(
                Mult_UInt_ConstUInt(reg_list=[self.column_index, "_addr_child"], param_list=[2]))

            self.program_list.append(
                XGate(reg_list=["_addr_child"], param_list=[0]))

            self.program_list.append(
                QRAMFast(reg_list=[self.column_index, "_data_parent"], param_list=[self.qram]))

            self.program_list.append(
                QRAMFast(reg_list=["_addr_child", "_data_child"], param_list=[self.qram]))

            self.program_list.append(
                Div_Sqrt_Arccos_Int_Int(
                    reg_list=["_data_child", "_data_parent", "_div_result"],
                    param_list=[]))

            self.program_list.append(
                CondRot_General_Bool(
                    reg_list=["_div_result", "_rot"],
                    param_list=[func]))  # 3-arg: pass angle_function

            self.program_list.append(ClearZero(reg_list=[], param_list=[1e-10]))

            # Uncompute
            self.program_list.append(
                Div_Sqrt_Arccos_Int_Int(
                    reg_list=["_data_child", "_data_parent", "_div_result"],
                    param_list=[]))
            self.program_list.append(
                QRAMFast(reg_list=["_addr_child", "_data_child"], param_list=[self.qram]))
            self.program_list.append(
                QRAMFast(reg_list=[self.column_index, "_data_parent"], param_list=[self.qram]))
            self.program_list.append(
                XGate(reg_list=["_addr_child"], param_list=[0]))
            self.program_list.append(
                Mult_UInt_ConstUInt(reg_list=[self.column_index, "_addr_child"], param_list=[2]))
            # In-place: column_index -= (pow2(k) - 1)
            self.program_list.append(
                Add_ConstUInt(
                    reg_list=[self.column_index, self.column_index],
                    param_list=[-(pow2(k) - 1)]))
            self.program_list.append(
                ShiftLeft(reg_list=[self.column_index], param_list=[1]))
            self.program_list.append(
                SplitRegister(reg_list=[self.column_index, "_tmp_bit"], param_list=[1]))
            self.program_list.append(
                CombineRegister(reg_list=[self.column_index, "_rot"]))
            self.program_list.append(
                ShiftLeft(reg_list=[self.column_index], param_list=[1]))

        self.program_list.append(ShiftRight(reg_list=[self.column_index], param_list=[1]))
        self.declare_program_list()

    def pyqsparse_object(self, dagger_ctx=False, controllers_ctx=None):
        raise NotImplementedError(
            "UR is composite; use pysparq pysparq.algorithms.block_encoding.UR for simulation")


# ==============================================================================
# UL (Left-multiplication operator)
# ==============================================================================

class UL(StandardComposite):
    """Left-multiplication operator for QRAM-based block encoding.

    Encodes the row structure of the target matrix. Iterates over upper
    address bits, constructing parent/child addresses, loading from QRAM,
    computing rotation angles, and applying conditional rotations.
    """

    def __init__(
        self,
        reg_list=None,
        param_list=None,
        submodules=None,
        qram=None,
        row_index: str = "row",
        column_index: str = "col",
        data_size: int = 32,
        rational_size: int = 16,
    ):
        if reg_list is None:
            reg_list = [row_index]
        super().__init__(reg_list=reg_list, param_list=param_list, submodules=submodules or [])
        self.qram = qram
        self.row_index = row_index
        self.column_index = column_index
        self.data_size = data_size
        self.rational_size = rational_size
        self.addr_size = reg_sz(row_index)
        self._build_program_list()

    def _build_program_list(self):
        from ..primitives.arithmetic import (
            Add_ConstUInt, Add_Mult_UInt_ConstUInt,
            Add_UInt_UInt_InPlace, Mult_UInt_ConstUInt,
            ShiftLeft, ShiftRight, GetRotateAngle_Int_Int,
            Div_Sqrt_Arccos_Int_Int,
        )
        from ..primitives.gates import X as XGate
        from ..primitives.qram import QRAMFast
        from ..primitives.cond_rot import CondRot_General_Bool
        from ..primitives.state_prep import ClearZero

        def pow2(n: int) -> int:
            return 1 << n

        self.program_list = []

        # Create angle-function closure capturing rational_size (n_digit).
        n_digit = self.rational_size
        func = lambda value, _n=n_digit: make_func(value, _n)

        for k in range(self.addr_size, 2 * self.addr_size):
            self.program_list.append(
                SplitRegister(reg_list=[self.row_index, "_rot"], param_list=[1]))

            # In-place: _addr_parent += pow2(k) - 1
            self.program_list.append(
                Add_ConstUInt(
                    reg_list=["_addr_parent", "_addr_parent"], param_list=[pow2(k) - 1]))

            # Multiply-accumulate: _addr_parent += column_index * pow2(k-self.addr_size)
            # pysparq: Add_Mult_UInt_ConstUInt(column_index, pow2(k-self.addr_size), _addr_parent)
            self.program_list.append(
                Add_Mult_UInt_ConstUInt(
                    reg_list=[self.column_index, "_addr_parent"],
                    param_list=[pow2(k - self.addr_size), 0]))

            # In-place: _addr_parent += row_index
            self.program_list.append(
                Add_UInt_UInt_InPlace(
                    reg_list=[self.row_index, "_addr_parent"], param_list=[]))

            # Multiply: _addr_child = _addr_parent * 2
            self.program_list.append(
                Mult_UInt_ConstUInt(
                    reg_list=["_addr_parent", "_addr_child"], param_list=[2]))

            self.program_list.append(
                XGate(reg_list=["_addr_child"], param_list=[0]))

            if k != 2 * self.addr_size - 1:
                self.program_list.append(
                    QRAMFast(reg_list=["_addr_parent", "_data_parent"], param_list=[self.qram]))
                self.program_list.append(
                    QRAMFast(reg_list=["_addr_child", "_data_child"], param_list=[self.qram]))
                self.program_list.append(
                    Div_Sqrt_Arccos_Int_Int(
                        reg_list=["_data_child", "_data_parent", "_div_result"],
                        param_list=[]))
                self.program_list.append(
                    CondRot_General_Bool(
                        reg_list=["_div_result", "_rot"],
                        param_list=[func]))  # 3-arg: pass angle_function
                # Uncompute
                self.program_list.append(
                    Div_Sqrt_Arccos_Int_Int(
                        reg_list=["_data_child", "_data_parent", "_div_result"],
                        param_list=[]))
                self.program_list.append(
                    QRAMFast(reg_list=["_addr_parent", "_data_parent"], param_list=[self.qram]))
                self.program_list.append(
                    QRAMFast(reg_list=["_addr_child", "_data_child"], param_list=[self.qram]))
            else:
                # Last iteration: use GetRotateAngle
                self.program_list.append(
                    ShiftLeft(reg_list=["_addr_parent"], param_list=[1]))
                self.program_list.append(
                    XGate(reg_list=["_addr_parent"], param_list=[0]))
                # In-place: _addr_child += 1
                self.program_list.append(
                    Add_ConstUInt(reg_list=["_addr_child", "_addr_child"], param_list=[1]))
                self.program_list.append(
                    QRAMFast(reg_list=["_addr_parent", "_data_parent"], param_list=[self.qram]))
                self.program_list.append(
                    QRAMFast(reg_list=["_addr_child", "_data_child"], param_list=[self.qram]))
                self.program_list.append(
                    GetRotateAngle_Int_Int(
                        reg_list=["_data_parent", "_data_child", "_div_result"],
                        param_list=[]))
                self.program_list.append(
                    CondRot_General_Bool(
                        reg_list=["_data_parent", "_rot"],
                        param_list=[func]))  # 3-arg: pass angle_function
                # Uncompute
                self.program_list.append(
                    GetRotateAngle_Int_Int(
                        reg_list=["_data_parent", "_data_child", "_div_result"],
                        param_list=[]))
                self.program_list.append(
                    QRAMFast(reg_list=["_addr_parent", "_data_parent"], param_list=[self.qram]))
                self.program_list.append(
                    QRAMFast(reg_list=["_addr_child", "_data_child"], param_list=[self.qram]))
                # In-place: _addr_child -= 1 (dagger)
                self.program_list.append(
                    Add_ConstUInt(reg_list=["_addr_child", "_addr_child"], param_list=[-1]))
                self.program_list.append(
                    XGate(reg_list=["_addr_parent"], param_list=[0]))
                self.program_list.append(
                    ShiftRight(reg_list=["_addr_parent"], param_list=[1]))

            # Uncompute address computation
            self.program_list.append(
                XGate(reg_list=["_addr_child"], param_list=[0]))
            self.program_list.append(
                Mult_UInt_ConstUInt(
                    reg_list=["_addr_parent", "_addr_child"], param_list=[2]))
            # Uncompute: _addr_parent -= row_index
            self.program_list.append(
                Add_UInt_UInt_InPlace(
                    reg_list=[self.row_index, "_addr_parent"], param_list=[]).dagger())
            # Uncompute multiply-accumulate
            self.program_list.append(
                Add_Mult_UInt_ConstUInt(
                    reg_list=[self.column_index, "_addr_parent"],
                    param_list=[pow2(k - self.addr_size), 0]).dagger())
            # Uncompute: _addr_parent -= pow2(k) - 1
            self.program_list.append(
                Add_ConstUInt(
                    reg_list=["_addr_parent", "_addr_parent"], param_list=[-(pow2(k) - 1)]))
            self.program_list.append(
                CombineRegister(reg_list=[self.row_index, "_rot"]))
            self.program_list.append(
                ShiftLeft(reg_list=[self.row_index], param_list=[1]))

        self.program_list.append(ShiftRight(reg_list=[self.row_index], param_list=[1]))
        self.declare_program_list()

    def pyqsparse_object(self, dagger_ctx=False, controllers_ctx=None):
        raise NotImplementedError(
            "UL is composite; use pysparq pysparq.algorithms.block_encoding.UL for simulation")


# ==============================================================================
# BlockEncodingViaQRAM
# ==============================================================================

class BlockEncodingViaQRAM(StandardComposite):
    """Block encoding of an arbitrary matrix via QRAM.

    Composed as: U_A = SWAP(row, col) · U_R†(col) · U_L(row, col)

    Attributes:
        qram: pysparq.QRAMCircuit_qutrit
        row_index: Row index register
        column_index: Column index register
        data_size: Data register bit size
        rational_size: Rational rotation register bit size
    """

    def __init__(
        self,
        reg_list=None,
        param_list=None,
        submodules=None,
        qram=None,
        row_index: str = "row",
        column_index: str = "col",
        data_size: int = 32,
        rational_size: int = 16,
    ):
        if reg_list is None:
            reg_list = [row_index, column_index]
        super().__init__(reg_list=reg_list, param_list=param_list, submodules=submodules or [])
        self.qram = qram
        self.row_index = row_index
        self.column_index = column_index
        self.data_size = data_size
        self.rational_size = rational_size
        self._build_program_list()

    def _build_program_list(self):
        from ..primitives.arithmetic import Swap_General_General

        self.program_list = [
            UL(qram=self.qram, row_index=self.row_index,
               column_index=self.column_index,
               data_size=self.data_size, rational_size=self.rational_size),
            UR(qram=self.qram, column_index=self.column_index,
               data_size=self.data_size, rational_size=self.rational_size).dagger(),
            Swap_General_General(
                reg_list=[self.row_index, self.column_index], param_list=[]),
        ]
        self.declare_program_list()

    def pyqsparse_object(self, dagger_ctx=False, controllers_ctx=None):
        raise NotImplementedError(
            "BlockEncodingViaQRAM is composite; "
            "use pysparq pysparq.algorithms.block_encoding.BlockEncodingViaQRAM")


# ==============================================================================
# PlusOneOverflow (local Primitive for block encoding)
# ==============================================================================

class PlusOneOverflow(Primitive):
    """Increment main register by 1, with overflow flag.

    Used in BlockEncodingTridiagonal for controlled increment.
    Implements ps.PlusOneAndOverflow(main_reg, overflow_reg).

    The forward operation conditions on anc_UA=1, the dagger on anc_UA=2.
    """
    __self_conjugate__ = False

    def __init__(self, reg_list, param_list=None):
        super().__init__(reg_list=reg_list, param_list=param_list)
        self.main_reg = reg_list[0] if len(reg_list) > 0 else None
        self.overflow_reg = reg_list[1] if len(reg_list) > 1 else None
        self.cond_value = param_list[0] if param_list else None

    def dagger(self):
        self.dagger_flag = not self.dagger_flag
        return self

    def pyqsparse_object(self, dagger_ctx=False, controllers_ctx=None):
        controllers_ctx = merge_controllers(self.controllers, controllers_ctx or {})
        obj = PyQSparseOperationWrapper(
            ps.PlusOneAndOverflow(self.main_reg, self.overflow_reg))
        obj.set_controller(controllers_ctx)
        if self.cond_value is not None:
            obj.conditioned_by_value({self.overflow_reg: self.cond_value})
        return obj

    def t_count(self, dagger_ctx=False, controllers_ctx=None):
        ncontrols = get_control_qubit_count(
            merge_controllers(self.controllers, controllers_ctx or {}))
        # Ripple-carry increment: O(n) Toffoli
        n = reg_sz(self.main_reg)
        return 4 * n


# Alias for compatibility
BlockEncoding = BlockEncodingViaQRAM
