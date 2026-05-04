# Generated from YAML definition

from ..core.operation import StandardComposite
from ..core.registry import OperationRegistry
from ..core.utils import merge_controllers
import math

class QECExampleBV(StandardComposite):
    """Bernstein-Vazirani (secret=0b101) — mirrors QEC-Compiler build_bv_circuit"""
    def __init__(self, reg_list, param_list=None, operations=None):
        if param_list is None:
            param_list = []
        StandardComposite.__init__(self, reg_list=reg_list, param_list=param_list, operations=operations)
        self.q0 = reg_list[0]
        self.q1 = reg_list[1]
        self.q2 = reg_list[2]
        self.anc = reg_list[3]
        self.n = param_list[0]
        self.program_list = [
            OperationRegistry.get_class("Hadamard")(reg_list=[self.q0]),
            OperationRegistry.get_class("Hadamard")(reg_list=[self.q1]),
            OperationRegistry.get_class("Hadamard")(reg_list=[self.q2]),
            OperationRegistry.get_class("CNOT")(reg_list=[self.q0, self.anc], param_list=[0, 0]),
            OperationRegistry.get_class("CNOT")(reg_list=[self.q2, self.anc], param_list=[0, 0]),
            OperationRegistry.get_class("Hadamard")(reg_list=[self.q0]),
            OperationRegistry.get_class("Hadamard")(reg_list=[self.q1]),
            OperationRegistry.get_class("Hadamard")(reg_list=[self.q2]),
        ]
        self.declare_program_list()