# Generated from YAML definition

from ..core.operation import StandardComposite
from ..core.registry import OperationRegistry
from ..core.utils import merge_controllers
import math
from ..algorithms.qec_examples import build_qec_qpe

class QECExampleQPE(StandardComposite):
    """YAML mirror of QEC-Compiler QPE benchmark gates"""
    def __init__(self, reg_list, param_list=None, operations=None):
        if param_list is None:
            param_list = []
        StandardComposite.__init__(self, reg_list=reg_list, param_list=param_list, operations=operations)
        self.q = reg_list[0]
        self.n_counting = param_list[0]
        self.n_system = param_list[1]
        self.unitary_eigenvalue = param_list[2]
        # Complex implementation with loops/conditionals
        self._impl_structure = [{"_type": "python", "code": "from ..algorithms.qec_examples import build_qec_qpe\n"}, {"_type": "python", "code": "build_qec_qpe(\n    self.program_list, self.q, self.n_counting,\n    self.n_system, self.unitary_eigenvalue)\n"}]
        self._build_execute_method()

    def _build_execute_method(self):
        # Build program_list by expanding loops and conditionals
        self.program_list = []
        build_qec_qpe(
            self.program_list, self.q, self.n_counting,
            self.n_system, self.unitary_eigenvalue)
        self.declare_program_list()