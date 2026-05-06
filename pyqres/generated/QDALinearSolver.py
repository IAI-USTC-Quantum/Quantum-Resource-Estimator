# Generated from YAML definition

from ..core.operation import AbstractComposite
from ..core.registry import OperationRegistry
from ..core.utils import merge_controllers
import math

class QDALinearSolver(AbstractComposite):
    """QDA quantum linear system solver using discrete adiabatic evolution"""
    def __init__(self, reg_list, param_list=None, operations=None):
        if param_list is None:
            param_list = []
        AbstractComposite.__init__(self, reg_list=reg_list, param_list=param_list, operations=operations)
        self.main_reg = reg_list[0]
        self.anc_UA = reg_list[1]
        self.anc_1 = reg_list[2]
        self.anc_2 = reg_list[3]
        self.anc_3 = reg_list[4]
        self.anc_4 = reg_list[5]
        self.kappa = param_list[0]
        self.epsilon = param_list[1]
        self.p = 0.5
        self.n_steps = int(math.ceil(math.log(self.kappa / self.epsilon)))
        if operations is None:
            operations = []
        self.encode_A = operations[0] if 0 < len(operations) else None
        self.encode_b = operations[1] if 1 < len(operations) else None
        # Complex implementation with loops/conditionals
        self._impl_structure = [{"_type": "python", "code": "def compute_fs(s, kappa, p):\n    \"\"\"Compute f_s = p * (1 - s) + (1-p) * s\"\"\"\n    return p * (1 - s) + (1 - p) * s\n"}, {"_type": "op", "op": "X", "qregs": ["main_reg"], "params": [0]}, {"_type": "comment", "text": "State preparation |0\u27e9 \u2192 |b\u27e9 \u2014 via encode_b (operation param)"}, {"_type": "comment", "text": "Discrete adiabatic evolution: WalkS at each interpolation point s"}, {"_type": "op", "op": "X", "qregs": ["anc_1"], "params": [0]}]
        self._build_execute_method()

    def _build_execute_method(self):
        # Build program_list by expanding loops and conditionals
        self.program_list = []
        def compute_fs(s, kappa, p):
            """Compute f_s = p * (1 - s) + (1-p) * s"""
            return p * (1 - s) + (1 - p) * s
        self.program_list.append(OperationRegistry.get_class("X")(reg_list=[self.main_reg], param_list=[0]))
        if self.encode_b is not None:
            if callable(self.encode_b):
                self.program_list.append(self.encode_b(reg_list=[self.main_reg]))
            else:
                self.program_list.append(self.encode_b)
        for i in range(self.n_steps):
                s = i / max(1, self.n_steps - 1) if self.n_steps > 1 else 1.0
                fs = compute_fs(s, self.kappa, self.p)
                # Pass encode_A and encode_b as operations for block encoding
                walk_ops = []
                if self.encode_A:
                    walk_ops.append(self.encode_A)
                if self.encode_b:
                    walk_ops.append(self.encode_b)
                self.program_list.append(
                    OperationRegistry.get_class("WalkS_Primitive")(
                        reg_list=[self.main_reg, self.anc_UA, self.anc_1,
                                 self.anc_2, self.anc_3, self.anc_4],
                        param_list=[fs],
                        operations=walk_ops))
                pass
        self.program_list.append(OperationRegistry.get_class("X")(reg_list=[self.anc_1], param_list=[0]))
        self.declare_program_list()