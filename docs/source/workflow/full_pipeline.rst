完整调用链路
============

本页给出从 pyqres 程序到 QEC-Compiler ``AbstractCircuit`` 的最小可复用模式。

声明寄存器
----------

pyqres lowering 和 simulation 都依赖 ``RegisterMetadata``：

.. code-block:: python

   from pyqres.core.metadata import RegisterMetadata

   rm = RegisterMetadata.get_register_metadata()
   rm.declare_register("q0", 1, "Boolean")
   rm.declare_register("q1", 1, "Boolean")

构造 Operation tree
-------------------

.. code-block:: python

   from pyqres.primitives import Hadamard, CNOT

   class BellProgram:
       def __init__(self):
           self.program_list = [
               Hadamard(["q0"]),
               CNOT(["q0", "q1"], [0, 0]),
           ]

       def traverse(self, visitor, dagger_ctx=False, controllers_ctx=None):
           for op in self.program_list:
               op.traverse(visitor, dagger_ctx, controllers_ctx or {})

   program = BellProgram()

PySparQ simulation smoke
------------------------

.. code-block:: python

   import pysparq as ps
   from pyqres.core.simulator import SimulatorVisitor

   sim = SimulatorVisitor()
   program.traverse(sim)
   print(ps.StatePrint(sim.state, ps.StatePrintDisplay.Detail))

lower 到 AbstractCircuit
------------------------

.. code-block:: python

   from pyqres.core.lowering import to_abstract_circuit
   from qec_compiler.ir import emit_ir_json

   circuit = to_abstract_circuit(program)
   print(circuit.num_qubits)
   print([gate.name for gate in circuit.gates])
   open("circuit.ir.json", "w", encoding="utf-8").write(emit_ir_json(circuit))

进入 QEC-Compiler
-----------------

.. code-block:: python

   from qec_compiler import QECCompiler
   from qec_compiler.output import emit_qeol_json

   compilation = QECCompiler().compile(
       circuit,
       data_block_style="intermediate",
       distance_data=3,
       distance_factory=3,
   )
   open("qeol.json", "w", encoding="utf-8").write(
       emit_qeol_json(compilation.qeol_program)
   )

也可以通过 CLI 编译：

.. code-block:: bash

   cd QEC-compiler
   MPLCONFIGDIR=/tmp .venv/bin/qec-compile \
     ../Quantum-Resource-Estimator/circuit.ir.json \
     --style intermediate \
     --d 3 \
     --d-fac 3 \
     --out-dir runs/pyqres_demo

输出目录包含 ``logical_circuit.ir.json``、``surgery_graph.ir.json``、
``layout_plan.ir.json``、``operation_schedule.ir.json``、``space_time_schedule.ir.json``、
``qeol.json`` 等 QEC artifacts。
