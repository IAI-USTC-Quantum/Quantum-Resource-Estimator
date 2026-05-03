pyqres.core
===========

核心操作类
----------

.. currentmodule:: pyqres.core.operation

Operation
~~~~~~~~~

.. autoclass:: Operation
   :members:
   :show-inheritance:
   :special-members: __init__

Primitive
~~~~~~~~~

.. autoclass:: Primitive
   :members:
   :show-inheritance:
   :special-members: __init__

Composite
~~~~~~~~~

.. autoclass:: Composite
   :members:
   :show-inheritance:
   :special-members: __init__

StandardComposite
~~~~~~~~~~~~~~~~~

.. autoclass:: StandardComposite
   :members:
   :show-inheritance:
   :special-members: __init__

AbstractComposite
~~~~~~~~~~~~~~~~~

.. autoclass:: AbstractComposite
   :members:
   :show-inheritance:
   :special-members: __init__

注册表
------

.. currentmodule:: pyqres.core.registry

OperationRegistry
~~~~~~~~~~~~~~~~~

.. autoclass:: OperationRegistry
   :members:
   :special-members: __init__

元数据
------

.. currentmodule:: pyqres.core.metadata

RegisterMetadata
~~~~~~~~~~~~~~~~

.. autoclass:: RegisterMetadata
   :members:
   :special-members: __init__

ProgramMetadata
~~~~~~~~~~~~~~~

.. autoclass:: ProgramMetadata
   :members:
   :special-members: __init__

访问者
------

.. currentmodule:: pyqres.core.visitor

TCounter
~~~~~~~~

.. autoclass:: TCounter
   :members:
   :special-members: __init__

TDepthCounter
~~~~~~~~~~~~~

.. autoclass:: TDepthCounter
   :members:
   :special-members: __init__

TreeRenderer
~~~~~~~~~~~~

.. autoclass:: TreeRenderer
   :members:
   :special-members: __init__

PlainRenderer
~~~~~~~~~~~~~

.. autoclass:: PlainRenderer
   :members:
   :special-members: __init__

ToffoliCounter
~~~~~~~~~~~~~~

.. autoclass:: ToffoliCounter
   :members:
   :special-members: __init__

Lowering
--------

.. currentmodule:: pyqres.core.lowering

LoweringEngine
~~~~~~~~~~~~~~

.. autoclass:: LoweringEngine
   :members:
   :special-members: __init__

TCountEstimator
~~~~~~~~~~~~~~~

.. autoclass:: TCountEstimator
   :members:
   :special-members: __init__

TDepthEstimator
~~~~~~~~~~~~~~~

.. autoclass:: TDepthEstimator
   :members:
   :special-members: __init__

QECEstimator
~~~~~~~~~~~~

.. autoclass:: QECEstimator
   :members:
   :special-members: __init__

.. autofunction:: to_abstract_circuit

QEC lowering internals
~~~~~~~~~~~~~~~~~~~~~~

.. currentmodule:: pyqres.core.qec_lowering

.. autoclass:: QECLoweringVisitor
   :members:
   :special-members: __init__

.. autoclass:: UnsupportedQECPrimitive
   :members:

模拟器
------

.. currentmodule:: pyqres.core.simulator

SimulatorVisitor
~~~~~~~~~~~~~~~~

.. autoclass:: SimulatorVisitor
   :members:
   :special-members: __init__

PyQSparseOperationWrapper
~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: PyQSparseOperationWrapper
   :members:
   :special-members: __init__

工具函数
--------

.. currentmodule:: pyqres.core.utils

.. autofunction:: merge_controllers

.. autofunction:: reg_sz

.. autofunction:: get_control_qubit_count

.. autofunction:: mcx_t_count
