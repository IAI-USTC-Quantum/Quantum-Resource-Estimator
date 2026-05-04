# Generated from YAML definition

from ..core.operation import StandardComposite
from ..core.registry import OperationRegistry
from ..core.utils import merge_controllers
import math

class QECExampleSmallShor(StandardComposite):
    """Small Shor order-finding fixture for N=15 or N=21"""
    def __init__(self, reg_list, param_list=None, operations=None):
        if param_list is None:
            param_list = []
        StandardComposite.__init__(self, reg_list=reg_list, param_list=param_list, operations=operations)
        self.q = reg_list[0]
        self.modulus = param_list[0]
        self.base = param_list[1]
        self.counting_bits = 4 if self.modulus == 15 else 6
        self.work_bits = 4 if self.modulus == 15 else 5
        # Complex implementation with loops/conditionals
        self._impl_structure = [{"_type": "op", "op": "X", "qregs": ["q"], "params": [{"type": "expr", "value": "counting_bits"}]}, {"_type": "for_each", "var": "control", "items": "counting_bits", "body": [{"_type": "op", "op": "H", "qregs": ["q"], "params": [{"type": "expr", "value": "control"}]}]}, {"_type": "for_each", "var": "control", "items": "counting_bits", "body": [{"_type": "op", "op": "CMUL_MOD_N", "qregs": ["q"], "params": [{"type": "expr", "value": "[control] + list(range(counting_bits, counting_bits + work_bits))"}, {"type": "expr", "value": "float(pow(base, 1 << control, modulus))"}, {"type": "expr", "value": "float(modulus)"}]}]}, {"_type": "for_each", "var": "left", "items": {"type": "expr", "value": "range(counting_bits // 2)"}, "body": [{"_type": "op", "op": "SWAP", "qregs": ["q"], "params": [{"type": "expr", "value": "left"}, {"type": "expr", "value": "counting_bits - 1 - left"}]}]}, {"_type": "for_each", "var": "target", "items": "counting_bits", "body": [{"_type": "for_each", "var": "control", "items": {"type": "expr", "value": "range(target)"}, "body": [{"_type": "op", "op": "CPHASE", "qregs": ["q"], "params": [{"type": "expr", "value": "control"}, {"type": "expr", "value": "target"}, {"type": "expr", "value": "-math.pi / (1 << (target - control))"}]}]}, {"_type": "op", "op": "H", "qregs": ["q"], "params": [{"type": "expr", "value": "target"}]}]}]
        self._build_execute_method()

    def _build_execute_method(self):
        # Build program_list by expanding loops and conditionals
        self.program_list = []
        self.program_list.append(OperationRegistry.get_class("X")(reg_list=[self.q], param_list=[self.counting_bits]))
        for control in range(self.counting_bits):
                self.program_list.append(OperationRegistry.get_class("H")(reg_list=[self.q], param_list=[control]))
        for control in range(self.counting_bits):
                self.program_list.append(OperationRegistry.get_class("CMUL_MOD_N")(reg_list=[self.q], param_list=[[control] + list(range(self.counting_bits, self.counting_bits + self.work_bits)), float(pow(self.base, 1 << control, self.modulus)), float(self.modulus)]))
        for left in range(self.counting_bits // 2):
                self.program_list.append(OperationRegistry.get_class("SWAP")(reg_list=[self.q], param_list=[left, self.counting_bits - 1 - left]))
        for target in range(self.counting_bits):
                for control in range(target):
                        self.program_list.append(OperationRegistry.get_class("CPHASE")(reg_list=[self.q], param_list=[control, target, -math.pi / (1 << (target - control))]))
                self.program_list.append(OperationRegistry.get_class("H")(reg_list=[self.q], param_list=[target]))
        self.declare_program_list()