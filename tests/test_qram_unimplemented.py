"""Tests that QRAM/QRAMFast fail closed with NotImplementedError.

These tests codify the contract: QRAM primitives must NOT silently provide
dummy or approximate behavior.  They must raise NotImplementedError until
a written QRAM contract exists.

If you are implementing QRAM, update these tests to match the new contract.
"""

from __future__ import annotations

import pytest

from pyqres.core.metadata import RegisterMetadata


@pytest.fixture(autouse=True)
def fresh_metadata():
    while len(RegisterMetadata.register_metadata_stack):
        RegisterMetadata.pop_register_metadata()
    RegisterMetadata.push_register_metadata()
    yield
    while len(RegisterMetadata.register_metadata_stack):
        RegisterMetadata.pop_register_metadata()
    RegisterMetadata.push_register_metadata()


def _declare_reg(name, size, reg_type="General"):
    RegisterMetadata.get_register_metadata().declare_register(name, size, reg_type)


class TestQRAMFailClosed:
    """QRAM must raise NotImplementedError on all operational methods."""

    def test_qram_pysparse_object_raises(self):
        from pyqres.primitives.qram import QRAM

        _declare_reg("addr", 2, "UnsignedInteger")
        _declare_reg("data", 3, "UnsignedInteger")
        op = QRAM(reg_list=["addr", "data"], param_list=[0])

        with pytest.raises(NotImplementedError, match="QRAM.*disabled"):
            op.pyqsparse_object()

    def test_qram_t_count_raises(self):
        from pyqres.primitives.qram import QRAM

        _declare_reg("addr", 2, "UnsignedInteger")
        _declare_reg("data", 3, "UnsignedInteger")
        op = QRAM(reg_list=["addr", "data"], param_list=[0])

        with pytest.raises(NotImplementedError, match="QRAM.*disabled"):
            op.t_count()


class TestQRAMFastFailClosed:
    """QRAMFast must raise NotImplementedError on all operational methods."""

    def test_qramfast_pysparse_object_raises(self):
        from pyqres.primitives.qram import QRAMFast

        _declare_reg("addr", 2, "UnsignedInteger")
        _declare_reg("data", 3, "UnsignedInteger")
        op = QRAMFast(reg_list=["addr", "data"], param_list=[None])

        with pytest.raises(NotImplementedError, match="QRAMFast.*disabled"):
            op.pyqsparse_object()

    def test_qramfast_t_count_raises(self):
        from pyqres.primitives.qram import QRAMFast

        _declare_reg("addr", 2, "UnsignedInteger")
        _declare_reg("data", 3, "UnsignedInteger")
        op = QRAMFast(reg_list=["addr", "data"], param_list=[None])

        with pytest.raises(NotImplementedError, match="QRAMFast.*disabled"):
            op.t_count()
