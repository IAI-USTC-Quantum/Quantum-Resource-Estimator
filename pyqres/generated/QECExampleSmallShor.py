# Generated from YAML definition

from ..core.operation import StandardComposite
from ..core.registry import OperationRegistry
from ..core.utils import merge_controllers
import math
from ..algorithms.qec_examples import build_qec_small_shor

class QECExampleSmallShor(StandardComposite):
    """YAML mirror of QEC-Compiler small Shor fixture gates"""
    def __init__(self, reg_list, param_list=None, operations=None):
        if param_list is None:
            param_list = []
        StandardComposite.__init__(self, reg_list=reg_list, param_list=param_list, operations=operations)
        self.q = reg_list[0]
        self.modulus = param_list[0]
        self.base = param_list[1]
        # Complex implementation with loops/conditionals
        self._impl_structure = [{"_type": "python", "code": "from ..algorithms.qec_examples import build_qec_small_shor\n"}, {"_type": "python", "code": "build_qec_small_shor(self.program_list, self.q, self.modulus, self.base)\n"}]
        self._build_execute_method()

    def _build_execute_method(self):
        # Build program_list by expanding loops and conditionals
        self.program_list = []
        build_qec_small_shor(self.program_list, self.q, self.modulus, self.base)
        self.declare_program_list()