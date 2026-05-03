pyqres.quantikz
===============

模块概述
--------

``pyqres.quantikz`` 模块提供 Quantikz LaTeX 量子线路图生成功能。当前实现以
pyqres 的 ``Operation`` 树为主入口：visitor 会展开 composite，继承父级
controller，处理 dagger 上下文，并将 primitive/register operation 编译为
register-level Quantikz timeline。

核心类包括：

- :class:`~pyqres.quantikz.generator.QuantumCircuit` - 量子电路表示
- :class:`~pyqres.quantikz.generator.QReg` - 量子寄存器
- :class:`~pyqres.quantikz.generator.OpCode` - 操作码数据类
- :class:`~pyqres.quantikz.generator.Controller` - 控制器数据类
- :class:`~pyqres.quantikz.generator.LatexGenerator` - LaTeX 代码生成器
- :class:`~pyqres.quantikz.generator.Compiler` - LaTeX 编译器
- :class:`~pyqres.quantikz.visitor.QuantikzVisitor` - Operation 树编译 visitor

从 Operation 树生成线路图
--------------------------

从操作树生成 LaTeX 线路图：

.. code-block:: python

   from pyqres.core.metadata import RegisterMetadata
   from pyqres.primitives import Hadamard, X
   from pyqres.quantikz import QuantikzVisitor

   rm = RegisterMetadata.get_register_metadata()
   rm.declare_register("ctrl", 1)
   rm.declare_register("q", 1)

   op = X(["q"], [0]).control_by_bit([("ctrl", 0)])

   visitor = QuantikzVisitor()
   op.traverse(visitor)
   latex_code = visitor.to_latex()

``to_latex()`` 返回完整 standalone LaTeX 文档；``to_latex_figure(caption)``
返回可嵌入已有 LaTeX 文档的 ``figure`` 环境。

直接构造线路
------------

如果不从 ``Operation`` 树出发，也可以直接构造 register-level timeline：

.. code-block:: python

   from pyqres.quantikz.generator import (
       QuantumCircuit, OpCode, Controller, LatexGenerator, Compiler
   )

   circuit = QuantumCircuit({'q1': 1, 'q2': 1, 'ctrl': 1})

   circuit.add_op(OpCode(
       name='CNOT',
       targets=['q1'],
       controls=[Controller('ctrl', 'conditioned_by_all_ones')]
   ))
   circuit.add_op(OpCode(name='H', targets=['q2']))

   latex_code = LatexGenerator.generate(circuit)
   Compiler.compile(latex_code, 'my_circuit.tex')

语义说明
--------

- 输出是 register-level 线路图，不展开到单个物理 qubit wire。
- composite 会按当前 pyqres traversal 规则展开；dagger composite 会逆序遍历子操作。
- controller context 会传播到子 primitive，并渲染为 Quantikz control。
- ``SplitRegister``、``CombineRegister``、``AddRegister``、``RemoveRegister``
  等 register operation 会作为显式 register-level gate 显示。
- LaTeX 特殊字符会被转义，例如 ``_overflow`` 会渲染为 ``\_overflow``。

依赖要求
--------

- quantikz2 TikZ 库
- pdflatex（用于编译 PDF）
