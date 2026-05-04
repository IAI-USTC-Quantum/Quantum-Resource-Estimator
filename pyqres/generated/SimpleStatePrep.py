# Generated from YAML definition

from ..core.operation import StandardComposite
from ..core.registry import OperationRegistry
from ..core.utils import merge_controllers
import math

class SimpleStatePrep(StandardComposite):
    """Simple state preparation for uniform superposition"""
    def __init__(self, reg_list, param_list=None, operations=None):
        if param_list is None:
            param_list = []
        StandardComposite.__init__(self, reg_list=reg_list, param_list=param_list, operations=operations)
        self.reg = reg_list[0]
        self.n_qubits = param_list[0]
        # Complex implementation with loops/conditionals
        self._impl_structure = [{"_type": "for_each", "var": "i", "items": "n_qubits", "body": [{"_type": "op", "op": "Hadamard", "qregs": ["reg"]}]}]
        self._build_execute_method()

    def _build_execute_method(self):
        # Build program_list by expanding loops and conditionals
        self.program_list = []
        for i in range(self.n_qubits):
                self.program_list.append(OperationRegistry.get_class("Hadamard")(reg_list=[self.reg]))
        self.declare_program_list()