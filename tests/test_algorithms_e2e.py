"""End-to-end algorithm tests: CKS and QDA linear solver pipelines."""

import pytest
import numpy as np
import pysparq

from pyqres.core.operation import Primitive, Composite, AbstractComposite
from pyqres.core.metadata import RegisterMetadata, program_metadata
from pyqres.core.simulator import SimulatorVisitor
from pyqres.core.lowering import LoweringEngine, TCountEstimator, SimulationEstimator
from pyqres.primitives import (
    Hadamard, X, CNOT, Ry, SplitRegister,
    Init_Unsafe, Rot_GeneralStatePrep, Reflection_Bool,
)
from pyqres.core.utils import reg_sz, merge_controllers
from pyqres.core.simulator import PyQSparseOperationWrapper
from pyqres.generated import Swap, QDALinearSolver, CKSLinearSolver
from pyqres.algorithms.qda_solver import WalkS_Primitive

# Import pyqres algorithm helpers (re-exported from PySparQ)
from pyqres.algorithms.cks_solver import (
    SparseMatrix as PyqresSparseMatrix,
    ChebyshevPolynomialCoefficient,
    get_coef_positive_only, get_coef_common, make_walk_angle_func,
)
from pyqres.algorithms.qda_solver import (
    compute_fs, compute_rotation_matrix,
    chebyshev_T, dolph_chebyshev, compute_fourier_coeffs, calculate_angles,
    classical_to_quantum,
)

# Import BlockEncoding and StatePreparation from PySparQ
from pyqres.algorithms.qda_solver import BlockEncoding, StatePreparation
from pysparq.algorithms.qda_solver import BlockEncodingHs, BlockEncodingHsPD, WalkS, LCU, Filtering

# Import PySparQ solver functions (they use pysparq.algorithms internally).
# Some packaged PySparQ builds do not expose cks_solve_v2; the only tests that
# use it are skipped below, so keep collection robust across those builds.
try:
    from pysparq.algorithms.cks_solver import (
        cks_solve_v2,
        ChebyshevPolynomialCoefficient as PS_Chebyshev,
    )
except ImportError:
    cks_solve_v2 = None
    PS_Chebyshev = None
from pysparq.algorithms.qda_solver import (
    compute_fs as ps_compute_fs,
    compute_rotation_matrix as ps_compute_rotation_matrix,
)

# Import pyqres qda_solve (fixed to add registers before BlockEncoding)
from pyqres.algorithms.qda_solver import qda_solve


def declare_regs(**regs):
    for name, size in regs.items():
        RegisterMetadata.get_register_metadata().declare_register(name, size)


def declare_regs_typed(*entries):
    for name, size, rtype in entries:
        RegisterMetadata.get_register_metadata().declare_register(name, size, rtype)


def read_reg(state, reg_name):
    reg_id = pysparq.System.get_id(reg_name)
    return state.basis_states[0].registers[reg_id].value


def state_size(state):
    return state.size()


@pytest.fixture(autouse=True)
def clean_pysparq():
    while len(RegisterMetadata.register_metadata_stack) > 1:
        RegisterMetadata.pop_register_metadata()
    RegisterMetadata.register_metadata_stack.clear()
    RegisterMetadata.push_register_metadata()
    pysparq.System.clear()
    yield
    while len(RegisterMetadata.register_metadata_stack) > 0:
        RegisterMetadata.pop_register_metadata()
    RegisterMetadata.push_register_metadata()
    pysparq.System.clear()


# ── CKS Helper Tests ──


class TestCKSHelpers:
    def test_sparse_matrix_from_dense(self):
        A = np.array([[2, 1], [1, 2]], dtype=float)
        mat = PyqresSparseMatrix.from_dense(A, data_size=8)
        assert mat.n_row == 2
        assert mat.nnz_col == 2
        assert mat.data_size == 8
        assert mat.positive_only == True  # Use == for numpy bool comparison

    def test_sparse_matrix_signed(self):
        A = np.array([[1, -1], [-1, 1]], dtype=float)
        mat = PyqresSparseMatrix.from_dense(A, data_size=8)
        assert mat.positive_only == False  # Use == for numpy bool comparison

    def test_chebyshev_coefficients_small_b(self):
        cheb = ChebyshevPolynomialCoefficient(b=10)
        for j in range(cheb.b):
            coef = cheb.coef(j)
            assert coef >= 0
            assert cheb.step(j) == 2 * j + 1
            assert cheb.sign(j) == ((j & 1) == 1)

    def test_chebyshev_coefficients_large_b(self):
        cheb = ChebyshevPolynomialCoefficient(b=200)
        for j in range(min(10, cheb.b)):
            coef = cheb.coef(j)
            assert coef >= 0

    def test_chebyshev_step_sizes(self):
        cheb = ChebyshevPolynomialCoefficient(b=10)
        steps = [cheb.step(j) for j in range(5)]
        assert steps == [1, 3, 5, 7, 9]

    def test_walk_angle_positive_only(self):
        R = get_coef_positive_only(8, 128, 0, 0)
        assert len(R) == 4
        assert abs(R[0]) > 0

    def test_walk_angle_common_signed(self):
        R = get_coef_common(8, 128, 0, 1)
        assert len(R) == 4

    def test_make_walk_angle_func(self):
        f = make_walk_angle_func(8, True)
        R = f(128, 0, 0)
        assert len(R) == 4


class TestCKSSolve:
    """Tests for PySparQ CKS solve function.

    These test pysparq's own cks_solve_v2 implementation (not pyqres code).
    Skipped because pysparq has a C++ upstream regression on these inputs.
    """

    @pytest.mark.skip(reason="pysparq C++ upstream regression: QRAMCircuit_qutrit ValueError on sparse data")
    @pytest.mark.filterwarnings("ignore::RuntimeWarning")
    def test_cks_solve_3x3(self):
        """Test CKS solve with 3x3 system."""
        A = np.array([[4, 1, 0], [1, 4, 1], [0, 1, 4]], dtype=float)
        b = np.array([1, 2, 1], dtype=float)
        x = cks_solve_v2(A, b, eps=0.1)
        np.testing.assert_allclose(A @ x, b, atol=1e-6)

    @pytest.mark.skip(reason="pysparq C++ upstream regression: RuntimeError in RemoveRegister during simulation")
    @pytest.mark.filterwarnings("ignore::RuntimeWarning")
    def test_cks_solve_simple(self):
        """Test CKS solve with simple 2x2 system."""
        A = np.array([[2, 1], [1, 2]], dtype=float)
        b = np.array([1, 1], dtype=float)
        x = cks_solve_v2(A, b, eps=0.1)
        assert x is not None
        np.testing.assert_allclose(A @ x, b, atol=1e-6)


# ── QDA Helper Tests ──


class TestQDAHelpers:
    def test_compute_fs_endpoints(self):
        assert compute_fs(0.0, 10.0, 0.5) == pytest.approx(0.0, abs=1e-10)
        assert compute_fs(1.0, 10.0, 0.5) == pytest.approx(1.0, abs=1e-6)

    def test_compute_fs_monotone(self):
        vals = [compute_fs(s, 10.0, 0.5) for s in np.linspace(0, 1, 20)]
        for i in range(1, len(vals)):
            assert vals[i] >= vals[i - 1]

    def test_rotation_matrix_unitary(self):
        R = compute_rotation_matrix(0.3)
        R_mat = np.array([[R[0].real, R[1].real], [R[2].real, R[3].real]])
        product = R_mat @ R_mat.T
        np.testing.assert_allclose(product, np.eye(2), atol=1e-10)

    def test_chebyshev_T(self):
        assert chebyshev_T(0, 0.5) == 1.0
        assert chebyshev_T(1, 0.5) == 0.5
        assert chebyshev_T(2, 0.5) == pytest.approx(-0.5)

    def test_dolph_chebyshev(self):
        val = dolph_chebyshev(0.1, 5, np.pi / 4)
        assert isinstance(val, float)
        assert not np.isnan(val)

    def test_fourier_coeffs(self):
        coeffs = compute_fourier_coeffs(0.1, 5)
        assert len(coeffs) > 0
        assert all(isinstance(c, float) for c in coeffs)

    def test_calculate_angles(self):
        coeffs = [0.5, 0.3, 0.2]
        angles = calculate_angles(coeffs)
        assert len(angles) == 3
        for a in angles:
            assert 0 <= a <= 2 * np.pi

    def test_classical_to_quantum_hermitian(self):
        A = np.array([[2, 1], [1, 2]], dtype=float)
        b = np.array([1, 0], dtype=float)
        A_q, b_q, recover = classical_to_quantum(A, b)
        assert A_q.shape[0] == 2
        assert np.allclose(A_q, A_q.T.conj())

    def test_classical_to_quantum_non_hermitian(self):
        A = np.array([[1, 2], [3, 4]], dtype=float)
        b = np.array([1, 0], dtype=float)
        A_q, b_q, recover = classical_to_quantum(A, b)
        assert A_q.shape[0] == 4
        assert np.allclose(A_q, A_q.T.conj())


class TestQDABlockEncoding:
    def test_block_encoding_creation(self):
        A = np.array([[2, 1], [1, 2]], dtype=float)
        b = np.array([1, 0], dtype=float)
        enc_A = BlockEncoding(A)
        enc_b = StatePreparation(b)
        # BlockEncoding factory returns either Tridiagonal or QRAM encoding
        # Both have a matrix/n_row attribute
        assert enc_A is not None
        assert len(enc_b.b) == 2

    def test_rotation_matrix_properties(self):
        for fs in [0.1, 0.3, 0.5, 0.7, 0.9]:
            R = compute_rotation_matrix(fs)
            assert len(R) == 4
            assert all(isinstance(r, complex) for r in R)

    def test_walk_s_fs_range(self):
        A = np.array([[2, 1], [1, 2]], dtype=float)
        b = np.array([1, 0], dtype=float)
        enc_A = BlockEncoding(A)
        enc_b = StatePreparation(b)
        for s in [0.0, 0.25, 0.5, 0.75, 1.0]:
            walk = WalkS(enc_A, enc_b, "main", "anc_UA",
                         "anc_1", "anc_2", "anc_3", "anc_4",
                         s=s, kappa=2.0, p=0.5)
            assert 0 <= walk.fs <= 1


class TestQDASolve:
    def test_qda_solve_simple(self):
        A = np.array([[2, 1], [1, 2]], dtype=float)
        b = np.array([1, 1], dtype=float)
        x = qda_solve(A, b, kappa=2.0)
        np.testing.assert_allclose(A @ x, b, atol=1e-6)

    def test_qda_solve_with_kappa(self):
        A = np.array([[4, 1, 0], [1, 4, 1], [0, 1, 4]], dtype=float)
        b = np.array([1, 2, 1], dtype=float)
        kappa = np.linalg.cond(A)
        x = qda_solve(A, b, kappa=kappa, eps=0.1)
        np.testing.assert_allclose(A @ x, b, atol=1e-6)


# ── Tridiagonal Block Encoding (QDA Tridiagonal variant for pyqres) ──


class BlockEncodingTridiagonalPyqres(Composite):
    """pyqres version of tridiagonal block encoding for resource estimation."""

    def __init__(self, reg_list, param_list, temp_reg_list=[("overflow", 0), ("other", 0)]):
        super().__init__(reg_list=reg_list, param_list=param_list, temp_reg_list=temp_reg_list)
        self.main_reg = reg_list[0]
        self.anc_UA = reg_list[1]
        self.alpha = param_list[0]
        self.beta = param_list[1]

        import sympy as sp
        self.n = 2 ** reg_sz(self.main_reg)
        s = self.n * self.alpha ** 2 + 2 * (self.n - 1) * self.beta ** 2
        norm_F = sp.sqrt(s)
        self.prep_state = [sp.sqrt(self.alpha / norm_F),
                           sp.sqrt(self.beta / norm_F),
                           sp.sqrt(self.beta / norm_F),
                           sp.sqrt(1 - (self.alpha + 2 * self.beta) / norm_F)]

        self.program_list = [
            SplitRegister([self.anc_UA, "overflow", "other"], [1, 1]),
            Rot_GeneralStatePrep([self.anc_UA], self.prep_state),
            X(["other"], [0]).control_by_all_ones([self.anc_UA]),
            Rot_GeneralStatePrep([self.anc_UA], self.prep_state).dagger(),
            SplitRegister([self.anc_UA, "overflow", "other"], [1, 1]).dagger(),
        ]
        self.declare_program_list()


class TestQDATridiagonal:
    def test_block_encoding_tridiagonal_simulation(self):
        declare_regs(main_reg=2, anc_UA=4)
        sim = SimulatorVisitor()
        BlockEncodingTridiagonalPyqres(["main_reg", "anc_UA"], [0.5, 0.25]).traverse(sim)
        assert state_size(sim.state) >= 1

    def test_block_encoding_dagger_roundtrip(self):
        declare_regs(main_reg=2, anc_UA=4)
        sim = SimulatorVisitor()
        Init_Unsafe(['main_reg'], [1]).traverse(sim)
        be = BlockEncodingTridiagonalPyqres(["main_reg", "anc_UA"], [0.5, 0.25])
        be.traverse(sim)
        be_dag = BlockEncodingTridiagonalPyqres(["main_reg", "anc_UA"], [0.5, 0.25])
        be_dag.dagger()
        be_dag.traverse(sim)
        assert state_size(sim.state) >= 1


# ── Other Tests ──


class TestGroverComponents:
    def test_diffusion_operator_simulation(self):
        declare_regs(q=2, anc=1)
        sim = SimulatorVisitor()
        Hadamard(['q']).traverse(sim)
        Hadamard(['q']).traverse(sim)
        X(['q'], [0]).traverse(sim)
        X(['q'], [1]).traverse(sim)
        CNOT(['q', 'anc'], [1, 0]).traverse(sim)
        X(['q'], [0]).traverse(sim)
        X(['q'], [1]).traverse(sim)
        Hadamard(['q']).traverse(sim)
        assert state_size(sim.state) >= 1

    def test_swap_via_composite(self):
        declare_regs(a=2, b_reg=2)
        sim = SimulatorVisitor()
        Hadamard(['a']).traverse(sim)
        Swap(['a', 'b_reg']).traverse(sim)
        assert state_size(sim.state) > 0


class TestLoweringEngine:
    def test_simulation_estimator(self):
        declare_regs(q=2)
        engine = LoweringEngine()
        result = engine.estimate(Hadamard(['q']), SimulationEstimator())
        assert result.size() == 4


# ── YAML-Generated Solver Tests ──


class TestQDAGenerated:
    """YAML-generated QDALinearSolver replacing the Python-native version."""

    def test_walks_in_program_list(self):
        """QDALinearSolver.program_list should contain WalkS_Primitive instances (> 2 ops)."""
        declare_regs(main_reg=2, anc_UA=4, anc_1=1, anc_2=1, anc_3=1, anc_4=1)
        solver = QDALinearSolver(
            reg_list=["main_reg", "anc_UA", "anc_1", "anc_2", "anc_3", "anc_4"],
            param_list=[2.0, 0.1],
            operations=[None, None])
        assert len(solver.program_list) > 2

    def test_simulation_runs(self):
        """QDALinearSolver can be traversed by SimulatorVisitor without error."""
        declare_regs(main_reg=2, anc_UA=4, anc_1=1, anc_2=1, anc_3=1, anc_4=1)
        solver = QDALinearSolver(
            reg_list=["main_reg", "anc_UA", "anc_1", "anc_2", "anc_3", "anc_4"],
            param_list=[2.0, 0.1],
            operations=[None, None])
        sim = SimulatorVisitor()
        solver.traverse(sim)
        assert sim.state.size() >= 1


class TestCKSGenerated:
    """YAML-generated CKSLinearSolver replacing the Python-native version."""

    def test_chebyshev_loop_in_program_list(self):
        """CKSLinearSolver.program_list should contain operations from Chebyshev loop (> 0)."""
        declare_regs(main_reg=2, anc_reg=4)
        solver = CKSLinearSolver(
            reg_list=["main_reg", "anc_reg"],
            param_list=[2.0, 0.1],
            operations=[None, None])
        assert len(solver.program_list) > 0

    def test_simulation_runs(self):
        """CKSLinearSolver can be traversed by SimulatorVisitor without error."""
        declare_regs(main_reg=2, anc_reg=4)
        solver = CKSLinearSolver(
            reg_list=["main_reg", "anc_reg"],
            param_list=[2.0, 0.1],
            operations=[None, None])
        sim = SimulatorVisitor()
        solver.traverse(sim)
        assert sim.state.size() >= 1
