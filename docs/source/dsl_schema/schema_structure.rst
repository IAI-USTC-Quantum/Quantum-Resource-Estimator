YAML Schema 结构
================

本页描述当前 composite YAML schema。primitive set YAML 仅用于 primitive registry/coverage，
实际 primitive 行为由 ``pyqres.primitives`` 中的 Python 类实现。

顶层字段
--------

.. list-table::
   :widths: 22 14 64
   :header-rows: 1

   * - 字段
     - 必选
     - 说明
   * - ``name``
     - 是
     - 生成的 Python 类名，建议 PascalCase。
   * - ``description``
     - 否
     - 文档说明，进入生成类 docstring。
   * - ``qregs``
     - 否但常用
     - 量子寄存器声明，生成 ``self.<name>`` 属性。
   * - ``params``
     - 否
     - 经典参数声明，生成 ``self.<name>`` 属性。
   * - ``temp_regs``
     - 否
     - 临时寄存器，Operation enter/exit 时自动声明和移除。
   * - ``computed_params``
     - 否
     - 从参数计算派生属性。
   * - ``impl``
     - 是
     - 子操作和控制结构列表。
   * - ``self_conjugate``
     - 否
     - 标记 operation 是否自伴。
   * - ``control_override``
     - 否
     - 特殊控制传播逻辑，如 ``cnot_swap``。
   * - ``sum_t_count_formula``
     - 否
     - ``custom`` 时生成 ``AbstractComposite``，由手写逻辑补充资源聚合。

寄存器声明
----------

.. code-block:: yaml

   qregs:
     - {name: main, type: UnsignedInteger, desc: "Main index register"}
     - {name: flag, type: Boolean}

   temp_regs:
     - {name: overflow, size: 1}
     - {name: scratch, size: 4}

支持的 register type：

* ``General``
* ``UnsignedInteger``
* ``SignedInteger``
* ``Boolean``
* ``Rational``

参数声明
--------

.. code-block:: yaml

   params:
     - {name: n, type: int}
     - {name: epsilon, type: float}
     - {name: edges, type: array}
     - {name: encode_A, type: operation}

支持的 param type：

* ``int`` / ``float`` / ``symbol`` / ``str`` / ``bool``
* ``array`` / ``list`` / ``object``
* ``callable`` / ``operation`` / ``op_instance``
* ``qram`` / ``qram_ref``，当前仅保留 schema 能力；pyqres QRAM primitive 暂不支持。

impl: 普通 operation call
------------------------

.. code-block:: yaml

   impl:
     - op: Hadamard_NDigits
       qregs: [search_reg]
       params: [n_qubits]

     - op: CNOT
       qregs: [control, target]
       params: [0, 0]

``qregs`` 引用当前 ``qregs``、``temp_regs`` 或 ``computed_params`` 中声明的名字。
``params`` 中的字符串如果匹配参数名，会生成 ``self.<param>``。

impl: loop
----------

.. code-block:: yaml

   - loop:
       iterations: n_steps
       body:
         - op: X
           qregs: [main]
           params: [0]

生成：

.. code-block:: python

   for i in range(self.n_steps):
       ...

impl: for_each
--------------

.. code-block:: yaml

   - for_each:
       var: i
       items: n_qubits
       body:
         - op: X
           qregs: [search_reg]
           params: [$i]

如果 ``items`` 是 int 参数，生成 ``range(self.n_qubits)``。如果是 array/list 参数，直接遍历。

impl: if / elif / else
---------------------

.. code-block:: yaml

   - if:
       condition: self.beta < 0
       body:
         - op: Reflection_Bool
           qregs: [main]
           params: [False]
       else:
         - op: Hadamard
           qregs: [main]

condition 是 Python 表达式，生成代码时原样进入方法体。

controllers
-----------

.. code-block:: yaml

   controllers:
     all_ones: [ctrl]
     bit: [[selector, 0]]
     value: [[selector, 2]]

支持 controller 类型：

* ``all_ones``
* ``nonzero``
* ``bit``
* ``value``

QEC lowering 对 controller 的支持范围小于 PySparQ；不支持的 controller 应显式报错。

python block
------------

.. code-block:: yaml

   - python: |
       if self.encode_A:
           self.program_list.append(self.encode_A)

只有 import-only block 会被 codegen 提升到生成文件顶部；非 import 代码会进入 ``_build_execute_method``。

QEC IR primitive 参数结构
------------------------

QEC examples mirror 使用显式 primitive，而不是任意 gate adapter。

.. code-block:: python

   RZ(reg_list=["q"], param_list=[2, 0.125])
   CPHASE(reg_list=["q"], param_list=[0, 1, 0.25])

分别发出：

.. code-block:: python

   AbstractGate(name="RZ", qubits=(2,), params=(0.125,))
   AbstractGate(name="CPHASE", qubits=(0, 1), params=(0.25,))

它没有 PySparQ reference，也没有 pyqres resource estimator 语义。
