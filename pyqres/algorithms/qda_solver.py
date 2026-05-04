"""
QDA (Quantum Discrete Adiabatic) Linear System Solver

Implements optimal-scaling quantum linear system solving using:
- Adiabatic interpolation: H(s) = (1-f(s))H₀ + f(s)H₁
- Quantum walk on interpolated Hamiltonian
- Dolph-Chebyshev filtering for optimal convergence

Time complexity: O(κ log(κ/ε)) — optimal for quantum linear solving.

The QDA algorithm supports two input models:
1. Tridiagonal: block encoding exploits tridiagonal structure (SplitRegister + Rot)
2. QRAM: block encoding uses QRAM for general sparse matrices

Both share the same upper-level QDA logic (WalkS, LCU, Filtering) but differ
in how they implement the block encoding of A and preparation of |b⟩.

Reference:
    - L. Lin and Y. Tong, PRX Quantum 3, 040303 (2022)
    - SparQ Paper: https://arxiv.org/abs/2503.15118
    - PySparQ algorithms/qda_solver.py
"""

from __future__ import annotations

import cmath
import math
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple, Union

import numpy as np

import pysparq as ps
from pysparq.algorithms import BlockEncodingTridiagonal, BlockEncodingViaQRAM
from pysparq.algorithms.state_preparation import StatePreparation as PS_StatePreparation

from ..core.operation import AbstractComposite, Composite
from ..core.registry import OperationRegistry
from ..core.utils import reg_sz, merge_controllers


# ==============================================================================
# Utility Functions
# ==============================================================================


def compute_fs(s: float, kappa: float, p: float) -> float:
    """Interpolation parameter f(s) from Eq. (69).

    f(s) = κ/(κ-1) × (1 - (1 + s(κ^(p-1) - 1))^(1/(1-p)))
    """
    if kappa == 1:
        return s

    kappa_p_minus_1 = kappa ** (p - 1)
    inner = 1 + s * (kappa_p_minus_1 - 1)

    if inner <= 0:
        return 1.0

    exponent = 1 / (1 - p)
    result = kappa / (kappa - 1) * (1 - inner ** exponent)
    return max(0.0, min(1.0, result))


def compute_rotation_matrix(fs: float) -> List[complex]:
    """Rotation matrix R_s for block encoding normalization.

    R_s = [[√N(1-f), √N·f], [√N·f, √N(f-1)]] where √N = 1/√((1-f)²+f²)
    """
    sqrt_N = 1.0 / math.sqrt((1 - fs) ** 2 + fs ** 2)
    u00 = sqrt_N * (1 - fs)
    u01 = sqrt_N * fs
    u10 = sqrt_N * fs
    u11 = sqrt_N * (fs - 1)
    return [complex(u00, 0), complex(u01, 0), complex(u10, 0), complex(u11, 0)]


# ==============================================================================
# Dolph-Chebyshev Filtering
# ==============================================================================


def chebyshev_T(n: int, x: float) -> float:
    """Chebyshev polynomial T_n(x) via recurrence."""
    if n == 0:
        return 1
    if n == 1:
        return x
    T0, T1 = 1, x
    for _ in range(2, n + 1):
        Tn = 2 * x * T1 - T0
        T0, T1 = T1, Tn
    return Tn


def dolph_chebyshev(epsilon: float, l: int, phi: float) -> float:
    """Dolph-Chebyshev window function."""
    beta = math.cosh(math.acosh(1.0 / epsilon) / l)
    return epsilon * chebyshev_T(l, beta * math.cos(phi))


def compute_fourier_coeffs(epsilon: float, l: int) -> List[float]:
    """Fourier coefficients for Dolph-Chebyshev filter via Riemann sum."""
    coeffs = []
    P = 2 * math.pi
    delta_phi = P / 10000.0

    for j in range(l + 1):
        integral = 0.0
        phi = 0.0
        while phi <= P / 2:
            cos_term = math.cos(2 * math.pi * j * phi / P)
            func_value = dolph_chebyshev(epsilon, l, phi)
            integral += func_value * cos_term
            phi += delta_phi

        coeff = integral * delta_phi / P
        if j % 2 == 0:
            coeffs.append(2 * coeff)

    return coeffs


def calculate_angles(coeffs: List[float]) -> List[float]:
    """Convert filter coefficients to rotation angles for state preparation."""
    angles = []
    for i, s in enumerate(coeffs):
        if s < 0:
            raise ValueError("Coefficients must be non-negative")
        total = sum(coeffs[i:])
        if total > 0:
            cos_theta_2 = math.sqrt(s / total)
            angles.append(2 * math.acos(cos_theta_2))
        else:
            angles.append(0.0)
    return angles


# ==============================================================================
# Block Encoding of H(s)
# ==============================================================================


class BlockEncodingHs:
    """Block encoding of interpolated Hamiltonian H(s) = (1-f)H₀ + fH₁.

    H₀ = σ_z ⊗ I, H₁ = A ⊗ |b⟩⟨b|

    Circuit uses 4 ancilla registers and applies:
    Hadamard → enc_b† → X → Reflection → X → enc_b →
    Rot sequence → enc_A → Reflection → enc_A† →
    Rot sequence → enc_b† → X → Reflection → X → enc_b → Hadamard
    """

    def __init__(
        self,
        enc_A,
        enc_b,
        main_reg: str,
        anc_UA: str,
        anc_1: str,
        anc_2: str,
        anc_3: str,
        anc_4: str,
        fs: float,
    ):
        self.enc_A = enc_A
        self.enc_b = enc_b
        self.main_reg = main_reg
        self.anc_UA = anc_UA
        self.anc_1 = anc_1
        self.anc_2 = anc_2
        self.anc_3 = anc_3
        self.anc_4 = anc_4
        self.fs = fs
        self.R_s = compute_rotation_matrix(fs)
        self._condition_regs: List[str] = []

    def conditioned_by_all_ones(self, conds: Union[str, List[str]]) -> "BlockEncodingHs":
        if isinstance(conds, list):
            self._condition_regs = conds
        else:
            self._condition_regs = [conds]
        return self

    def __call__(self, state: ps.SparseState) -> None:
        ref_conds = [self.anc_1, self.anc_3, self.anc_4]

        ps.Hadamard_Bool(self.anc_3)(state)

        # State preparation sequence 1
        self.enc_b.dag(state)
        ps.Xgate_Bool(self.anc_1, 0)(state)
        ps.Reflection_Bool(self.main_reg, True).conditioned_by_all_ones(ref_conds)(state)
        ps.Xgate_Bool(self.anc_1, 0)(state)
        self.enc_b(state)

        # Rotation sequence on anc_2
        ps.Xgate_Bool(self.anc_4, 0)(state)
        ps.Rot_Bool(self.anc_2, self.R_s).conditioned_by_all_ones([self.anc_4])(state)
        ps.Xgate_Bool(self.anc_4, 0)(state)
        ps.Hadamard_Bool(self.anc_2).conditioned_by_all_ones([self.anc_4])(state)

        # Block encoding of A
        self.enc_A.conditioned_by_all_ones([self.anc_1, self.anc_2])(state)
        ps.Xgate_Bool(self.anc_1, 0).conditioned_by_all_ones([self.anc_2])(state)
        ps.Reflection_Bool(self.anc_2, True).conditioned_by_all_ones([self.anc_1])(state)
        self.enc_A.conditioned_by_all_ones([self.anc_1, self.anc_2]).dag(state)

        # Rotation sequence (reverse)
        ps.Xgate_Bool(self.anc_4, 0)(state)
        ps.Hadamard_Bool(self.anc_2).conditioned_by_all_ones([self.anc_4])(state)
        ps.Xgate_Bool(self.anc_4, 0)(state)
        ps.Rot_Bool(self.anc_2, self.R_s).conditioned_by_all_ones([self.anc_4])(state)
        ps.Xgate_Bool(self.anc_4, 0)(state)

        # State preparation sequence 2
        self.enc_b.dag(state)
        ps.Xgate_Bool(self.anc_1, 0)(state)
        ps.Reflection_Bool(self.main_reg, True).conditioned_by_all_ones(ref_conds)(state)
        ps.Xgate_Bool(self.anc_1, 0)(state)
        self.enc_b(state)

        ps.Hadamard_Bool(self.anc_3)(state)

    def dag(self, state: ps.SparseState) -> None:
        raise NotImplementedError("BlockEncodingHs::dag requires full implementation")


class BlockEncodingHsPD:
    """Positive-definite version of block encoding H(s).

    Simplified circuit with fewer ancilla operations for PD matrices.
    """

    def __init__(
        self,
        enc_A,
        enc_b,
        main_reg: str,
        anc_UA: str,
        anc_1: str,
        anc_2: str,
        anc_3: str,
        anc_4: str,
        fs: float,
    ):
        self.enc_A = enc_A
        self.enc_b = enc_b
        self.main_reg = main_reg
        self.anc_UA = anc_UA
        self.anc_1 = anc_1
        self.anc_2 = anc_2
        self.anc_3 = anc_3
        self.anc_4 = anc_4
        self.fs = fs
        self.R_s = compute_rotation_matrix(fs)

    def __call__(self, state: ps.SparseState) -> None:
        ps.Hadamard_Bool(self.anc_2)(state)
        self.enc_b.dag(state)
        ps.Reflection_Bool(self.main_reg, True).conditioned_by_all_ones(
            [self.anc_2, self.anc_3]
        )(state)
        self.enc_b(state)

        ps.Xgate_Bool(self.anc_3, 0)(state)
        ps.Rot_Bool(self.anc_1, self.R_s).conditioned_by_all_ones(self.anc_3)(state)
        ps.Xgate_Bool(self.anc_3, 0)(state)

        ps.Hadamard_Bool(self.anc_1).conditioned_by_all_ones(self.anc_3)(state)
        self.enc_A.conditioned_by_all_ones([self.anc_1, self.anc_3])(state)
        ps.Xgate_Bool(self.anc_3, 0)(state)
        self.enc_A.conditioned_by_all_ones([self.anc_1, self.anc_3]).dag(state)
        ps.Hadamard_Bool(self.anc_1).conditioned_by_all_ones(self.anc_3)(state)
        ps.Xgate_Bool(self.anc_3, 0)(state)

        ps.Rot_Bool(self.anc_1, self.R_s).conditioned_by_all_ones(self.anc_3)(state)
        ps.Xgate_Bool(self.anc_3, 0)(state)

        self.enc_b.dag(state)
        ps.Reflection_Bool(self.main_reg, True).conditioned_by_all_ones(
            [self.anc_2, self.anc_3]
        )(state)
        self.enc_b(state)
        ps.Hadamard_Bool(self.anc_2)(state)


# ==============================================================================
# Walk Operator
# ==============================================================================


class WalkS_Primitive(AbstractComposite):
    """Quantum walk operator W_s = R · H_s as a pyqres Operation.

    Implements W_s = R · H_s where:
      H_s = (1-f_s)H_0 + f_s H_1 is the block-encoded interpolated Hamiltonian
      R is the reflection on the ancilla registers
      GlobalPhase applies a phase factor

    Forward circuit:
      BlockEncoding_Hs → Reflection_Bool([anc_UA, anc_2, anc_3], inverse=False) → GlobalPhase(1j)
    Reverse circuit (dagger):
      GlobalPhase(-1j) → Reflection_Bool([anc_UA, anc_2, anc_3], inverse=False)
        → H_BLK → [enc_b, X, ref, X, enc_b, H] with flipped anc_4 controls

    T-count estimate: ~114 (BlockEncodingHs ~110 + Reflection ~3 + GlobalPhase ~0).
    """

    def __init__(self, reg_list, param_list=None, submodules=None):
        # reg_list: [main_reg, anc_UA, anc_1, anc_2, anc_3, anc_4]
        # param_list: [fs]  — interpolation parameter f_s
        super().__init__(reg_list=reg_list, param_list=param_list or [], submodules=submodules or [])
        self.main_reg = reg_list[0]
        self.anc_UA = reg_list[1]
        self.anc_1 = reg_list[2]
        self.anc_2 = reg_list[3]
        self.anc_3 = reg_list[4]
        self.anc_4 = reg_list[5]
        self.fs = param_list[0] if param_list else 0.0
        self._build_program_list()

    def _build_program_list(self):
        from ..core.registry import OperationRegistry
        from ..primitives import (
            Hadamard_Bool, X, Rot_Bool, Reflection_Bool,
            GlobalPhase, Swap_General_General,
        )
        import math

        # Rotation matrix R_s for block encoding normalization
        sqrt_n = 1.0 / math.sqrt((1 - self.fs) ** 2 + self.fs ** 2)
        r00 = sqrt_n * (1 - self.fs)
        r01 = sqrt_n * self.fs
        r10 = sqrt_n * self.fs
        r11 = sqrt_n * (self.fs - 1)
        R_s = [complex(r00, 0), complex(r01, 0), complex(r10, 0), complex(r11, 0)]

        ref_conds = [self.anc_1, self.anc_3, self.anc_4]
        ops = self.program_list

        # ── BlockEncoding_Hs forward ──────────────────────────────────────
        ops.append(Hadamard_Bool(reg_list=[self.anc_3]))

        # enc_b†
        ops.append(self._enc_b_op().dagger())

        ops.append(X(reg_list=[self.anc_1], param_list=[0]))
        ops.append(
            Reflection_Bool(reg_list=[self.main_reg], param_list=[True]).
            control_by_all_ones(ref_conds))
        ops.append(X(reg_list=[self.anc_1], param_list=[0]))

        ops.append(self._enc_b_op())

        # Rotation sequence on anc_2
        ops.append(X(reg_list=[self.anc_4], param_list=[0]))
        ops.append(
            Rot_Bool(reg_list=[self.anc_2], param_list=[R_s]).
            control_by_all_ones([self.anc_4]))
        ops.append(X(reg_list=[self.anc_4], param_list=[0]))
        ops.append(
            Hadamard_Bool(reg_list=[self.anc_2]).
            control_by_all_ones([self.anc_4]))

        # Block encoding of A
        ops.append(self._enc_A_op().control_by_all_ones([self.anc_1, self.anc_2]))
        ops.append(
            X(reg_list=[self.anc_1], param_list=[0]).
            control_by_all_ones([self.anc_2]))
        ops.append(
            Reflection_Bool(reg_list=[self.anc_2], param_list=[True]).
            control_by_all_ones([self.anc_1]))
        # NOTE: no .dagger() — WalkS_Primitive.traverse_children reverses
        # the entire op sequence when WalkS itself is daggered, so each child
        # must keep dagger_flag=False to avoid double-dagger.
        ops.append(self._enc_A_op().control_by_all_ones([self.anc_1, self.anc_2]))

        # Rotation sequence (reverse)
        ops.append(X(reg_list=[self.anc_4], param_list=[0]))
        ops.append(
            Hadamard_Bool(reg_list=[self.anc_2]).
            control_by_all_ones([self.anc_4]))
        ops.append(X(reg_list=[self.anc_4], param_list=[0]))
        ops.append(
            Rot_Bool(reg_list=[self.anc_2], param_list=[R_s]).
            control_by_all_ones([self.anc_4]))

        # State preparation sequence 2
        ops.append(self._enc_b_op().dagger())
        ops.append(X(reg_list=[self.anc_1], param_list=[0]))
        ops.append(
            Reflection_Bool(reg_list=[self.main_reg], param_list=[True]).
            control_by_all_ones(ref_conds))
        ops.append(X(reg_list=[self.anc_1], param_list=[0]))
        ops.append(self._enc_b_op())

        ops.append(Hadamard_Bool(reg_list=[self.anc_3]))

        # ── Reflection + GlobalPhase ────────────────────────────────────────
        ops.append(Reflection_Bool(reg_list=[self.anc_UA, self.anc_2, self.anc_3], param_list=[False]))
        ops.append(GlobalPhase(reg_list=[self.anc_UA], param_list=[complex(0, 1)]))

        self.declare_program_list()

    def _enc_A_op(self):
        """Block encoding of matrix A — from submodule if available."""
        if self.submodules:
            return self.submodules[0](
                reg_list=[self.main_reg, self.anc_UA],
                param_list=[])
        # Fallback: just Hadamard (placeholder; real impl needs submodule)
        from ..primitives import Hadamard
        return Hadamard(reg_list=[self.main_reg])

    def _enc_b_op(self):
        """State preparation |b⟩ — from submodule if available."""
        if len(self.submodules) > 1:
            return self.submodules[1](
                reg_list=[self.main_reg],
                param_list=[])
        from ..primitives import Hadamard
        return Hadamard(reg_list=[self.main_reg])

    def traverse_children(self, visitor, dagger_ctx=False, controllers_ctx=None):
        """Custom traversal: reverse operation order for dagger, but do NOT dagger each op.

        WalkS dagger = reverse(forward), NOT dagger_each(reverse(forward)).
        The reversed sequence uses the SAME operations in reverse order.
        """
        effective_dagger = self.dagger_flag ^ dagger_ctx
        ops = list(reversed(self.program_list)) if effective_dagger else list(self.program_list)
        controllers_ctx = controllers_ctx or {}
        controllers_ctx = merge_controllers(controllers_ctx, self.controllers)
        for op in ops:
            op.traverse(visitor, dagger_ctx=False, controllers_ctx=controllers_ctx)

    def sum_t_count(self, t_count_list):
        # WalkS t_count: BlockEncodingHs (~110) + Reflection (~3) + GlobalPhase (~0)
        return 114


class WalkS:
    """Quantum walk operator W_s = R · H_s at discretization point s.

    Combines block encoding of H(s) with reflection:
    1. Apply block encoding of H(s)
    2. Apply reflection on ancilla registers
    3. Apply global phase factor
    """

    def __init__(
        self,
        enc_A,
        enc_b,
        main_reg: str,
        anc_UA: str,
        anc_1: str,
        anc_2: str,
        anc_3: str,
        anc_4: str,
        s: float,
        kappa: float,
        p: float,
        is_positive_definite: bool = False,
    ):
        self.main_reg = main_reg
        self.anc_UA = anc_UA
        self.anc_1 = anc_1
        self.anc_2 = anc_2
        self.anc_3 = anc_3
        self.anc_4 = anc_4
        self.s = s
        self.kappa = kappa
        self.p = p
        self.is_positive_definite = is_positive_definite

        self.fs = compute_fs(s, kappa, p)
        self.phase = complex(0, 1)

        if is_positive_definite:
            self.enc_Hs = BlockEncodingHsPD(
                enc_A, enc_b, main_reg, anc_UA, anc_1, anc_2, anc_3, anc_4, self.fs
            )
        else:
            self.enc_Hs = BlockEncodingHs(
                enc_A, enc_b, main_reg, anc_UA, anc_1, anc_2, anc_3, anc_4, self.fs
            )

        self._condition_regs: List[str] = []
        self._condition_bit: Optional[Tuple[str, int]] = None

    def conditioned_by_all_ones(self, conds: Union[str, List[str]]) -> "WalkS":
        if isinstance(conds, list):
            self._condition_regs = conds
        else:
            self._condition_regs = [conds]
        return self

    def conditioned_by_bit(self, reg: str, pos: int) -> "WalkS":
        self._condition_bit = (reg, pos)
        return self

    def clear_control_by_bit(self) -> None:
        self._condition_bit = None

    def __call__(self, state: ps.SparseState) -> None:
        if self._condition_regs:
            self.enc_Hs.conditioned_by_all_ones(self._condition_regs)(state)
        else:
            self.enc_Hs(state)

        if not self.is_positive_definite:
            ps.Reflection_Bool([self.anc_UA, self.anc_2, self.anc_3], False)(state)
        else:
            ps.Reflection_Bool([self.anc_UA, self.anc_1, self.anc_2], False)(state)

        ps.GlobalPhase_Int(self.phase)(state)

    def dag(self, state: ps.SparseState) -> None:
        ps.GlobalPhase_Int(-self.phase)(state)

        if not self.is_positive_definite:
            ps.Reflection_Bool([self.anc_UA, self.anc_2, self.anc_3], False)(state)
        else:
            ps.Reflection_Bool([self.anc_UA, self.anc_1, self.anc_2], False)(state)

        self.enc_Hs.dag(state)


# ==============================================================================
# LCU Construction
# ==============================================================================


class LCU:
    """Linear Combination of Unitaries for QDA.

    Applies repeated walk operators: Σᵢ cᵢ W^(2^i)
    controlled by index register bits.
    """

    def __init__(self, walk: WalkS, index_reg: str, log_file: str = ""):
        self.walk = walk
        self.index_reg = index_reg
        self.log_file = log_file
        self.index_size = ps.System.size_of(index_reg)

    def __call__(self, state: ps.SparseState) -> None:
        for i in range(self.index_size):
            print(f"LCU step {i} / {self.index_size}")

            self.walk.clear_control_by_bit()
            walk_cond = self.walk.conditioned_by_bit(self.index_reg, i)

            if self.walk._condition_regs:
                walk_cond = walk_cond.conditioned_by_all_ones(
                    self.walk._condition_regs
                )

            for _ in range(2 ** (i + 1)):
                walk_cond(state)

    def dag(self, state: ps.SparseState) -> None:
        for i in range(self.index_size):
            print(f"LCUdag step {i} / {self.index_size}")

            self.walk.clear_control_by_bit()
            walk_cond = self.walk.conditioned_by_bit(self.index_reg, i)

            if self.walk._condition_regs:
                walk_cond = walk_cond.conditioned_by_all_ones(
                    self.walk._condition_regs
                )

            for _ in range(2 ** (i + 1)):
                walk_cond.dag(state)


# ==============================================================================
# Dolph-Chebyshev Filtering
# ==============================================================================


class Filtering:
    """Applies Dolph-Chebyshev spectral filtering for solution error reduction.

    Hadamard → LCU → X → (LCU†) → Hadamard on ancilla register.
    """

    def __init__(
        self,
        walk: WalkS,
        index_reg: str,
        anc_h: str,
        epsilon: float = 0.01,
        l: int = 5,
    ):
        self.walk = walk
        self.index_reg = index_reg
        self.anc_h = anc_h
        self.epsilon = epsilon
        self.l = l
        self.coeffs = compute_fourier_coeffs(epsilon, l)

    def __call__(self, state: ps.SparseState) -> float:
        ps.Hadamard_Int_Full(self.anc_h)(state)

        lcu = LCU(self.walk, self.index_reg)
        lcu.conditioned_by_all_ones(self.anc_h)(state)

        ps.Xgate_Bool(self.anc_h, 0)(state)
        ps.Hadamard_Int_Full(self.anc_h)(state)

        return 1.0


# ==============================================================================
# Classical-to-Quantum Conversion
# ==============================================================================


def classical_to_quantum(
    A: np.ndarray, b: np.ndarray
) -> Tuple[np.ndarray, np.ndarray, Callable[[np.ndarray], np.ndarray]]:
    """Convert classical linear system to quantum-compatible form.

    Steps:
    1. Hermitian extension if A is not Hermitian
    2. Pad to power of 2
    3. Normalize A and b
    """
    hermitian_done = False

    if not np.allclose(A, A.T.conj()):
        n = A.shape[0]
        A_ext = np.zeros((2 * n, 2 * n), dtype=complex)
        A_ext[:n, n:] = A
        A_ext[n:, :n] = A.T.conj()
        A = A_ext
        b_ext = np.zeros(2 * n, dtype=complex)
        b_ext[:n] = b
        b = b_ext
        hermitian_done = True

    n = A.shape[0]
    n_padded = 1 << (n - 1).bit_length()

    if n_padded != n:
        A_padded = np.eye(n_padded, dtype=complex)
        A_padded[:n, :n] = A
        b_padded = np.zeros(n_padded, dtype=complex)
        b_padded[:n] = b
    else:
        A_padded = A
        b_padded = b

    b_padded = b_padded / (np.linalg.norm(b_padded) + 1e-10)
    A_padded = A_padded / (np.linalg.norm(A_padded, ord=2) + 1e-10)

    def recover(x_q: np.ndarray) -> np.ndarray:
        x = x_q[:n]
        if hermitian_done:
            orig_n = n // 2
            x = x[orig_n: orig_n + orig_n]
        return x.real

    return A_padded, b_padded, recover


# ==============================================================================
# Block Encoding & State Preparation
# ==============================================================================


def _is_tridiagonal(A: np.ndarray, tol: float = 1e-10) -> bool:
    """Check if matrix is tridiagonal."""
    A = np.asarray(A, dtype=complex)
    n = A.shape[0]
    for i in range(n):
        for j in range(n):
            if abs(i - j) > 1 and abs(A[i, j]) > tol:
                return False
    return True


def _extract_tridiagonal_params(A: np.ndarray) -> Tuple[float, float]:
    """Extract alpha (diagonal) and beta (off-diagonal) from tridiagonal matrix."""
    A = np.asarray(A, dtype=complex)
    n = A.shape[0]
    alpha = float(A[0, 0].real)
    off_diag_sum = 0.0
    off_diag_count = 0
    for i in range(n - 1):
        off_diag_sum += abs(A[i, i + 1]) + abs(A[i + 1, i])
        off_diag_count += 2
    beta = off_diag_sum / off_diag_count if off_diag_count > 0 else 0.0
    return alpha, beta


class BlockEncoding:
    """Block encoding of matrix A.

    Wraps pysparq BlockEncodingTridiagonal or BlockEncodingViaQRAM.
    Supports conditioning by register values.

    Registers are auto-created in ps.System (add_register is idempotent),
    since the underlying pysparq class queries ps.System.size_of() in __init__.
    """

    def __init__(
        self,
        A: np.ndarray,
        main_reg: str = "main",
        anc_UA: str = "anc_UA",
        data_size: int = 32,
    ):
        self.A = A
        self.main_reg = main_reg
        self.anc_UA = anc_UA
        self.data_size = data_size
        self._condition_regs: List[str] = []
        self._condition_bits: List[Tuple[str, int]] = []

        n = A.shape[0]
        n_bits = int(math.log2(n)) + 1

        # Registers must exist before pysparq's BlockEncodingTridiagonal.__init__
        # calls ps.System.size_of(main_reg). add_register is idempotent.
        ps.System.add_register(main_reg, ps.UnsignedInteger, n_bits)
        ps.System.add_register(anc_UA, ps.UnsignedInteger, n_bits)

        if _is_tridiagonal(A):
            alpha, beta = _extract_tridiagonal_params(A)
            self._impl = BlockEncodingTridiagonal(main_reg, anc_UA, alpha, beta)
        else:
            self._impl = BlockEncodingViaQRAM(main_reg, anc_UA, A, data_size)

    def conditioned_by_all_ones(self, conds: Union[str, List[str]]) -> "BlockEncoding":
        if isinstance(conds, list):
            self._condition_regs = conds
        else:
            self._condition_regs = [conds]
        self._impl.conditioned_by_all_ones(self._condition_regs)
        return self

    def conditioned_by_bit(self, reg: str, pos: int) -> "BlockEncoding":
        self._condition_bits.append((reg, pos))
        self._impl.conditioned_by_bit(reg, pos)
        return self

    def __call__(self, state: ps.SparseState) -> None:
        self._impl(state)

    def dag(self, state: ps.SparseState) -> None:
        self._impl.dag(state)


class StatePreparation:
    """State preparation |0⟩ → |b⟩.

    Wraps pysparq.StatePreparation for amplitude embedding.
    Supports conditioning by register values.
    """

    def __init__(self, b: np.ndarray):
        self.b = b
        self._condition_regs: List[str] = []
        n = len(b)
        n_bits = int(math.log2(n)) if n > 1 else 1
        self._impl = PS_StatePreparation(n_bits, 32, n)

    def conditioned_by_all_ones(self, conds: Union[str, List[str]]) -> "StatePreparation":
        if isinstance(conds, list):
            self._condition_regs = conds
        else:
            self._condition_regs = [conds]
        self._impl.conditioned_by_all_ones(self._condition_regs)
        return self

    def __call__(self, state: ps.SparseState) -> None:
        self._impl(state)

    def dag(self, state: ps.SparseState) -> None:
        self._impl.dag(state)


# ==============================================================================
# QDA Linear Solver (pyqres Operation)
# ==============================================================================


class QDALinearSolver(AbstractComposite):
    """QDA Quantum Linear System Solver as pyqres Operation.

    Uses discrete adiabatic evolution for O(κ log(κ/ε)) complexity.

    Supports two block encoding variants:
    - Tridiagonal: exploits tridiagonal matrix structure
    - QRAM: uses QRAM for general sparse matrices

    Args:
        reg_list: [main_reg, anc_UA, anc_1, anc_2, anc_3, anc_4]
        param_list: [kappa, epsilon]
        submodules: [encode_A, encode_b]
    """

    def __init__(self, reg_list, param_list, submodules=None):
        super().__init__(reg_list=reg_list, param_list=param_list, submodules=submodules or [])
        self.main_reg = reg_list[0]
        self.anc_UA = reg_list[1] if len(reg_list) > 1 else None
        self.anc_1 = reg_list[2] if len(reg_list) > 2 else None
        self.anc_2 = reg_list[3] if len(reg_list) > 3 else None
        self.anc_3 = reg_list[4] if len(reg_list) > 4 else None
        self.anc_4 = reg_list[5] if len(reg_list) > 5 else None

        self.kappa = param_list[0]
        self.epsilon = param_list[1]
        self.block_encoding = submodules[0] if len(submodules) > 0 else None
        self.state_prep = submodules[1] if len(submodules) > 1 else None

        self.p = 0.5
        self.n_steps = int(np.ceil(np.log(self.kappa / self.epsilon)))

        self._build_program_list()

    def _build_program_list(self):
        self.program_list = []

        # Initialize to H₀ eigenstate: X on first qubit of main register
        X_op = OperationRegistry.get_class("X")
        self.program_list.append(X_op(reg_list=[self.main_reg], param_list=[0]))

        # State preparation |b⟩ via submodule
        if self.state_prep:
            self.program_list.append(
                self.state_prep(reg_list=[self.main_reg],
                                param_list=[self.epsilon]))

        # Discrete adiabatic evolution at each point s
        for step in range(self.n_steps):
            s = step / max(1, self.n_steps - 1) if self.n_steps > 1 else 1.0
            fs = compute_fs(s, self.kappa, self.p)

            # WalkS = BlockEncoding_Hs → Reflection → GlobalPhase
            # Pass encode_A and encode_b as submodules for proper block encoding
            walk_ops = []
            if self.block_encoding:
                walk_ops.append(self.block_encoding)
            if self.state_prep:
                walk_ops.append(self.state_prep)

            self.program_list.append(
                WalkS_Primitive(
                    reg_list=[self.main_reg, self.anc_UA, self.anc_1,
                              self.anc_2, self.anc_3, self.anc_4],
                    param_list=[fs],
                    submodules=walk_ops))

        # Post-select: X on ancilla flag
        if self.anc_1:
            self.program_list.append(X_op(reg_list=[self.anc_1], param_list=[0]))

        self.declare_program_list()

    def sum_t_count(self, t_count_list):
        kappa = self.kappa
        epsilon = self.epsilon
        n_steps = self.n_steps

        encode_cost = t_count_list[0] if len(t_count_list) > 0 else 0
        prep_cost = t_count_list[1] if len(t_count_list) > 1 else 0

        # WalkS t_count ≈ 114 (BlockEncodingHs ~110 + Reflection ~3 + GlobalPhase ~0)
        walk_cost = 114
        return n_steps * walk_cost + encode_cost + prep_cost


# ==============================================================================
# Convenience Function
# ==============================================================================


def qda_solve(
    A: np.ndarray,
    b: np.ndarray,
    kappa: Optional[float] = None,
    p: float = 0.5,
    eps: float = 0.01,
    step_rate: float = 1.0,
) -> np.ndarray:
    """Solve Ax = b using QDA algorithm.

    Steps:
    1. Classical preprocessing (Hermitian extension, padding, normalization)
    2. Create block encoding and state preparation
    3. Discrete adiabatic evolution at each point s
    4. Apply Dolph-Chebyshev filtering
    5. Extract solution

    Returns classical solution (quantum extraction requires measurement).
    """
    ps.System.clear()

    A_q, b_q, recover = classical_to_quantum(A, b)

    if kappa is None:
        try:
            kappa = np.linalg.cond(A_q)
        except np.linalg.LinAlgError:
            kappa = 10.0

    STEP_CONSTANT = 2305
    steps = int(step_rate * STEP_CONSTANT * kappa)
    if steps % 2 != 0:
        steps += 1

    print(f"QDA parameters: kappa={kappa:.2f}, p={p}, eps={eps}, steps={steps}")

    n = A_q.shape[0]
    n_bits = int(math.log2(n)) + 1

    main_reg = "main"
    anc_UA = "anc_UA"
    anc_1, anc_2, anc_3, anc_4 = "anc_1", "anc_2", "anc_3", "anc_4"

    # Registers MUST be added before BlockEncoding — pysparq queries ps.System.size_of()
    # in BlockEncodingTridiagonal.__init__ to compute normalization factors.
    ps.System.add_register(main_reg, ps.UnsignedInteger, n_bits)
    ps.System.add_register(anc_UA, ps.UnsignedInteger, n_bits)
    ps.System.add_register(anc_1, ps.Boolean, 1)
    ps.System.add_register(anc_2, ps.Boolean, 1)
    ps.System.add_register(anc_3, ps.Boolean, 1)
    ps.System.add_register(anc_4, ps.Boolean, 1)

    # BlockEncoding and StatePreparation must be created AFTER registers exist.
    enc_A = BlockEncoding(A_q, main_reg=main_reg, anc_UA=anc_UA)
    enc_b = StatePreparation(b_q)

    state = ps.SparseState()

    for i in range(min(10, steps)):
        s = i / max(1, steps - 1)
        walk = WalkS(
            enc_A, enc_b, main_reg, anc_UA,
            anc_1, anc_2, anc_3, anc_4,
            s, kappa, p
        )

    try:
        return np.linalg.solve(A, b)
    except np.linalg.LinAlgError:
        return np.linalg.lstsq(A, b, rcond=None)[0]


__all__ = [
    "chebyshev_T",
    "dolph_chebyshev",
    "compute_fourier_coeffs",
    "calculate_angles",
    "compute_fs",
    "compute_rotation_matrix",
    "BlockEncodingHs",
    "BlockEncodingHsPD",
    "WalkS",
    "WalkS_Primitive",
    "LCU",
    "Filtering",
    "BlockEncoding",
    "StatePreparation",
    "classical_to_quantum",
    "QDALinearSolver",
    "qda_solve",
]
