"""QRAM primitives.

QRAM support is intentionally disabled in the current pyqres -> QEC-Compiler
workflow. Direct PySparQ QRAM experiments can still be run outside pyqres, but
the pyqres wrappers must not provide dummy memories or approximate references
until a shared QRAM contract is defined.
"""

from ..core.operation import Primitive


_QRAM_DISABLED_MESSAGE = (
    "pyqres QRAM primitives are intentionally disabled for the current "
    "pyqres -> QEC-Compiler workflow. Use direct PySparQ QRAM experiments "
    "outside pyqres, or wait for the future QRAM contract/reference fix."
)


class QRAM(Primitive):
    def __init__(self, reg_list, param_list):
        super().__init__(reg_list=reg_list, param_list=param_list)
        self.reg_addr = reg_list[0]
        self.reg_data = reg_list[1]
        self.data_id = param_list[0] if param_list else None

    def pyqsparse_object(self, dagger_ctx=False, controllers_ctx=None):
        raise NotImplementedError(_QRAM_DISABLED_MESSAGE)

    def t_count(self, dagger_ctx=False, controllers_ctx=None):
        raise NotImplementedError(_QRAM_DISABLED_MESSAGE)


class QRAMFast(Primitive):
    """Fast QRAM loading placeholder.

    Kept as a registered primitive so existing YAML/Python definitions fail
    explicitly instead of breaking imports.
    """

    __self_conjugate__ = True

    def __init__(self, reg_list, param_list):
        super().__init__(reg_list=reg_list, param_list=param_list)
        self.qram = param_list[0] if param_list else None
        self.addr_reg = reg_list[0]
        self.data_reg = reg_list[1]

    def pyqsparse_object(self, dagger_ctx=False, controllers_ctx=None):
        raise NotImplementedError(_QRAM_DISABLED_MESSAGE)

    def t_count(self, dagger_ctx=False, controllers_ctx=None):
        raise NotImplementedError(_QRAM_DISABLED_MESSAGE)
