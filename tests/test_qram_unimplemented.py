"""QRAM is explicitly disabled in the current pyqres/QEC workflow."""

from __future__ import annotations

import pytest

from pyqres.core.metadata import RegisterMetadata


def _declare_qram_regs() -> None:
    rm = RegisterMetadata.get_register_metadata()
    rm.declare_register("addr", 2, "UnsignedInteger")
    rm.declare_register("data", 3, "UnsignedInteger")


@pytest.mark.xfail(raises=NotImplementedError, strict=True, reason="QRAM contract deferred")
def test_qram_reference_is_deferred_xfail():
    from pyqres.primitives import QRAM

    _declare_qram_regs()
    QRAM(["addr", "data"], [0]).pyqsparse_object()


@pytest.mark.xfail(raises=NotImplementedError, strict=True, reason="QRAM contract deferred")
def test_qramfast_reference_is_deferred_xfail():
    from pyqres.primitives import QRAMFast

    _declare_qram_regs()
    QRAMFast(["addr", "data"], [None]).pyqsparse_object()
