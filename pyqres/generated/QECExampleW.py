# Generated from YAML definition

from ..core.operation import StandardComposite
from ..core.registry import OperationRegistry
from ..core.utils import merge_controllers
import math

class QECExampleW(StandardComposite):
    """W-state preparation"""
    def __init__(self, reg_list, param_list=None, operations=None):
        if param_list is None:
            param_list = []
        StandardComposite.__init__(self, reg_list=reg_list, param_list=param_list, operations=operations)
        self.q = reg_list[0]
        self.n = param_list[0]
        # Complex implementation with loops/conditionals
        self._impl_structure = [{"_type": "for_each", "var": "i", "items": "n", "body": [{"_type": "if", "condition": "i == n - 1", "body": [{"_type": "op", "op": "X", "qregs": ["q"], "params": [{"type": "expr", "value": "i"}]}], "else": [{"_type": "op", "op": "RY", "qregs": ["q"], "params": [{"type": "expr", "value": "i"}, {"type": "expr", "value": "2 * math.asin(math.sqrt((n - i - 1) / (n - i)))"}]}, {"_type": "op", "op": "CNOT", "qregs": ["q", "q"], "params": [{"type": "expr", "value": "i"}, {"type": "expr", "value": "i + 1"}]}, {"_type": "op", "op": "RY", "qregs": ["q"], "params": [{"type": "expr", "value": "i + 1"}, {"type": "expr", "value": "-2 * math.asin(math.sqrt((n - i - 1) / (n - i)))"}]}, {"_type": "op", "op": "CNOT", "qregs": ["q", "q"], "params": [{"type": "expr", "value": "i"}, {"type": "expr", "value": "i + 1"}]}, {"_type": "op", "op": "X", "qregs": ["q"], "params": [{"type": "expr", "value": "i"}]}]}]}]
        self._build_execute_method()

    def _build_execute_method(self):
        # Build program_list by expanding loops and conditionals
        self.program_list = []
        for i in range(self.n):
                if i == self.n - 1:
                        self.program_list.append(OperationRegistry.get_class("X")(reg_list=[self.q], param_list=[i]))
                else:
                        self.program_list.append(OperationRegistry.get_class("RY")(reg_list=[self.q], param_list=[i, 2 * math.asin(math.sqrt((self.n - i - 1) / (self.n - i)))]))
                        self.program_list.append(OperationRegistry.get_class("CNOT")(reg_list=[self.q, self.q], param_list=[i, i + 1]))
                        self.program_list.append(OperationRegistry.get_class("RY")(reg_list=[self.q], param_list=[i + 1, -2 * math.asin(math.sqrt((self.n - i - 1) / (self.n - i)))]))
                        self.program_list.append(OperationRegistry.get_class("CNOT")(reg_list=[self.q, self.q], param_list=[i, i + 1]))
                        self.program_list.append(OperationRegistry.get_class("X")(reg_list=[self.q], param_list=[i]))
        self.declare_program_list()