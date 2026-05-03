pyqres.primitives
=================

门操作
------

.. currentmodule:: pyqres.primitives.gates

.. autoclass:: Hadamard
   :show-inheritance:
   :special-members: __init__

.. autoclass:: Hadamard_NDigits
   :show-inheritance:
   :special-members: __init__

.. autoclass:: X
   :show-inheritance:
   :special-members: __init__

.. autoclass:: Y
   :show-inheritance:
   :special-members: __init__

.. autoclass:: CNOT
   :show-inheritance:
   :special-members: __init__

.. autoclass:: Toffoli
   :show-inheritance:
   :special-members: __init__

.. autoclass:: Rx
   :show-inheritance:
   :special-members: __init__

.. autoclass:: Ry
   :show-inheritance:
   :special-members: __init__

.. autoclass:: PhaseGate
   :show-inheritance:
   :special-members: __init__

.. autoclass:: Rz
   :show-inheritance:
   :special-members: __init__

.. autoclass:: U3
   :show-inheritance:
   :special-members: __init__

新门 (Phase 2)
~~~~~~~~~~~~~~

.. autoclass:: Hadamard_Bool
   :show-inheritance:
   :special-members: __init__

.. autoclass:: Hadamard_PartialQubit
   :show-inheritance:
   :special-members: __init__

.. autoclass:: Sgate
   :show-inheritance:
   :special-members: __init__

.. autoclass:: Tgate
   :show-inheritance:
   :special-members: __init__

.. autoclass:: SXgate
   :show-inheritance:
   :special-members: __init__

.. autoclass:: U2gate
   :show-inheritance:
   :special-members: __init__

.. autoclass:: Swap_Bool_Bool
   :show-inheritance:
   :special-members: __init__

.. autoclass:: GlobalPhase
   :show-inheritance:
   :special-members: __init__

算术操作
--------

.. currentmodule:: pyqres.primitives.arithmetic

.. autoclass:: Add_UInt_UInt
   :show-inheritance:
   :special-members: __init__

.. autoclass:: Add_UInt_UInt_InPlace
   :show-inheritance:
   :special-members: __init__

.. autoclass:: Add_UInt_ConstUInt
   :show-inheritance:
   :special-members: __init__

.. autoclass:: Add_ConstUInt
   :show-inheritance:
   :special-members: __init__

.. autoclass:: Mult_UInt_ConstUInt
   :show-inheritance:
   :special-members: __init__

.. autoclass:: ShiftLeft
   :show-inheritance:
   :special-members: __init__

.. autoclass:: ShiftRight
   :show-inheritance:
   :special-members: __init__

.. autoclass:: Compare_UInt_UInt
   :show-inheritance:
   :special-members: __init__

.. autoclass:: Less_UInt_UInt
   :show-inheritance:
   :special-members: __init__

.. autoclass:: GetMid_UInt_UInt
   :show-inheritance:
   :special-members: __init__

.. autoclass:: Assign
   :show-inheritance:
   :special-members: __init__

.. autoclass:: Swap_General_General
   :show-inheritance:
   :special-members: __init__

新算术操作 (Phase 2)
~~~~~~~~~~~~~~~~~~~~

.. autoclass:: Add_Mult_UInt_ConstUInt
   :show-inheritance:
   :special-members: __init__

.. autoclass:: AddAssign_AnyInt_AnyInt
   :show-inheritance:
   :special-members: __init__

.. autoclass:: CustomArithmetic
   :show-inheritance:
   :special-members: __init__

.. autoclass:: PlusOneAndOverflow
   :show-inheritance:
   :special-members: __init__

.. autoclass:: GetDataAddr
   :show-inheritance:
   :special-members: __init__

.. autoclass:: GetRowAddr
   :show-inheritance:
   :special-members: __init__

QEC 中间层 Primitive
~~~~~~~~~~~~~~~~~~~~

.. currentmodule:: pyqres.primitives.intermediate

这些 primitive 是 pyqres 与 QEC-compiler 第一版联调使用的冻结中间层。
它们可以通过 ``pyqres.core.lowering.to_abstract_circuit`` lowering 为
QEC-compiler ``AbstractGate``，并由 QEC-compiler 继续分解到
``MCX``/Clifford/rotation/CCZ 路径。

.. autoclass:: MCX
   :show-inheritance:
   :special-members: __init__

.. autoclass:: ADD
   :show-inheritance:
   :special-members: __init__

.. autoclass:: PLUS_ONE
   :show-inheritance:
   :special-members: __init__

.. autoclass:: REFLECT
   :show-inheritance:
   :special-members: __init__

.. autoclass:: MOD_ADD
   :show-inheritance:
   :special-members: __init__

.. autoclass:: MOD_MUL
   :show-inheritance:
   :special-members: __init__

寄存器操作
----------

.. currentmodule:: pyqres.primitives.register_ops

.. autoclass:: SplitRegister
   :show-inheritance:
   :special-members: __init__

.. autoclass:: CombineRegister
   :show-inheritance:
   :special-members: __init__

.. autoclass:: Push
   :show-inheritance:
   :special-members: __init__

.. autoclass:: Pop
   :show-inheritance:
   :special-members: __init__

新寄存器操作 (Phase 2)
~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: AddRegister
   :show-inheritance:
   :special-members: __init__

.. autoclass:: AddRegisterWithHadamard
   :show-inheritance:
   :special-members: __init__

.. autoclass:: RemoveRegister
   :show-inheritance:
   :special-members: __init__

.. autoclass:: MoveBackRegister
   :show-inheritance:
   :special-members: __init__

变换操作
--------

.. currentmodule:: pyqres.primitives.transform

.. autoclass:: QFT
   :show-inheritance:
   :special-members: __init__

.. autoclass:: InverseQFT
   :show-inheritance:
   :special-members: __init__

.. autoclass:: Reflection_Bool
   :show-inheritance:
   :special-members: __init__

态制备
------

.. currentmodule:: pyqres.primitives.state_prep

.. autoclass:: Normalize
   :show-inheritance:
   :special-members: __init__

.. autoclass:: ClearZero
   :show-inheritance:
   :special-members: __init__

.. autoclass:: Init_Unsafe
   :show-inheritance:
   :special-members: __init__

.. autoclass:: Rot_GeneralStatePrep
   :show-inheritance:
   :special-members: __init__

.. autoclass:: ViewNormalization
   :show-inheritance:
   :special-members: __init__

QRAM
----

.. currentmodule:: pyqres.primitives.qram

.. autoclass:: QRAM
   :show-inheritance:
   :special-members: __init__

.. autoclass:: QRAMFast
   :show-inheritance:
   :special-members: __init__

条件旋转
--------

.. currentmodule:: pyqres.primitives.cond_rot

.. autoclass:: CondRot_General_Bool
   :show-inheritance:
   :special-members: __init__

.. autoclass:: CondRot_General_Bool_QW
   :show-inheritance:
   :special-members: __init__

.. autoclass:: ZeroConditionalPhaseFlip
   :show-inheritance:
   :special-members: __init__

.. autoclass:: RangeConditionalPhaseFlip
   :show-inheritance:
   :special-members: __init__

.. autoclass:: CondRot_Rational_Bool
   :show-inheritance:
   :special-members: __init__

.. autoclass:: Rot_GeneralUnitary
   :show-inheritance:
   :special-members: __init__

测量
----

.. currentmodule:: pyqres.primitives.measurement

.. autoclass:: PartialTrace
   :show-inheritance:
   :special-members: __init__

.. autoclass:: PartialTraceSelect
   :show-inheritance:
   :special-members: __init__

.. autoclass:: PartialTraceSelectRange
   :show-inheritance:
   :special-members: __init__

.. autoclass:: Prob
   :show-inheritance:
   :special-members: __init__

.. autoclass:: StatePrint
   :show-inheritance:
   :special-members: __init__
