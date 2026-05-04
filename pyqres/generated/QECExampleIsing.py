# Generated from YAML definition

from ..core.operation import StandardComposite
from ..core.registry import OperationRegistry
from ..core.utils import merge_controllers
import math
from ..algorithms.qec_examples import build_qec_ising

class QECExampleIsing(StandardComposite):
    """YAML mirror of QEC-Compiler Ising benchmark gates"""
    def __init__(self, reg_list, param_list=None, operations=None):
        if param_list is None:
            param_list = []
        StandardComposite.__init__(self, reg_list=reg_list, param_list=param_list, operations=operations)
        self.q = reg_list[0]
        self.n_spins = param_list[0]
        self.couplings = param_list[1]
        self.p_level = param_list[2]
        self.h_transverse = param_list[3]
        # Complex implementation with loops/conditionals
        self._impl_structure = [{"_type": "python", "code": "from ..algorithms.qec_examples import build_qec_ising\n"}, {"_type": "python", "code": "build_qec_ising(\n    self.program_list, self.q, self.n_spins, self.couplings,\n    self.p_level, self.h_transverse)\n"}]
        self._build_execute_method()

    def _build_execute_method(self):
        # Build program_list by expanding loops and conditionals
        self.program_list = []
        build_qec_ising(
            self.program_list, self.q, self.n_spins, self.couplings,
            self.p_level, self.h_transverse)
        self.declare_program_list()