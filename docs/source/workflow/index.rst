pyqres -> PySparQ -> QEC-Compiler 联合工作流
=============================================

本章是 Quantum-Resource-Estimator 当前最重要的使用路径：以 pyqres YAML DSL
和 Operation tree 作为算法入口，先在 PySparQ 中做 register-level 语义验证，
再 lowering 到 QEC-Compiler 的 ``AbstractCircuit``，最终进入 QEC 编译和资源计算。

.. toctree::
   :maxdepth: 1

   philosophy
   installation
   full_pipeline
   supported_algorithms
   yaml_qec_examples
   qda_tridiagonal
   qram_status
