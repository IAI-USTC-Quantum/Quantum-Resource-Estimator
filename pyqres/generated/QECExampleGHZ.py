# Generated from YAML definition

from ..core.operation import StandardComposite
from ..core.registry import OperationRegistry
from ..core.utils import merge_controllers
import math

class QECExampleGHZ(StandardComposite):
    """GHZ state preparation"""
    def __init__(self, reg_list, param_list=None, operations=None):
        if param_list is None:
            param_list = []
        StandardComposite.__init__(self, reg_list=reg_list, param_list=param_list, operations=operations)
        self.q = reg_list[0]
        self.n = param_list[0]
        # Complex implementation with loops/conditionals
        self._impl_structure = [{"_type": "op", "op": "H", "qregs": ["q"], "params": [0]}, {"_type": "for_each", "var": "i", "items": {"type": "expr", "value": "range(n - 1)"}, "body": [{"_type": "op", "op": "CNOT", "qregs": ["q", "q"], "params": [{"type": "expr", "value": "i"}, {"type": "expr", "value": "i + 1"}]}]}]
        self._build_execute_method()

    def _build_execute_method(self):
        # Build program_list by expanding loops and conditionals
        self.program_list = []
        self.program_list.append(OperationRegistry.get_class("H")(reg_list=[self.q], param_list=[0]))
        for i in range(self.n - 1):
                self.program_list.append(OperationRegistry.get_class("CNOT")(reg_list=[self.q, self.q], param_list=[i, i + 1]))
        self.declare_program_list()