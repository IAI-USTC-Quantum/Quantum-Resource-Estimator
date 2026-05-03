"""Contract tests for pyqres intermediate primitive PySparQ references."""

from __future__ import annotations

import pytest

pytest.importorskip("pysparq")

from pyqres.core.metadata import RegisterMetadata


@pytest.fixture(autouse=True)
def fresh_metadata():
    while len(RegisterMetadata.register_metadata_stack) > 1:
        RegisterMetadata.pop_register_metadata()
    RegisterMetadata.register_metadata_stack.clear()
    RegisterMetadata.push_register_metadata()
    yield
    while len(RegisterMetadata.register_metadata_stack) > 0:
        RegisterMetadata.pop_register_metadata()
    RegisterMetadata.push_register_metadata()


def _declare_reg(name, size, reg_type="UnsignedInteger"):
    RegisterMetadata.get_register_metadata().declare_register(name, size, reg_type)


def test_mod_add_pysparq_reference_fails_closed():
    """MOD_ADD must not use plain Add_UInt_UInt_InPlace as a false reference."""
    from pyqres.primitives import MOD_ADD

    _declare_reg("a", 2)
    _declare_reg("b", 2)
    op = MOD_ADD(reg_list=["a", "b"], param_list=[3])

    with pytest.raises(NotImplementedError, match="MOD_ADD"):
        op.pyqsparse_object()


def test_mod_mul_pysparq_reference_exists_for_forward_and_dagger():
    """MOD_MUL uses PySparQ modular multiplication and inverse multiplier for dagger."""
    from pyqres.primitives import MOD_MUL

    _declare_reg("x", 4)
    op = MOD_MUL(reg_list=["x"], param_list=[2, 15])

    assert op.pyqsparse_object() is not None
    assert op.pyqsparse_object(dagger_ctx=True) is not None


def test_mod_mul_pysparq_reference_rejects_non_coprime_multiplier():
    from pyqres.primitives import MOD_MUL

    _declare_reg("x", 4)
    op = MOD_MUL(reg_list=["x"], param_list=[3, 15])

    with pytest.raises(ValueError, match="coprime"):
        op.pyqsparse_object()
