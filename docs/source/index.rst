Quantum-Resource-Estimator (pyqres) 文档
========================================

Quantum-Resource-Estimator 是一个 register-level 量子算法编程、模拟、资源估计和
QEC 编译对接工具。当前主线是把 pyqres 作为算法 authoring layer：算法先写成 YAML DSL
或 Python ``Operation`` tree，再用 PySparQ 做小规模语义验证，最后 lowering 到
QEC-Compiler ``AbstractCircuit``，进入 QEC-level schedule/QEOL 资源计算。

核心链路：

.. code-block:: text

   YAML DSL / Python Operation tree
      -> PySparQ simulation when supported
      -> pyqres QEC lowering
      -> QEC-Compiler AbstractCircuit
      -> logical lowering / lattice surgery / QEOL

.. toctree::
   :maxdepth: 2
   :caption: 快速开始

   getting_started/index

.. toctree::
   :maxdepth: 2
   :caption: 联合工作流

   workflow/index

.. toctree::
   :maxdepth: 2
   :caption: 核心概念

   core_concepts/index

.. toctree::
   :maxdepth: 2
   :caption: 定义操作

   defining_operations/index

.. toctree::
   :maxdepth: 2
   :caption: 资源估计

   resource_estimation/index

.. toctree::
   :maxdepth: 2
   :caption: QEC 集成

   qec_integration

.. toctree::
   :maxdepth: 2
   :caption: 模拟与可视化

   simulation/index
   visualization/index

.. toctree::
   :maxdepth: 2
   :caption: 命令行工具

   cli/index

.. toctree::
   :maxdepth: 2
   :caption: API 参考

   api/index

.. toctree::
   :maxdepth: 2
   :caption: DSL Schema 参考

   dsl_schema/index

索引与搜索
==========

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
