# Generated from YAML definition

from ..core.operation import StandardComposite
from ..core.registry import OperationRegistry
from ..core.utils import merge_controllers
import math

class QECExampleQFT(StandardComposite):
    """Quantum Fourier Transform benchmark algorithm"""
    def __init__(self, reg_list, param_list=None, operations=None):
        if param_list is None:
            param_list = []
        StandardComposite.__init__(self, reg_list=reg_list, param_list=param_list, operations=operations)
        self.q = reg_list[0]
        self.n = param_list[0]
        # Complex implementation with loops/conditionals
        self._impl_structure = [{"_type": "for_each", "var": "i", "items": "n", "body": [{"_type": "op", "op": "H", "qregs": ["q"], "params": [{"type": "expr", "value": "i"}]}, {"_type": "for_each", "var": "j", "items": {"type": "expr", "value": "range(i + 1, n)"}, "body": [{"_type": "op", "op": "CPHASE", "qregs": ["q"], "params": [{"type": "expr", "value": "i"}, {"type": "expr", "value": "j"}, {"type": "expr", "value": "math.pi / (1 << (j - i))"}]}]}]}, {"_type": "for_each", "var": "i", "items": {"type": "expr", "value": "range(n // 2)"}, "body": [{"_type": "op", "op": "SWAP", "qregs": ["q"], "params": [{"type": "expr", "value": "i"}, {"type": "expr", "value": "n - 1 - i"}]}]}]
        self._build_execute_method()

    def _build_execute_method(self):
        # Build program_list by expanding loops and conditionals
        self.program_list = []
        for i in range(self.n):
                self.program_list.append(OperationRegistry.get_class("H")(reg_list=[self.q], param_list=[i]))
                for j in range(i + 1, self.n):
                        self.program_list.append(OperationRegistry.get_class("CPHASE")(reg_list=[self.q], param_list=[i, j, math.pi / (1 << (j - i))]))
        for i in range(self.n // 2):
                self.program_list.append(OperationRegistry.get_class("SWAP")(reg_list=[self.q], param_list=[i, self.n - 1 - i]))
        self.declare_program_list()