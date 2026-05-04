# Generated from YAML definition

from ..core.operation import StandardComposite
from ..core.registry import OperationRegistry
from ..core.utils import merge_controllers
import math

class QECExampleQAOA(StandardComposite):
    """QAOA MaxCut benchmark algorithm"""
    def __init__(self, reg_list, param_list=None, operations=None):
        if param_list is None:
            param_list = []
        StandardComposite.__init__(self, reg_list=reg_list, param_list=param_list, operations=operations)
        self.q = reg_list[0]
        self.n_vertices = param_list[0]
        self.edges = param_list[1]
        self.p = param_list[2]
        self.gamma = param_list[3]
        self.beta = param_list[4]
        self.gamma_step = self.gamma / self.p
        self.beta_step = self.beta / self.p
        # Complex implementation with loops/conditionals
        self._impl_structure = [{"_type": "for_each", "var": "i", "items": "n_vertices", "body": [{"_type": "op", "op": "H", "qregs": ["q"], "params": [{"type": "expr", "value": "i"}]}]}, {"_type": "loop", "iterations": "p", "body": [{"_type": "for_each", "var": "edge", "items": "edges", "body": [{"_type": "op", "op": "CNOT", "qregs": ["q", "q"], "params": [{"type": "expr", "value": "edge[0]"}, {"type": "expr", "value": "edge[1]"}]}, {"_type": "op", "op": "RZ", "qregs": ["q"], "params": [{"type": "expr", "value": "edge[1]"}, {"type": "expr", "value": "gamma_step"}]}, {"_type": "op", "op": "CNOT", "qregs": ["q", "q"], "params": [{"type": "expr", "value": "edge[0]"}, {"type": "expr", "value": "edge[1]"}]}]}, {"_type": "for_each", "var": "i", "items": "n_vertices", "body": [{"_type": "op", "op": "RX", "qregs": ["q"], "params": [{"type": "expr", "value": "i"}, {"type": "expr", "value": "beta_step"}]}]}]}]
        self._build_execute_method()

    def _build_execute_method(self):
        # Build program_list by expanding loops and conditionals
        self.program_list = []
        for i in range(self.n_vertices):
                self.program_list.append(OperationRegistry.get_class("H")(reg_list=[self.q], param_list=[i]))
        for i in range(self.p):
                for edge in self.edges:
                        self.program_list.append(OperationRegistry.get_class("CNOT")(reg_list=[self.q, self.q], param_list=[edge[0], edge[1]]))
                        self.program_list.append(OperationRegistry.get_class("RZ")(reg_list=[self.q], param_list=[edge[1], self.gamma_step]))
                        self.program_list.append(OperationRegistry.get_class("CNOT")(reg_list=[self.q, self.q], param_list=[edge[0], edge[1]]))
                for i in range(self.n_vertices):
                        self.program_list.append(OperationRegistry.get_class("RX")(reg_list=[self.q], param_list=[i, self.beta_step]))
        self.declare_program_list()