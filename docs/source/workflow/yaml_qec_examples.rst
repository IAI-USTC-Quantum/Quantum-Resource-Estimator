YAML 定义 QEC-Compiler examples
===============================

入口文件
--------

QEC examples 的 YAML 定义在：

.. code-block:: text

   pyqres/dsl/schemas/composites/qec_examples.yml

编译后生成 ``pyqres/generated/QECExample*.py``。运行：

.. code-block:: bash

   cd Quantum-Resource-Estimator
   .venv/bin/pyqres compile
   .venv/bin/pyqres check

核心机制：QEC IR primitives
--------------------------

这些 YAML examples 直接调用 QEC-Compiler 认识的 primitive，而不是 import Python
builder 或通过任意 gate adapter 注入 payload。

可用的 QEC-facing primitives 包括：

.. code-block:: text

   H, X, Y, Z, CNOT, SWAP, CPHASE, RX, RY, RZ, CCX
   ADD, MOD_ADD, MOD_MUL, CMUL_MOD_N, MCX, PLUS_ONE, REFLECT

示例：GHZ
---------

.. code-block:: yaml

   - name: QECExampleGHZ
     qregs:
       - {name: q, type: General}
     params:
       - {name: n, type: int}
     impl:
       - op: H
         qregs: [q]
         params: [0]
       - for_each:
           var: i
           items: {type: expr, value: "range(n - 1)"}
           body:
             - op: CNOT
               qregs: [q, q]
               params: [$i, {type: expr, value: "i + 1"}]

使用：

.. code-block:: python

   from pyqres.core.metadata import RegisterMetadata
   from pyqres.core.lowering import to_abstract_circuit
   from pyqres.generated import QECExampleGHZ

   RegisterMetadata.get_register_metadata().declare_register("q", 4, "General")
   op = QECExampleGHZ(["q"], [4])
   circuit = to_abstract_circuit(op)

   assert [gate.name for gate in circuit.gates] == ["H", "CNOT", "CNOT", "CNOT"]

示例：QFT
---------

.. code-block:: yaml

   - name: QECExampleQFT
     qregs:
       - {name: q, type: General}
     params:
       - {name: n, type: int}
     impl:
       - for_each:
           var: i
           items: n
           body:
             - op: H
               qregs: [q]
               params: [$i]
             - for_each:
                 var: j
                 items: {type: expr, value: "range(i + 1, n)"}
                 body:
                   - op: CPHASE
                     qregs: [q]
                     params: [$i, $j, {type: expr, value: "math.pi / (1 << (j - i))"}]

验证命令
--------

.. code-block:: bash

   PYTHONPATH=../QEC-compiler/src:. .venv/bin/pytest \
     tests/test_qec_examples_yaml.py -q

该测试覆盖：

.. code-block:: text

   GHZ, W, BV, DJ, Grover, QFT, QPE, QAOA, VQE, Ising, SWAP-test, small Shor
