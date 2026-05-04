import pysparq

from ..core.operation import Primitive
from ..core.metadata import RegisterMetadata
from ..core.utils import merge_controllers
from ..core.simulator import PyQSparseOperationWrapper


class SplitRegister(Primitive):
    """Split a register into sub-registers, or merge them back on dagger."""

    def __init__(self, reg_list, param_list):
        super().__init__(reg_list=reg_list, param_list=param_list)

    def render_this(self, indent=0, dagger_ctx=False, controllers_ctx=None):
        controllers_ctx = controllers_ctx or {}
        dagger_ctx = self.dagger_flag ^ dagger_ctx
        split_str = ", ".join(
            f"{reg}({size})"
            for reg, size in zip(self.reg_list[1:], self.param_list))
        action = "MergeRegister" if dagger_ctx else "SplitRegister"
        return f"{' ' * indent}{action}: {self.reg_list[0]} {'<-' if dagger_ctx else '->'} {split_str}"

    def enter(self, dagger_ctx=False, controllers_ctx=None):
        register_metadata_ = RegisterMetadata.get_register_metadata()
        dagger_ctx = self.dagger_flag ^ dagger_ctx
        if not dagger_ctx:
            register_metadata_.split_register(
                self.reg_list[0],
                list(zip(self.reg_list[1:], self.param_list)))

    def exit(self, dagger_ctx=False, controllers_ctx=None):
        register_metadata_ = RegisterMetadata.get_register_metadata()
        dagger_ctx = self.dagger_flag ^ dagger_ctx
        if dagger_ctx:
            register_metadata_.merge_register(
                self.reg_list[0], list(self.reg_list[1:]))

    def t_count(self, dagger_ctx=False, controllers_ctx=None):
        return 0

    def pyqsparse_object(self, dagger_ctx=False, controllers_ctx=None):
        controllers_ctx = merge_controllers(self.controllers, controllers_ctx or {})
        dagger_ctx = self.dagger_flag ^ dagger_ctx
        if not dagger_ctx:
            return [
                PyQSparseOperationWrapper(
                    pysparq.SplitRegister(self.reg_list[0], reg, size))
                for reg, size in zip(self.reg_list[1:], self.param_list)]
        else:
            return [
                PyQSparseOperationWrapper(
                    pysparq.CombineRegister(self.reg_list[0], reg))
                for reg in self.reg_list[1:]]


class CombineRegister(Primitive):
    def __init__(self, reg_list, param_list=None):
        super().__init__(reg_list, param_list)
        self.first = reg_list[0]
        self.second = reg_list[1]

    def enter(self, dagger_ctx=False, controllers_ctx=None):
        # Mirror SplitRegister.enter(): restore metadata when combining forward.
        register_metadata_ = RegisterMetadata.get_register_metadata()
        dagger_ctx = self.dagger_flag ^ dagger_ctx
        if not dagger_ctx:
            register_metadata_.merge_register(self.first, [self.second])

    def pyqsparse_object(self, dagger_ctx=False, controllers_ctx=None):
        controllers_ctx = merge_controllers(self.controllers, controllers_ctx or {})
        obj = PyQSparseOperationWrapper(
            pysparq.CombineRegister(self.first, self.second))
        obj.set_dagger(dagger_ctx ^ self.dagger_flag)
        obj.set_controller(controllers_ctx)
        return obj

    def t_count(self, dagger_ctx=False, controllers_ctx=None):
        return 0


class Push(Primitive):
    def __init__(self, reg_list, param_list):
        super().__init__(reg_list=reg_list, param_list=param_list)
        self.reg = reg_list[0]
        self.garbage = param_list[0]

    def pyqsparse_object(self, dagger_ctx=False, controllers_ctx=None):
        controllers_ctx = merge_controllers(self.controllers, controllers_ctx or {})
        obj = PyQSparseOperationWrapper(pysparq.Push(self.reg, self.garbage))
        obj.set_dagger(dagger_ctx ^ self.dagger_flag)
        obj.set_controller(controllers_ctx)
        return obj

    def t_count(self, dagger_ctx=False, controllers_ctx=None):
        return 0


class Pop(Primitive):
    def __init__(self, reg_list, param_list=None):
        super().__init__(reg_list, param_list)
        self.reg = reg_list[0]

    def pyqsparse_object(self, dagger_ctx=False, controllers_ctx=None):
        controllers_ctx = merge_controllers(self.controllers, controllers_ctx or {})
        obj = PyQSparseOperationWrapper(pysparq.Pop(self.reg))
        obj.set_dagger(dagger_ctx ^ self.dagger_flag)
        obj.set_controller(controllers_ctx)
        return obj

    def t_count(self, dagger_ctx=False, controllers_ctx=None):
        return 0


# ==============================================================================
# New register management primitives (Phase 2)
# ==============================================================================


class AddRegister(Primitive):
    """Add a new quantum register to the system.

    Registers must be declared before they can be used in other operations.
    Note: this is a system management operation, not a quantum gate.
    T-count = 0.
    """
    __self_conjugate__ = True

    def __init__(self, reg_list, param_list):
        super().__init__(reg_list=reg_list, param_list=param_list)
        self.name = param_list[0]
        self.reg_type = param_list[1]  # pysparq.StateStorageType
        self.size = param_list[2]

    def pyqsparse_object(self, dagger_ctx=False, controllers_ctx=None):
        return pysparq.AddRegister(self.name, self.reg_type, self.size)

    def t_count(self, dagger_ctx=False, controllers_ctx=None):
        return 0


class AddRegisterWithHadamard(Primitive):
    """Add a new quantum register initialized with Hadamard superposition.

    Equivalent to AddRegister + Hadamard on all qubits.
    T-count = 0.
    """
    __self_conjugate__ = True

    def __init__(self, reg_list, param_list):
        super().__init__(reg_list=reg_list, param_list=param_list)
        self.name = param_list[0]
        self.reg_type = param_list[1]
        self.size = param_list[2]

    def pyqsparse_object(self, dagger_ctx=False, controllers_ctx=None):
        return pysparq.AddRegisterWithHadamard(self.name, self.reg_type, self.size)

    def t_count(self, dagger_ctx=False, controllers_ctx=None):
        return 0


class RemoveRegister(Primitive):
    """Remove a quantum register from the system.

    Note: this is a system management operation.
    T-count = 0.
    """
    __self_conjugate__ = True

    def __init__(self, reg_list, param_list):
        super().__init__(reg_list=reg_list, param_list=param_list)
        self.name = param_list[0]

    def pyqsparse_object(self, dagger_ctx=False, controllers_ctx=None):
        return pysparq.RemoveRegister(self.name)

    def t_count(self, dagger_ctx=False, controllers_ctx=None):
        return 0


class MoveBackRegister(Primitive):
    """Move a register back to its original position in the system.

    Used to restore register order after temporary operations.
    T-count = 0.
    """
    __self_conjugate__ = True

    def __init__(self, reg_list, param_list=None):
        super().__init__(reg_list, param_list)
        self.reg = reg_list[0]

    def pyqsparse_object(self, dagger_ctx=False, controllers_ctx=None):
        return pysparq.MoveBackRegister(self.reg)

    def t_count(self, dagger_ctx=False, controllers_ctx=None):
        return 0
