YAML 定义 QEC-Compiler examples
===============================

入口文件
--------

QEC examples 的 YAML mirror 定义在：

.. code-block:: text

   pyqres/dsl/schemas/composites/qec_examples.yml

编译后生成：

.. code-block:: text

   pyqres/generated/QECExampleGHZ.py
   pyqres/generated/QECExampleW.py
   pyqres/generated/QECExampleBV.py
   ...

运行编译：

.. code-block:: bash

   cd Quantum-Resource-Estimator
   .venv/bin/pyqres compile
   .venv/bin/pyqres check

核心机制：QECGate
-----------------

``QECGate`` 是 compiler-only adapter。YAML helper 使用它直接发出 QEC-Compiler
``AbstractGate``：

.. code-block:: python

   QECGate(
       reg_list=["q"],
       param_list=["CNOT", [0, 1], []],
   )

含义是：在寄存器 ``q`` 的 bit 0 和 bit 1 上发出 QEC gate ``CNOT``。

``QECGate`` 的约束：

* 只用于 ``AbstractCircuit`` emission。
* ``pyqsparse_object()`` 抛 ``NotImplementedError``。
* ``t_count()`` 抛 ``NotImplementedError``。
* 不代表 register-level algorithm primitive。

示例：GHZ
---------

.. code-block:: yaml

   - name: QECExampleGHZ
     description: "YAML mirror of QEC-Compiler GHZ benchmark gates"
     qregs:
       - {name: q, type: General}
     params:
       - {name: n, type: int}
     impl:
       - python: |
           from ..algorithms.qec_examples import build_qec_ghz
       - python: |
           build_qec_ghz(self.program_list, self.q, self.n)

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
       - python: |
           from ..algorithms.qec_examples import build_qec_qft
       - python: |
           build_qec_qft(self.program_list, self.q, self.n)

Python 使用：

.. code-block:: python

   from pyqres.generated import QECExampleQFT

   RegisterMetadata.get_register_metadata().declare_register("q", 4, "General")
   qft = QECExampleQFT(["q"], [4])
   circuit = to_abstract_circuit(qft)

QEC-Compiler builder parity 测试逐门比较 ``H``、``CPHASE``、``SWAP`` 的顺序、参数和 qubit order。

示例：QAOA
----------

.. code-block:: yaml

   - name: QECExampleQAOA
     qregs:
       - {name: q, type: General}
     params:
       - {name: n_vertices, type: int}
       - {name: edges, type: array}
       - {name: p, type: int}
       - {name: gamma, type: float}
       - {name: beta, type: float}
     impl:
       - python: |
           from ..algorithms.qec_examples import build_qec_qaoa
       - python: |
           build_qec_qaoa(
               self.program_list, self.q, self.n_vertices, self.edges,
               self.p, self.gamma, self.beta)

Python 使用：

.. code-block:: python

   import math
   from pyqres.generated import QECExampleQAOA

   edges = [(0, 1), (1, 2), (2, 3)]
   RegisterMetadata.get_register_metadata().declare_register("q", 4, "General")
   op = QECExampleQAOA(["q"], [4, edges, 1, math.pi / 4, math.pi / 8])
   circuit = to_abstract_circuit(op)

示例：small Shor fixture
-----------------------

.. code-block:: yaml

   - name: QECExampleSmallShor
     qregs:
       - {name: q, type: General}
     params:
       - {name: modulus, type: int}
       - {name: base, type: int}
     impl:
       - python: |
           from ..algorithms.qec_examples import build_qec_small_shor
       - python: |
           build_qec_small_shor(self.program_list, self.q, self.modulus, self.base)

当前支持 ``N=15`` 和 ``N=21``，与 QEC-Compiler stage-5 small Shor fixture 对齐。

验证命令
--------

.. code-block:: bash

   PYTHONPATH=../QEC-compiler/src:. .venv/bin/pytest \
     tests/test_qec_examples_yaml.py -q

该测试覆盖：

.. code-block:: text

   GHZ, W, BV, DJ, Grover, QFT, QPE, QAOA, VQE, Ising, SWAP-test, small Shor
