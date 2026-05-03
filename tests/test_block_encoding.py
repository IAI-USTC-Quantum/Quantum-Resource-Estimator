"""Tests for block encoding algorithms (pyqres.algorithms.block_encoding)."""

import pytest
import numpy as np
from pyqres.algorithms.block_encoding import (
    get_tridiagonal_matrix, get_u_plus, get_u_minus,
    BlockEncodingTridiagonal, UR, UL,
    BlockEncodingViaQRAM, PlusOneOverflow,
)
from pyqres.core.operation import StandardComposite, Primitive


class TestUtilityFunctions:
    def test_get_tridiagonal_matrix(self):
        A = get_tridiagonal_matrix(alpha=1.0, beta=0.5, dim=4)
        assert A.shape == (4, 4)
        assert A[0, 0] == 1.0
        assert A[0, 1] == 0.5
        assert A[1, 0] == 0.5
        assert A[3, 3] == 1.0
        assert A[3, 2] == 0.5
        # Off-diagonal corners should be zero
        assert A[0, 3] == 0.0

    def test_get_tridiagonal_matrix_1x1(self):
        A = get_tridiagonal_matrix(alpha=2.0, beta=0.0, dim=1)
        assert A.shape == (1, 1)
        assert A[0, 0] == 2.0

    def test_get_u_plus(self):
        U = get_u_plus(4)
        assert U.shape == (4, 4)
        assert U[1, 0] == 1
        assert U[2, 1] == 1
        assert U[3, 2] == 1
        assert U[0, 0] == 0

    def test_get_u_minus(self):
        U = get_u_minus(4)
        assert U.shape == (4, 4)
        assert U[0, 1] == 1
        assert U[1, 2] == 1
        assert U[2, 3] == 1
        assert U[3, 3] == 0


class TestPlusOneOverflow:
    def test_is_primitive(self):
        assert issubclass(PlusOneOverflow, Primitive)

    def test_not_self_conjugate(self):
        # PlusOneOverflow with cond_value=1 is NOT the same as cond_value=2
        assert getattr(PlusOneOverflow, '__self_conjugate__', True) is False

    def test_dagger_marks_inverse_operation(self):
        from pyqres.core.metadata import RegisterMetadata
        RegisterMetadata.get_register_metadata().declare_register('main', 4)
        RegisterMetadata.get_register_metadata().declare_register('overflow', 1)

        forward = PlusOneOverflow(
            reg_list=['main', 'overflow'], param_list=[1])
        backward = forward.dagger()

        assert backward.dagger_flag is True
        assert backward.cond_value == 1
        assert backward.main_reg == 'main'
        assert backward.overflow_reg == 'overflow'

    def test_t_count(self):
        from pyqres.core.metadata import RegisterMetadata
        RegisterMetadata.get_register_metadata().declare_register('main', 4)
        RegisterMetadata.get_register_metadata().declare_register('overflow', 1)

        op = PlusOneOverflow(
            reg_list=['main', 'overflow'], param_list=[1])
        tc = op.t_count()
        # Ripple-carry: 4 * n = 4 * 4 = 16
        assert tc == 16


class TestBlockEncodingTridiagonal:
    def test_is_standard_composite(self):
        assert issubclass(BlockEncodingTridiagonal, StandardComposite)

    def test_builds_program_list(self):
        from pyqres.core.metadata import RegisterMetadata
        RegisterMetadata.get_register_metadata().declare_register('main', 2)
        RegisterMetadata.get_register_metadata().declare_register('anc', 2)

        be = BlockEncodingTridiagonal(
            main_reg='main', anc_UA='anc',
            alpha=1.0, beta=0.5,
        )
        assert len(be.program_list) > 0

    def test_prep_state_length_4(self):
        from pyqres.core.metadata import RegisterMetadata
        RegisterMetadata.get_register_metadata().declare_register('main', 2)
        RegisterMetadata.get_register_metadata().declare_register('anc', 2)

        be = BlockEncodingTridiagonal(
            main_reg='main', anc_UA='anc',
            alpha=1.0, beta=0.5,
        )
        assert len(be.prep_state) == 4
        # State vector should have valid complex numbers
        for v in be.prep_state:
            assert isinstance(v, complex)

    def test_prep_state_normalized(self):
        from pyqres.core.metadata import RegisterMetadata
        RegisterMetadata.get_register_metadata().declare_register('main', 2)
        RegisterMetadata.get_register_metadata().declare_register('anc', 2)

        be = BlockEncodingTridiagonal(
            main_reg='main', anc_UA='anc',
            alpha=1.0, beta=0.5,
        )
        norm_sq = sum(abs(v) ** 2 for v in be.prep_state)
        assert abs(norm_sq - 1.0) < 1e-10


class TestUR:
    def test_is_standard_composite(self):
        assert issubclass(UR, StandardComposite)

    def test_builds_program_list(self):
        from pyqres.core.metadata import RegisterMetadata
        RegisterMetadata.get_register_metadata().declare_register('col', 3)

        ur = UR(
            column_index='col',
            data_size=8,
            rational_size=4,
            qram=None,
        )
        assert len(ur.program_list) > 0
        assert ur.addr_size == 3


class TestUL:
    def test_is_standard_composite(self):
        assert issubclass(UL, StandardComposite)

    def test_builds_program_list(self):
        from pyqres.core.metadata import RegisterMetadata
        RegisterMetadata.get_register_metadata().declare_register('row', 3)

        ul = UL(
            row_index='row',
            column_index='col',
            data_size=8,
            rational_size=4,
            qram=None,
        )
        assert len(ul.program_list) > 0
        assert ul.addr_size == 3
