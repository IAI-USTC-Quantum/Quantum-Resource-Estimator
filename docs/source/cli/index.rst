命令行工具
==========

Quantum-Resource-Estimator 提供 ``pyqres`` 命令行工具，用于编译 YAML DSL、检查 schema
依赖、查看 operation tree 和运行 coarse resource estimation。

compile
-------

编译 YAML composite schema 生成 Python 类：

.. code-block:: bash

   # 编译默认 schemas 到 pyqres/generated/
   pyqres compile

   # 指定源和输出路径
   pyqres compile --source pyqres/dsl/schemas/composites/qec_examples.yml --output /tmp/generated

默认会读取：

.. code-block:: text

   pyqres/dsl/schemas/composites/

生成文件写入：

.. code-block:: text

   pyqres/generated/

当前内置 schema 包括基础 composite、Grover/QPE/QDA/Shor 等算法，以及
``QECExample*`` benchmark mirrors。

check
-----

检查操作定义完整性：

.. code-block:: bash

   pyqres check

检查内容包括：

* operation 引用是否存在。
* qreg/param/controller 引用是否在当前 schema 中声明。
* composite 依赖覆盖情况。

show
----

显示 operation 依赖树：

.. code-block:: bash

   pyqres show Swap --depth 3
   pyqres show QECExampleQFT --depth 2
   pyqres show QDALinearSolver --depth 3

``QECExample*`` 类通过 YAML loops/conditions 调用 QEC IR primitives 生成 gate
sequence，因此 dependency tree 可以显示这些 primitive 依赖。

estimate
--------

估计操作的 coarse resource：

.. code-block:: bash

   pyqres estimate Toffoli
   pyqres estimate Toffoli -m t_depth
   pyqres estimate Add_UInt_UInt -r a:4,b:4,c:4

参数说明：

* ``operation``：操作名称，必须存在于 ``OperationRegistry``。
* ``-r, --registers``：寄存器定义，格式为 ``name:size,name:size,...``。
* ``-p, --params``：参数定义，格式为 ``name:value,name:value,...``。
* ``-m, --metric``：资源指标，支持 ``t_count``、``t_depth``、``toffoli_count``。

注意：部分 QEC IR primitives 只定义 ``AbstractCircuit`` lowering，不提供
pyqres-local resource estimator 语义；QRAM 当前显式 ``NotImplementedError``。

QEC examples mirror 工作流
-------------------------

.. code-block:: bash

   pyqres compile
   pyqres check
   PYTHONPATH=../QEC-compiler/src:. .venv/bin/pytest tests/test_qec_examples_yaml.py -q

该测试验证 YAML-generated ``QECExample*`` 类能生成与 QEC-Compiler benchmark builders
逐门一致的 ``AbstractCircuit``。
