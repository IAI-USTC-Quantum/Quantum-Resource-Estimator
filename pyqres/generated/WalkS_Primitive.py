# Generated from YAML definition

from ..core.operation import AbstractComposite
from ..core.registry import OperationRegistry
from ..core.utils import merge_controllers
import math
from pyqres.primitives import Hadamard_Bool, X, Rot_Bool, Reflection_Bool, GlobalPhase

class WalkS_Primitive(AbstractComposite):
    """Quantum walk step W_s = R · H_s via discrete adiabatic evolution"""
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
        self.fs = param_list[0]
        if operations is None:
            operations = []
        self.encode_A = operations[0] if 0 < len(operations) else None
        self.encode_b = operations[1] if 1 < len(operations) else None
        # Complex implementation with loops/conditionals
        self._impl_structure = [{"_type": "python", "code": "from pyqres.primitives import Hadamard_Bool, X, Rot_Bool, Reflection_Bool, GlobalPhase\nimport math\n\ndef _compute_rotation_matrix(fs):\n    sqrt_n = 1.0 / math.sqrt((1 - fs) ** 2 + fs ** 2)\n    r00 = sqrt_n * (1 - fs)\n    r01 = sqrt_n * fs\n    r10 = sqrt_n * fs\n    r11 = sqrt_n * (fs - 1)\n    return [complex(r00, 0), complex(r01, 0), complex(r10, 0), complex(r11, 0)]\n"}, {"_type": "python", "code": "R_s = _compute_rotation_matrix(self.fs)\n"}, {"_type": "op", "op": "Hadamard_Bool", "qregs": ["anc_3"]}, {"_type": "python", "code": "if self.encode_b is not None:\n    # encode_b can be a callable (function returning op) or a class/instance\n    if callable(self.encode_b):\n        _enc = self.encode_b(reg_list=[self.main_reg])\n    else:\n        _enc = self.encode_b\n    self.program_list.append(_enc.dagger())\n"}, {"_type": "op", "op": "X", "qregs": ["anc_1"], "params": [0]}, {"_type": "op", "op": "Reflection_Bool", "qregs": ["main_reg"], "params": [True], "controllers": {"all_ones": ["anc_1", "anc_3", "anc_4"]}}, {"_type": "op", "op": "X", "qregs": ["anc_1"], "params": [0]}, {"_type": "python", "code": "if self.encode_b is not None:\n    if callable(self.encode_b):\n        self.program_list.append(self.encode_b(reg_list=[self.main_reg]))\n    else:\n        self.program_list.append(self.encode_b)\n"}, {"_type": "op", "op": "X", "qregs": ["anc_4"], "params": [0]}, {"_type": "python", "code": "self.program_list.append(\n    Rot_Bool(reg_list=[self.anc_2], param_list=[R_s]).\n        control_by_all_ones([self.anc_4]))\n"}, {"_type": "op", "op": "X", "qregs": ["anc_4"], "params": [0]}, {"_type": "op", "op": "Hadamard_Bool", "qregs": ["anc_2"], "controllers": {"all_ones": ["anc_4"]}}, {"_type": "python", "code": "if self.encode_A is not None:\n    if callable(self.encode_A):\n        _enc = self.encode_A(reg_list=[self.main_reg, self.anc_UA], param_list=[])\n    else:\n        _enc = self.encode_A\n    self.program_list.append(_enc.control_by_all_ones([self.anc_1, self.anc_2]))\n"}, {"_type": "op", "op": "X", "qregs": ["anc_1"], "params": [0], "controllers": {"all_ones": ["anc_2"]}}, {"_type": "op", "op": "Reflection_Bool", "qregs": ["anc_2"], "params": [True], "controllers": {"all_ones": ["anc_1"]}}, {"_type": "python", "code": "if self.encode_A is not None:\n    if callable(self.encode_A):\n        _enc = self.encode_A(reg_list=[self.main_reg, self.anc_UA], param_list=[])\n    else:\n        _enc = self.encode_A\n    self.program_list.append(_enc.control_by_all_ones([self.anc_1, self.anc_2]))\n"}, {"_type": "op", "op": "X", "qregs": ["anc_4"], "params": [0]}, {"_type": "op", "op": "Hadamard_Bool", "qregs": ["anc_2"], "controllers": {"all_ones": ["anc_4"]}}, {"_type": "op", "op": "X", "qregs": ["anc_4"], "params": [0]}, {"_type": "python", "code": "self.program_list.append(\n    Rot_Bool(reg_list=[self.anc_2], param_list=[R_s]).\n        control_by_all_ones([self.anc_4]))\n"}, {"_type": "python", "code": "if self.encode_b is not None:\n    if callable(self.encode_b):\n        _enc = self.encode_b(reg_list=[self.main_reg])\n    else:\n        _enc = self.encode_b\n    self.program_list.append(_enc.dagger())\n"}, {"_type": "op", "op": "X", "qregs": ["anc_1"], "params": [0]}, {"_type": "op", "op": "Reflection_Bool", "qregs": ["main_reg"], "params": [True], "controllers": {"all_ones": ["anc_1", "anc_3", "anc_4"]}}, {"_type": "op", "op": "X", "qregs": ["anc_1"], "params": [0]}, {"_type": "python", "code": "if self.encode_b is not None:\n    if callable(self.encode_b):\n        self.program_list.append(self.encode_b(reg_list=[self.main_reg]))\n    else:\n        self.program_list.append(self.encode_b)\n"}, {"_type": "op", "op": "Hadamard_Bool", "qregs": ["anc_3"]}, {"_type": "op", "op": "Reflection_Bool", "qregs": ["anc_UA", "anc_2", "anc_3"], "params": [False]}, {"_type": "python", "code": "self.program_list.append(\n    GlobalPhase(reg_list=[self.anc_UA], param_list=[complex(0, 1)]))\n"}]
        self._build_execute_method()

    def _build_execute_method(self):
        # Build program_list by expanding loops and conditionals
        self.program_list = []
        from pyqres.primitives import Hadamard_Bool, X, Rot_Bool, Reflection_Bool, GlobalPhase
        import math
        
        def _compute_rotation_matrix(fs):
            sqrt_n = 1.0 / math.sqrt((1 - fs) ** 2 + fs ** 2)
            r00 = sqrt_n * (1 - fs)
            r01 = sqrt_n * fs
            r10 = sqrt_n * fs
            r11 = sqrt_n * (fs - 1)
            return [complex(r00, 0), complex(r01, 0), complex(r10, 0), complex(r11, 0)]
        R_s = _compute_rotation_matrix(self.fs)
        self.program_list.append(OperationRegistry.get_class("Hadamard_Bool")(reg_list=[self.anc_3]))
        if self.encode_b is not None:
            # encode_b can be a callable (function returning op) or a class/instance
            if callable(self.encode_b):
                _enc = self.encode_b(reg_list=[self.main_reg])
            else:
                _enc = self.encode_b
            self.program_list.append(_enc.dagger())
        self.program_list.append(OperationRegistry.get_class("X")(reg_list=[self.anc_1], param_list=[0]))
        self.program_list.append(OperationRegistry.get_class("Reflection_Bool")(reg_list=[self.main_reg], param_list=[True]).control_by_all_ones([self.anc_1, self.anc_3, self.anc_4]))
        self.program_list.append(OperationRegistry.get_class("X")(reg_list=[self.anc_1], param_list=[0]))
        if self.encode_b is not None:
            if callable(self.encode_b):
                self.program_list.append(self.encode_b(reg_list=[self.main_reg]))
            else:
                self.program_list.append(self.encode_b)
        self.program_list.append(OperationRegistry.get_class("X")(reg_list=[self.anc_4], param_list=[0]))
        self.program_list.append(
            Rot_Bool(reg_list=[self.anc_2], param_list=[R_s]).
                control_by_all_ones([self.anc_4]))
        self.program_list.append(OperationRegistry.get_class("X")(reg_list=[self.anc_4], param_list=[0]))
        self.program_list.append(OperationRegistry.get_class("Hadamard_Bool")(reg_list=[self.anc_2]).control_by_all_ones([self.anc_4]))
        if self.encode_A is not None:
            if callable(self.encode_A):
                _enc = self.encode_A(reg_list=[self.main_reg, self.anc_UA], param_list=[])
            else:
                _enc = self.encode_A
            self.program_list.append(_enc.control_by_all_ones([self.anc_1, self.anc_2]))
        self.program_list.append(OperationRegistry.get_class("X")(reg_list=[self.anc_1], param_list=[0]).control_by_all_ones([self.anc_2]))
        self.program_list.append(OperationRegistry.get_class("Reflection_Bool")(reg_list=[self.anc_2], param_list=[True]).control_by_all_ones([self.anc_1]))
        if self.encode_A is not None:
            if callable(self.encode_A):
                _enc = self.encode_A(reg_list=[self.main_reg, self.anc_UA], param_list=[])
            else:
                _enc = self.encode_A
            self.program_list.append(_enc.control_by_all_ones([self.anc_1, self.anc_2]))
        self.program_list.append(OperationRegistry.get_class("X")(reg_list=[self.anc_4], param_list=[0]))
        self.program_list.append(OperationRegistry.get_class("Hadamard_Bool")(reg_list=[self.anc_2]).control_by_all_ones([self.anc_4]))
        self.program_list.append(OperationRegistry.get_class("X")(reg_list=[self.anc_4], param_list=[0]))
        self.program_list.append(
            Rot_Bool(reg_list=[self.anc_2], param_list=[R_s]).
                control_by_all_ones([self.anc_4]))
        if self.encode_b is not None:
            if callable(self.encode_b):
                _enc = self.encode_b(reg_list=[self.main_reg])
            else:
                _enc = self.encode_b
            self.program_list.append(_enc.dagger())
        self.program_list.append(OperationRegistry.get_class("X")(reg_list=[self.anc_1], param_list=[0]))
        self.program_list.append(OperationRegistry.get_class("Reflection_Bool")(reg_list=[self.main_reg], param_list=[True]).control_by_all_ones([self.anc_1, self.anc_3, self.anc_4]))
        self.program_list.append(OperationRegistry.get_class("X")(reg_list=[self.anc_1], param_list=[0]))
        if self.encode_b is not None:
            if callable(self.encode_b):
                self.program_list.append(self.encode_b(reg_list=[self.main_reg]))
            else:
                self.program_list.append(self.encode_b)
        self.program_list.append(OperationRegistry.get_class("Hadamard_Bool")(reg_list=[self.anc_3]))
        self.program_list.append(OperationRegistry.get_class("Reflection_Bool")(reg_list=[self.anc_UA, self.anc_2, self.anc_3], param_list=[False]))
        self.program_list.append(
            GlobalPhase(reg_list=[self.anc_UA], param_list=[complex(0, 1)]))
        self.declare_program_list()