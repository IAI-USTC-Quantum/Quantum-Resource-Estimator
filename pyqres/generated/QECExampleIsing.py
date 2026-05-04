# Generated from YAML definition

from ..core.operation import StandardComposite
from ..core.registry import OperationRegistry
from ..core.utils import merge_controllers
import math

class QECExampleIsing(StandardComposite):
    """Trotterized transverse-field Ising benchmark algorithm"""
    def __init__(self, reg_list, param_list=None, operations=None):
        if param_list is None:
            param_list = []
        StandardComposite.__init__(self, reg_list=reg_list, param_list=param_list, operations=operations)
        self.q = reg_list[0]
        self.n_spins = param_list[0]
        self.couplings = param_list[1]
        self.p_level = param_list[2]
        self.h_transverse = param_list[3]
        self.dt = 0.1
        # Complex implementation with loops/conditionals
        self._impl_structure = [{"_type": "loop", "iterations": "p_level", "body": [{"_type": "for_each", "var": "item", "items": {"type": "expr", "value": "enumerate(couplings)"}, "body": [{"_type": "op", "op": "CNOT", "qregs": ["q", "q"], "params": [{"type": "expr", "value": "item[0]"}, {"type": "expr", "value": "item[0] + 1"}]}, {"_type": "op", "op": "RZ", "qregs": ["q"], "params": [{"type": "expr", "value": "item[0] + 1"}, {"type": "expr", "value": "-float(item[1]) * dt"}]}, {"_type": "op", "op": "CNOT", "qregs": ["q", "q"], "params": [{"type": "expr", "value": "item[0]"}, {"type": "expr", "value": "item[0] + 1"}]}]}, {"_type": "for_each", "var": "i", "items": "n_spins", "body": [{"_type": "op", "op": "RX", "qregs": ["q"], "params": [{"type": "expr", "value": "i"}, {"type": "expr", "value": "-h_transverse * dt"}]}]}]}]
        self._build_execute_method()

    def _build_execute_method(self):
        # Build program_list by expanding loops and conditionals
        self.program_list = []
        for i in range(self.p_level):
                for item in enumerate(self.couplings):
                        self.program_list.append(OperationRegistry.get_class("CNOT")(reg_list=[self.q, self.q], param_list=[item[0], item[0] + 1]))
                        self.program_list.append(OperationRegistry.get_class("RZ")(reg_list=[self.q], param_list=[item[0] + 1, -float(item[1]) * self.dt]))
                        self.program_list.append(OperationRegistry.get_class("CNOT")(reg_list=[self.q, self.q], param_list=[item[0], item[0] + 1]))
                for i in range(self.n_spins):
                        self.program_list.append(OperationRegistry.get_class("RX")(reg_list=[self.q], param_list=[i, -self.h_transverse * self.dt]))
        self.declare_program_list()