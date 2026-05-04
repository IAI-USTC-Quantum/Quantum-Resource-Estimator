# Generated from YAML definition

from ..core.operation import StandardComposite
from ..core.registry import OperationRegistry
from ..core.utils import merge_controllers
import math

class QECExampleSwapTest(StandardComposite):
    """SWAP-test benchmark algorithm"""
    def __init__(self, reg_list, param_list=None, operations=None):
        if param_list is None:
            param_list = []
        StandardComposite.__init__(self, reg_list=reg_list, param_list=param_list, operations=operations)
        self.q = reg_list[0]
        self.total_qubits = param_list[0]
        self.n_data = (self.total_qubits - 1) // 2
        # Complex implementation with loops/conditionals
        self._impl_structure = [{"_type": "op", "op": "H", "qregs": ["q"], "params": [0]}, {"_type": "for_each", "var": "offset", "items": "n_data", "body": [{"_type": "op", "op": "RY", "qregs": ["q"], "params": [{"type": "expr", "value": "1 + offset"}, {"type": "expr", "value": "math.pi * (offset + 1) / (2 * (n_data + 1))"}]}]}, {"_type": "for_each", "var": "offset", "items": "n_data", "body": [{"_type": "op", "op": "RZ", "qregs": ["q"], "params": [{"type": "expr", "value": "1 + n_data + offset"}, {"type": "expr", "value": "math.pi * (offset + 2) / (3 * (n_data + 1))"}]}, {"_type": "if", "condition": "offset % 2 == 0", "body": [{"_type": "op", "op": "X", "qregs": ["q"], "params": [{"type": "expr", "value": "1 + n_data + offset"}]}]}]}, {"_type": "for_each", "var": "offset", "items": "n_data", "body": [{"_type": "op", "op": "CNOT", "qregs": ["q", "q"], "params": [{"type": "expr", "value": "1 + n_data + offset"}, {"type": "expr", "value": "1 + offset"}]}, {"_type": "op", "op": "CCX", "qregs": ["q"], "params": [0, {"type": "expr", "value": "1 + offset"}, {"type": "expr", "value": "1 + n_data + offset"}]}, {"_type": "op", "op": "CNOT", "qregs": ["q", "q"], "params": [{"type": "expr", "value": "1 + n_data + offset"}, {"type": "expr", "value": "1 + offset"}]}]}, {"_type": "op", "op": "H", "qregs": ["q"], "params": [0]}]
        self._build_execute_method()

    def _build_execute_method(self):
        # Build program_list by expanding loops and conditionals
        self.program_list = []
        self.program_list.append(OperationRegistry.get_class("H")(reg_list=[self.q], param_list=[0]))
        for offset in range(self.n_data):
                self.program_list.append(OperationRegistry.get_class("RY")(reg_list=[self.q], param_list=[1 + offset, math.pi * (offset + 1) / (2 * (self.n_data + 1))]))
        for offset in range(self.n_data):
                self.program_list.append(OperationRegistry.get_class("RZ")(reg_list=[self.q], param_list=[1 + self.n_data + offset, math.pi * (offset + 2) / (3 * (self.n_data + 1))]))
                if offset % 2 == 0:
                        self.program_list.append(OperationRegistry.get_class("X")(reg_list=[self.q], param_list=[1 + self.n_data + offset]))
        for offset in range(self.n_data):
                self.program_list.append(OperationRegistry.get_class("CNOT")(reg_list=[self.q, self.q], param_list=[1 + self.n_data + offset, 1 + offset]))
                self.program_list.append(OperationRegistry.get_class("CCX")(reg_list=[self.q], param_list=[0, 1 + offset, 1 + self.n_data + offset]))
                self.program_list.append(OperationRegistry.get_class("CNOT")(reg_list=[self.q, self.q], param_list=[1 + self.n_data + offset, 1 + offset]))
        self.program_list.append(OperationRegistry.get_class("H")(reg_list=[self.q], param_list=[0]))
        self.declare_program_list()