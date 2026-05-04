from .gates import (
    Hadamard, Hadamard_NDigits,
    X, Y, CNOT, Toffoli,
    Rx, Ry, PhaseGate, Rz, U3,
    # New Phase 2 gates
    Hadamard_Bool, Hadamard_PartialQubit,
    Sgate, Tgate, SXgate, U2gate,
    Swap_Bool_Bool, GlobalPhase,
)
from .arithmetic import (
    Add_UInt_UInt, Add_UInt_UInt_InPlace,
    Add_UInt_ConstUInt, Add_ConstUInt,
    Mult_UInt_ConstUInt,
    ShiftLeft, ShiftRight,
    Compare_UInt_UInt, Less_UInt_UInt, GetMid_UInt_UInt,
    Assign, Swap_General_General,
    Div_Sqrt_Arccos_Int_Int, Sqrt_Div_Arccos_Int_Int, GetRotateAngle_Int_Int,
    # Phase 2 arithmetic
    Add_Mult_UInt_ConstUInt, Mod_Mult_UInt_ConstUInt,
    AddAssign_AnyInt_AnyInt,
    CustomArithmetic, PlusOneAndOverflow,
    GetDataAddr, GetRowAddr,
)
from .register_ops import (
    SplitRegister, CombineRegister, Push, Pop,
    # New Phase 2 register ops
    AddRegister, AddRegisterWithHadamard, RemoveRegister, MoveBackRegister,
)
from .transform import QFT, InverseQFT, Reflection_Bool
from .state_prep import (
    Normalize, ClearZero, Init_Unsafe, Rot_GeneralStatePrep,
    # New Phase 2 state prep
    ViewNormalization, SortExceptKey, SortExceptKeyHadamard,
)
from .qram import QRAM, QRAMFast
from .cond_rot import (
    CondRot_General_Bool, CondRot_General_Bool_QW,
    ZeroConditionalPhaseFlip, RangeConditionalPhaseFlip,
    # New Phase 2 conditional rotations
    CondRot_Rational_Bool, Rot_GeneralUnitary, Rot_Bool,
    CondRot_Fixed_Bool, CondRot_General_Bool_QW_fast,
    GetQWRotateAngle_Int_Int_Int,
)
from .measurement import (
    PartialTrace, PartialTraceSelect, PartialTraceSelectRange,
    Prob, StatePrint,
)

from .debug import DebugPrimitive, CheckNan, CheckNormalization

# Intermediate / QEC-compiler IR layer
from .intermediate import (
    H, Z, SWAP, CPHASE, RX, RY, RZ, CCX,
    MCX, ADD, PLUS_ONE, REFLECT, MOD_ADD, MOD_MUL, CMUL_MOD_N,
)

__all__ = [
    # Gates
    "Hadamard", "Hadamard_NDigits",
    "X", "Y", "CNOT", "Toffoli",
    "Rx", "Ry", "PhaseGate", "Rz", "U3",
    "Hadamard_Bool", "Hadamard_PartialQubit",
    "Sgate", "Tgate", "SXgate", "U2gate",
    "Swap_Bool_Bool", "GlobalPhase",
    # Arithmetic
    "Add_UInt_UInt", "Add_UInt_UInt_InPlace",
    "Add_UInt_ConstUInt", "Add_ConstUInt",
    "Mult_UInt_ConstUInt",
    "ShiftLeft", "ShiftRight",
    "Compare_UInt_UInt", "Less_UInt_UInt", "GetMid_UInt_UInt",
    "Assign", "Swap_General_General",
    "Div_Sqrt_Arccos_Int_Int", "Sqrt_Div_Arccos_Int_Int", "GetRotateAngle_Int_Int",
    "Add_Mult_UInt_ConstUInt", "Mod_Mult_UInt_ConstUInt",
    "AddAssign_AnyInt_AnyInt",
    "CustomArithmetic", "PlusOneAndOverflow",
    "GetDataAddr", "GetRowAddr",
    # Register ops
    "SplitRegister", "CombineRegister", "Push", "Pop",
    "AddRegister", "AddRegisterWithHadamard", "RemoveRegister", "MoveBackRegister",
    # Transform
    "QFT", "InverseQFT", "Reflection_Bool",
    # State prep
    "Normalize", "ClearZero", "Init_Unsafe", "Rot_GeneralStatePrep",
    "ViewNormalization", "SortExceptKey", "SortExceptKeyHadamard",
    # QRAM
    "QRAM", "QRAMFast",
    # Conditional Rotation
    "CondRot_General_Bool", "CondRot_General_Bool_QW",
    "ZeroConditionalPhaseFlip", "RangeConditionalPhaseFlip",
    "CondRot_Rational_Bool", "Rot_GeneralUnitary", "Rot_Bool",
    "CondRot_Fixed_Bool", "CondRot_General_Bool_QW_fast",
    "GetQWRotateAngle_Int_Int_Int",
    # Measurement
    "PartialTrace", "PartialTraceSelect", "PartialTraceSelectRange",
    "Prob", "StatePrint",
    # Debug
    "DebugPrimitive", "CheckNan", "CheckNormalization",
    # Intermediate / QEC-compiler IR layer
    "H", "Z", "SWAP", "CPHASE", "RX", "RY", "RZ", "CCX",
    "MCX", "ADD", "PLUS_ONE", "REFLECT",
    "MOD_ADD", "MOD_MUL", "CMUL_MOD_N",
]
