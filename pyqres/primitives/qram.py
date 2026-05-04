"""QRAM primitives — currently disabled (fail-closed).

QRAM and QRAMFast are intentionally non-functional until a written QRAM
contract exists.  Both ``pyqsparse_object()`` and ``t_count()`` raise
``NotImplementedError``.

See ``docs/qram_contract.md`` for the contract questions that must be
answered before implementation work begins.
"""

from ..core.operation import Primitive


class QRAM(Primitive):
    """Quantum random-access memory load primitive (DISABLED).

    Once implemented, will load data from a QRAM circuit at the address
    in addr_reg into data_reg.  Currently raises NotImplementedError on
    all operational methods.
    """

    def __init__(self, reg_list, param_list):
        super().__init__(reg_list=reg_list, param_list=param_list)

    def pyqsparse_object(self, dagger_ctx=False, controllers_ctx=None):
        raise NotImplementedError(
            "QRAM.pyqsparse_object() is disabled until the QRAM contract "
            "is defined. See docs/qram_contract.md."
        )

    def t_count(self, dagger_ctx=False, controllers_ctx=None):
        raise NotImplementedError(
            "QRAM.t_count() is disabled until the QRAM contract "
            "is defined. See docs/qram_contract.md."
        )


class QRAMFast(Primitive):
    """Fast QRAM loading using the bucket-brigade protocol (DISABLED).

    Once implemented, will load data from a QRAM circuit at high speed.
    Currently raises NotImplementedError on all operational methods.
    """

    __self_conjugate__ = True

    def __init__(self, reg_list, param_list):
        super().__init__(reg_list=reg_list, param_list=param_list)

    def pyqsparse_object(self, dagger_ctx=False, controllers_ctx=None):
        raise NotImplementedError(
            "QRAMFast.pyqsparse_object() is disabled until the QRAM contract "
            "is defined. See docs/qram_contract.md."
        )

    def t_count(self, dagger_ctx=False, controllers_ctx=None):
        raise NotImplementedError(
            "QRAMFast.t_count() is disabled until the QRAM contract "
            "is defined. See docs/qram_contract.md."
        )
