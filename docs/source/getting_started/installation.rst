安装
====

单项目安装
----------

.. code-block:: bash

   git clone https://github.com/IAI-USTC-Quantum/Quantum-Resource-Estimator.git
   cd Quantum-Resource-Estimator
   python -m venv .venv
   source .venv/bin/activate
   pip install -e ".[test]"

``pysparq`` 是 pyqres 的依赖，用于 ``SimulatorVisitor``。如果需要运行 QEC integration，
还需要让 ``qec_compiler`` 可导入。

三项目联合安装
--------------

推荐目录结构：

.. code-block:: text

   connect-pysparq-pyqres-qecc/
      Quantum-Resource-Estimator/
      QRAM-Simulator/
      QEC-compiler/

QEC-Compiler 使用 ``uv``：

.. code-block:: bash

   cd QEC-compiler
   uv venv
   source .venv/bin/activate
   uv sync --all-extras

pyqres 调用本地 QEC-Compiler 源码：

.. code-block:: bash

   cd Quantum-Resource-Estimator
   PYTHONPATH=../QEC-compiler/src:. .venv/bin/python your_script.py

验证安装
--------

.. code-block:: bash

   cd Quantum-Resource-Estimator
   .venv/bin/pyqres compile
   .venv/bin/pyqres check

   PYTHONPATH=../QEC-compiler/src:. .venv/bin/pytest \
     tests/test_qec_examples_yaml.py \
     tests/test_qec_lowering.py \
     tests/test_intermediate_semantics.py \
     tests/test_qram_unimplemented.py -q
