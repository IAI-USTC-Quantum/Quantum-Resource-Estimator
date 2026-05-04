# Generated from YAML definition

from ..core.operation import StandardComposite
from ..core.registry import OperationRegistry
from ..core.utils import merge_controllers
import math

class QECExampleQPE(StandardComposite):
    """Quantum Phase Estimation benchmark algorithm"""
    def __init__(self, reg_list, param_list=None, operations=None):
        if param_list is None:
            param_list = []
        StandardComposite.__init__(self, reg_list=reg_list, param_list=param_list, operations=operations)
        self.q = reg_list[0]
        self.n_counting = param_list[0]
        self.n_system = param_list[1]
        self.unitary_eigenvalue = param_list[2]
        self.phase = 2 * math.pi * self.unitary_eigenvalue
        # Complex implementation with loops/conditionals
        self._impl_structure = [{"_type": "for_each", "var": "i", "items": "n_counting", "body": [{"_type": "op", "op": "H", "qregs": ["q"], "params": [{"type": "expr", "value": "i"}]}]}, {"_type": "for_each", "var": "i", "items": "n_counting", "body": [{"_type": "for_each", "var": "s", "items": "n_system", "body": [{"_type": "op", "op": "CPHASE", "qregs": ["q"], "params": [{"type": "expr", "value": "i"}, {"type": "expr", "value": "n_counting + s"}, {"type": "expr", "value": "phase * (1 << i)"}]}]}]}, {"_type": "for_each", "var": "i", "items": {"type": "expr", "value": "range(n_counting // 2)"}, "body": [{"_type": "op", "op": "SWAP", "qregs": ["q"], "params": [{"type": "expr", "value": "i"}, {"type": "expr", "value": "n_counting - 1 - i"}]}]}, {"_type": "for_each", "var": "i", "items": {"type": "expr", "value": "range(n_counting - 1, -1, -1)"}, "body": [{"_type": "for_each", "var": "j", "items": {"type": "expr", "value": "range(n_counting - 1, i, -1)"}, "body": [{"_type": "op", "op": "CPHASE", "qregs": ["q"], "params": [{"type": "expr", "value": "i"}, {"type": "expr", "value": "j"}, {"type": "expr", "value": "-math.pi / (1 << (j - i))"}]}]}, {"_type": "op", "op": "H", "qregs": ["q"], "params": [{"type": "expr", "value": "i"}]}]}]
        self._build_execute_method()

    def _build_execute_method(self):
        # Build program_list by expanding loops and conditionals
        self.program_list = []
        for i in range(self.n_counting):
                self.program_list.append(OperationRegistry.get_class("H")(reg_list=[self.q], param_list=[i]))
        for i in range(self.n_counting):
                for s in range(self.n_system):
                        self.program_list.append(OperationRegistry.get_class("CPHASE")(reg_list=[self.q], param_list=[i, self.n_counting + s, self.phase * (1 << i)]))
        for i in range(self.n_counting // 2):
                self.program_list.append(OperationRegistry.get_class("SWAP")(reg_list=[self.q], param_list=[i, self.n_counting - 1 - i]))
        for i in range(self.n_counting - 1, -1, -1):
                for j in range(self.n_counting - 1, i, -1):
                        self.program_list.append(OperationRegistry.get_class("CPHASE")(reg_list=[self.q], param_list=[i, j, -math.pi / (1 << (j - i))]))
                self.program_list.append(OperationRegistry.get_class("H")(reg_list=[self.q], param_list=[i]))
        self.declare_program_list()