# Generated from YAML definition

from ..core.operation import StandardComposite
from ..core.registry import OperationRegistry
from ..core.utils import merge_controllers
import math

class QECExampleGHZ(StandardComposite):
    """GHZ state preparation — mirrors QEC-Compiler build_ghz_circuit"""
    def __init__(self, reg_list, param_list=None, operations=None):
        if param_list is None:
            param_list = []
        StandardComposite.__init__(self, reg_list=reg_list, param_list=param_list, operations=operations)
        self.q0 = reg_list[0]
        self.q1 = reg_list[1]
        self.q2 = reg_list[2]
        self.n = param_list[0]
        self.program_list = [
            OperationRegistry.get_class("Hadamard")(reg_list=[self.q0]),
            OperationRegistry.get_class("CNOT")(reg_list=[self.q0, self.q1], param_list=[0, 0]),
            OperationRegistry.get_class("CNOT")(reg_list=[self.q1, self.q2], param_list=[0, 0]),
        ]
        self.declare_program_list()