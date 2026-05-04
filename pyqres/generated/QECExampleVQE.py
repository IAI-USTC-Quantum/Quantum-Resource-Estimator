# Generated from YAML definition

from ..core.operation import StandardComposite
from ..core.registry import OperationRegistry
from ..core.utils import merge_controllers
import math

class QECExampleVQE(StandardComposite):
    """Hardware-efficient VQE ansatz benchmark algorithm"""
    def __init__(self, reg_list, param_list=None, operations=None):
        if param_list is None:
            param_list = []
        StandardComposite.__init__(self, reg_list=reg_list, param_list=param_list, operations=operations)
        self.q = reg_list[0]
        self.n_qubits = param_list[0]
        self.layers = param_list[1]
        self.ring_entanglement = param_list[2]
        # Complex implementation with loops/conditionals
        self._impl_structure = [{"_type": "for_each", "var": "layer", "items": "layers", "body": [{"_type": "for_each", "var": "qubit", "items": "n_qubits", "body": [{"_type": "op", "op": "RY", "qregs": ["q"], "params": [{"type": "expr", "value": "qubit"}, {"type": "expr", "value": "math.pi * (layer + 1) * (qubit + 1) / (2 * (n_qubits + layers))"}]}, {"_type": "op", "op": "RZ", "qregs": ["q"], "params": [{"type": "expr", "value": "qubit"}, {"type": "expr", "value": "math.pi * (layer + 1) * (qubit + 2) / (4 * (n_qubits + layers))"}]}]}, {"_type": "for_each", "var": "control", "items": {"type": "expr", "value": "range(n_qubits - 1)"}, "body": [{"_type": "op", "op": "CNOT", "qregs": ["q", "q"], "params": [{"type": "expr", "value": "control"}, {"type": "expr", "value": "control + 1"}]}]}, {"_type": "if", "condition": "ring_entanglement and n_qubits > 2", "body": [{"_type": "op", "op": "CNOT", "qregs": ["q", "q"], "params": [{"type": "expr", "value": "n_qubits - 1"}, 0]}]}]}]
        self._build_execute_method()

    def _build_execute_method(self):
        # Build program_list by expanding loops and conditionals
        self.program_list = []
        for layer in range(self.layers):
                for qubit in range(self.n_qubits):
                        self.program_list.append(OperationRegistry.get_class("RY")(reg_list=[self.q], param_list=[qubit, math.pi * (layer + 1) * (qubit + 1) / (2 * (self.n_qubits + self.layers))]))
                        self.program_list.append(OperationRegistry.get_class("RZ")(reg_list=[self.q], param_list=[qubit, math.pi * (layer + 1) * (qubit + 2) / (4 * (self.n_qubits + self.layers))]))
                for control in range(self.n_qubits - 1):
                        self.program_list.append(OperationRegistry.get_class("CNOT")(reg_list=[self.q, self.q], param_list=[control, control + 1]))
                if self.ring_entanglement and self.n_qubits > 2:
                        self.program_list.append(OperationRegistry.get_class("CNOT")(reg_list=[self.q, self.q], param_list=[self.n_qubits - 1, 0]))
        self.declare_program_list()