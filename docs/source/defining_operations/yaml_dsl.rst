YAML DSL
========

pyqres YAML DSL 用于定义 ``Composite`` operation。编译器读取 YAML schema，验证依赖，
生成 Python 类到 ``pyqres.generated``，然后这些类可以像手写 ``Operation`` 一样参与
simulation、resource estimation、visualization 和 QEC lowering。

当前 DSL 是 composite-first：primitive 的 Python 实现位于 ``pyqres.primitives``，
YAML 负责组合 primitive、控制流程、参数化和少量 Python glue code。

基本流程
--------

.. code-block:: text

   YAML composite schema
      -> SchemaValidator
      -> CodeGenerator
      -> pyqres/generated/*.py
      -> OperationRegistry auto registration
      -> Operation tree traversal

常用命令：

.. code-block:: bash

   pyqres compile
   pyqres check
   pyqres show Swap --depth 3

最小示例：Swap
--------------

.. code-block:: yaml

   - name: Swap
     description: "Swap two registers via 3 CNOTs"
     qregs:
       - {name: reg1, type: General}
       - {name: reg2, type: General}
     impl:
       - op: CNOT
         qregs: [reg1, reg2]
       - op: CNOT
         qregs: [reg2, reg1]
       - op: CNOT
         qregs: [reg1, reg2]
     control_override: cnot_swap
     self_conjugate: true

使用生成类：

.. code-block:: python

   from pyqres.core.metadata import RegisterMetadata
   from pyqres.generated import Swap

   rm = RegisterMetadata.get_register_metadata()
   rm.declare_register("a", 1, "Boolean")
   rm.declare_register("b", 1, "Boolean")

   op = Swap(["a", "b"])

循环示例：Grover diffusion 片段
------------------------------

.. code-block:: yaml

   - comment: "Diffusion: X on all qubits"
     for_each:
       var: i
       items: n_qubits
       body:
         - op: X
           qregs: [search_reg]
           params: [$i]

``for_each.items`` 如果引用 ``int`` 参数，会生成 ``range(self.n_qubits)``；如果引用
``array`` 参数，会直接遍历该数组。

控制和 dagger
-------------

.. code-block:: yaml

   impl:
     - op: PlusOneOverflow
       qregs: [main, overflow]
       params: [1]
       controllers:
         value: [[selector, 1]]

     - op: Rot_GeneralStatePrep
       qregs: [anc]
       params: [prep_state]
       dagger: true

支持的 controller 类型：

* ``all_ones: [reg]``
* ``nonzero: [reg]``
* ``bit: [[reg, index]]``
* ``value: [[reg, value]]``

QEC lowering 当前只完整支持一部分 controller 语义；不支持的路径应 fail closed。

computed_params
---------------

.. code-block:: yaml

   computed_params:
     - name: p
       formula: "0.5"
     - name: n_steps
       formula: "int(math.ceil(math.log(kappa / epsilon)))"

生成类会把这些公式编译到 ``__init__`` 中，成为 ``self.p``、``self.n_steps``。

inline Python blocks
--------------------

复杂算法可以使用 ``python`` block 注入少量 glue code。典型用途：导入 helper，或把
operation 参数转换成 submodule 调用。

.. code-block:: yaml

   impl:
     - python: |
         from ..algorithms.qda_solver import compute_fs, WalkS_Primitive

     - loop:
         iterations: n_steps
         body:
           - python: |
               s = i / max(1, self.n_steps - 1) if self.n_steps > 1 else 1.0
               fs = compute_fs(s, self.kappa, self.p)
               self.program_list.append(
                   WalkS_Primitive(
                       reg_list=[self.main_reg, self.anc_UA, self.anc_1,
                                 self.anc_2, self.anc_3, self.anc_4],
                       param_list=[fs],
                       submodules=[op for op in [self.encode_A, self.encode_b] if op]))

inline Python 是 escape hatch。应优先用 YAML ``impl``、``loop``、``for_each`` 表达结构，
只有在算法生成逻辑确实超过 DSL 表达力时再使用。

QEC-Compiler examples YAML mirror
---------------------------------

为了验证 pyqres YAML DSL 能生成 QEC-Compiler examples 的正确 ``AbstractCircuit``，
项目提供 ``QECExample*`` 系列：

.. code-block:: text

   pyqres/dsl/schemas/composites/qec_examples.yml

这些 YAML 类通过显式 QEC IR primitives 精确发出 QEC gate：

.. code-block:: python

   CPHASE(reg_list=["q"], param_list=[0, 1, theta])

示例：QFT mirror

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

使用：

.. code-block:: python

   from pyqres.core.lowering import to_abstract_circuit
   from pyqres.core.metadata import RegisterMetadata
   from pyqres.generated import QECExampleQFT

   RegisterMetadata.get_register_metadata().declare_register("q", 4, "General")
   circuit = to_abstract_circuit(QECExampleQFT(["q"], [4]))

当前 mirror 覆盖 GHZ、W、BV、DJ、Grover、QFT、QPE、QAOA、VQE、Ising、SWAP-test、small Shor。

注意：部分 QEC IR primitives 只定义 ``AbstractCircuit`` lowering；完整资源统计由
QEC-Compiler 后续 lowering pipeline 负责。

文件组织建议
------------

* 通用 composite 放在 ``pyqres/dsl/schemas/composites/``。
* 可复用算法 helper 放在 ``pyqres/algorithms/``。
* primitive Python 实现放在 ``pyqres/primitives/``。
* 生成代码只由 ``pyqres compile`` 更新，不手工编辑 ``pyqres/generated/*.py``。
