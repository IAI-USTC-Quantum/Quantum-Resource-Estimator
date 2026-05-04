# Generated from YAML definition

from ..core.operation import StandardComposite
from ..core.registry import OperationRegistry
from ..core.utils import merge_controllers
import math
from ..algorithms.qec_examples import build_qec_grover

class QECExampleGrover(StandardComposite):
    """YAML mirror of QEC-Compiler Grover benchmark gates"""
    def __init__(self, reg_list, param_list=None, operations=None):
        if param_list is None:
            param_list = []
        StandardComposite.__init__(self, reg_list=reg_list, param_list=param_list, operations=operations)
        self.q = reg_list[0]
        self.n = param_list[0]
        self.marked_states = param_list[1]
        self.iterations = param_list[2]
        # Complex implementation with loops/conditionals
        self._impl_structure = [{"_type": "python", "code": "from ..algorithms.qec_examples import build_qec_grover\n"}, {"_type": "python", "code": "build_qec_grover(\n    self.program_list, self.q, self.n, self.marked_states, self.iterations)\n"}]
        self._build_execute_method()

    def _build_execute_method(self):
        # Build program_list by expanding loops and conditionals
        self.program_list = []
        build_qec_grover(
            self.program_list, self.q, self.n, self.marked_states, self.iterations)
        self.declare_program_list()