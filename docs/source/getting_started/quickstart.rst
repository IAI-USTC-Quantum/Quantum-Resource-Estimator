快速入门
========

Quantum-Resource-Estimator 采用 register-level Operation tree。一个量子程序既可以用于
PySparQ simulation，也可以 lowering 到 QEC-Compiler ``AbstractCircuit``。

基本概念
--------

* **RegisterMetadata**：声明寄存器名、宽度和类型。
* **Operation**：量子操作节点，分为 ``Primitive`` 和 ``Composite``。
* **Visitor**：遍历 Operation tree，用于 simulation、resource counting、QEC lowering。
* **YAML DSL**：声明 composite operation，并生成 Python 类。

第一个 simulation 例子
---------------------

.. code-block:: python

   import pysparq as ps

   from pyqres.core.metadata import RegisterMetadata
   from pyqres.core.simulator import SimulatorVisitor
   from pyqres.primitives import Hadamard, X

   rm = RegisterMetadata.get_register_metadata()
   rm.declare_register("q", 2, "UnsignedInteger")

   sim = SimulatorVisitor()
   Hadamard(["q"]).traverse(sim)
   X(["q"], [0]).traverse(sim)

   print(ps.StatePrint(sim.state, ps.StatePrintDisplay.Detail))

第一个 QEC lowering 例子
------------------------

.. code-block:: python

   from pyqres.core.lowering import to_abstract_circuit
   from pyqres.core.metadata import RegisterMetadata
   from pyqres.primitives import Hadamard, CNOT

   rm = RegisterMetadata.get_register_metadata()
   rm.declare_register("q0", 1, "Boolean")
   rm.declare_register("q1", 1, "Boolean")

   class BellProgram:
       def __init__(self):
           self.program_list = [Hadamard(["q0"]), CNOT(["q0", "q1"], [0, 0])]

       def traverse(self, visitor, dagger_ctx=False, controllers_ctx=None):
           for op in self.program_list:
               op.traverse(visitor, dagger_ctx, controllers_ctx or {})

   circuit = to_abstract_circuit(BellProgram())
   print(circuit.num_qubits)                # 2
   print([gate.name for gate in circuit.gates])  # ['H', 'CNOT']

使用 YAML generated operation
-----------------------------

.. code-block:: bash

   pyqres compile

.. code-block:: python

   from pyqres.core.lowering import to_abstract_circuit
   from pyqres.core.metadata import RegisterMetadata
   from pyqres.generated import QECExampleGHZ

   RegisterMetadata.get_register_metadata().declare_register("q", 4, "General")
   op = QECExampleGHZ(["q"], [4])
   circuit = to_abstract_circuit(op)

   assert [gate.name for gate in circuit.gates] == ["H", "CNOT", "CNOT", "CNOT"]

进入 QEC-Compiler
-----------------

.. code-block:: python

   from qec_compiler import QECCompiler

   compilation = QECCompiler().compile(
       circuit,
       data_block_style="intermediate",
       distance_data=3,
       distance_factory=3,
   )
   print(compilation.operation_schedule.total_cycles)

下一步阅读
----------

* :doc:`../workflow/index`：完整三项目工作流。
* :doc:`../defining_operations/yaml_dsl`：YAML DSL 示例。
* :doc:`../api/qec_intermediate_contract`：pyqres/QEC-Compiler 中间层 primitive contract。
