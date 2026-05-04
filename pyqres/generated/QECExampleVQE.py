# Generated from YAML definition

from ..core.operation import StandardComposite
from ..core.registry import OperationRegistry
from ..core.utils import merge_controllers
import math
from ..algorithms.qec_examples import build_qec_vqe

class QECExampleVQE(StandardComposite):
    """YAML mirror of QEC-Compiler VQE benchmark gates"""
    def __init__(self, reg_list, param_list=None, operations=None):
        if param_list is None:
            param_list = []
        StandardComposite.__init__(self, reg_list=reg_list, param_list=param_list, operations=operations)
        self.q = reg_list[0]
        self.n_qubits = param_list[0]
        self.layers = param_list[1]
        self.ring_entanglement = param_list[2]
        # Complex implementation with loops/conditionals
        self._impl_structure = [{"_type": "python", "code": "from ..algorithms.qec_examples import build_qec_vqe\n"}, {"_type": "python", "code": "build_qec_vqe(\n    self.program_list, self.q, self.n_qubits,\n    self.layers, self.ring_entanglement)\n"}]
        self._build_execute_method()

    def _build_execute_method(self):
        # Build program_list by expanding loops and conditionals
        self.program_list = []
        build_qec_vqe(
            self.program_list, self.q, self.n_qubits,
            self.layers, self.ring_entanglement)
        self.declare_program_list()