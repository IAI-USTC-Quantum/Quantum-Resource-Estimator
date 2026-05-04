# Generated from YAML definition

from ..core.operation import StandardComposite
from ..core.registry import OperationRegistry
from ..core.utils import merge_controllers
import math

class QECExampleDJ(StandardComposite):
    """Deutsch-Jozsa benchmark algorithm"""
    def __init__(self, reg_list, param_list=None, operations=None):
        if param_list is None:
            param_list = []
        StandardComposite.__init__(self, reg_list=reg_list, param_list=param_list, operations=operations)
        self.q = reg_list[0]
        self.n = param_list[0]
        self.balanced = param_list[1]
        # Complex implementation with loops/conditionals
        self._impl_structure = [{"_type": "op", "op": "X", "qregs": ["q"], "params": [{"type": "expr", "value": "n"}]}, {"_type": "op", "op": "H", "qregs": ["q"], "params": [{"type": "expr", "value": "n"}]}, {"_type": "for_each", "var": "i", "items": "n", "body": [{"_type": "op", "op": "H", "qregs": ["q"], "params": [{"type": "expr", "value": "i"}]}]}, {"_type": "if", "condition": "balanced", "body": [{"_type": "for_each", "var": "i", "items": "n", "body": [{"_type": "op", "op": "CNOT", "qregs": ["q", "q"], "params": [{"type": "expr", "value": "i"}, {"type": "expr", "value": "n"}]}]}]}, {"_type": "for_each", "var": "i", "items": "n", "body": [{"_type": "op", "op": "H", "qregs": ["q"], "params": [{"type": "expr", "value": "i"}]}]}]
        self._build_execute_method()

    def _build_execute_method(self):
        # Build program_list by expanding loops and conditionals
        self.program_list = []
        self.program_list.append(OperationRegistry.get_class("X")(reg_list=[self.q], param_list=[self.n]))
        self.program_list.append(OperationRegistry.get_class("H")(reg_list=[self.q], param_list=[self.n]))
        for i in range(self.n):
                self.program_list.append(OperationRegistry.get_class("H")(reg_list=[self.q], param_list=[i]))
        if self.balanced:
                for i in range(self.n):
                        self.program_list.append(OperationRegistry.get_class("CNOT")(reg_list=[self.q, self.q], param_list=[i, self.n]))
        for i in range(self.n):
                self.program_list.append(OperationRegistry.get_class("H")(reg_list=[self.q], param_list=[i]))
        self.declare_program_list()