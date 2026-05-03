# Top-level exports
from .core import (
    # Base classes
    Operation, Primitive, Composite,
    StandardComposite, AbstractComposite,
    # Registry
    OperationRegistry,
    # Metadata
    RegisterMetadata, ProgramMetadata, program_metadata,
    # Visitors
    TCounter, TDepthCounter, ToffoliCounter,
    TreeRenderer, PlainRenderer,
    tree_renderer, plain_renderer,
    # Utilities
    merge_controllers, reg_sz, get_control_qubit_count, mcx_t_count,
    # Lowering
    LoweringEngine, TCountEstimator, TDepthEstimator, ToffoliCountEstimator,
    # Simulator
    SimulatorVisitor, PyQSparseOperationWrapper,
    # Helpers
    mock_submodule,
)
from .primitives import (
    # Gates
    Hadamard, Hadamard_NDigits, X, Y, CNOT, Toffoli,
    Rx, Ry, PhaseGate, Rz, U3,
    # Arithmetic
    Add_UInt_UInt, Add_UInt_UInt_InPlace,
    Add_UInt_ConstUInt, Add_ConstUInt,
    Mult_UInt_ConstUInt,
    ShiftLeft, ShiftRight,
    Compare_UInt_UInt, Less_UInt_UInt, GetMid_UInt_UInt,
    Assign, Swap_General_General,
    Div_Sqrt_Arccos_Int_Int, Sqrt_Div_Arccos_Int_Int, GetRotateAngle_Int_Int,
    # Register ops
    SplitRegister, CombineRegister, Push, Pop,
    # Transform
    QFT, InverseQFT, Reflection_Bool,
    # State prep
    Normalize, ClearZero, Init_Unsafe, Rot_GeneralStatePrep,
    # QRAM
    QRAM,
)
from .algorithms import AmplitudeAmplification, Tomography, LinearSolver
from .visualization import (
    operation_to_tree_data,
    render_call_tree_html,
    render_circuit_html,
    write_call_tree_html,
    write_circuit_html,
)

# Backward compatibility aliases
BaseProgram = Composite
FinalProgram = Primitive
AbstractProgram = AbstractComposite

# DSL (optional import)
try:
    from . import dsl
except ImportError:
    pass
