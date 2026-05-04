# Generated from YAML definition

from ..core.operation import StandardComposite
from ..core.registry import OperationRegistry
from ..core.utils import merge_controllers
import math
from ..algorithms.qec_examples import build_qec_qaoa

class QECExampleQAOA(StandardComposite):
    """YAML mirror of QEC-Compiler QAOA benchmark gates"""
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
        # Complex implementation with loops/conditionals
        self._impl_structure = [{"_type": "python", "code": "from ..algorithms.qec_examples import build_qec_qaoa\n"}, {"_type": "python", "code": "build_qec_qaoa(\n    self.program_list, self.q, self.n_vertices, self.edges,\n    self.p, self.gamma, self.beta)\n"}]
        self._build_execute_method()

    def _build_execute_method(self):
        # Build program_list by expanding loops and conditionals
        self.program_list = []
        build_qec_qaoa(
            self.program_list, self.q, self.n_vertices, self.edges,
            self.p, self.gamma, self.beta)
        self.declare_program_list()