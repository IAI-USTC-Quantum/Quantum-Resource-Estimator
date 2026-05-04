三项目源码安装
==============

推荐在同一父目录下并列放置三个项目：

.. code-block:: text

   connect-pysparq-pyqres-qecc/
      Quantum-Resource-Estimator/
      QRAM-Simulator/
      QEC-compiler/

安装 PySparQ
------------

PySparQ 来自 QRAM-Simulator，是 pyqres simulation visitor 的运行时依赖。

.. code-block:: bash

   cd QRAM-Simulator
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .

如果需要构建 C++ 测试：

.. code-block:: bash

   cd QRAM-Simulator
   mkdir -p build
   cd build
   cmake .. -DCMAKE_BUILD_TYPE=Release
   make -j$(nproc)
   ctest --output-on-failure

当前 GPU/CUDA 后端不是 pyqres/QEC 联调主线，默认按 CPU-only 使用。

安装 QEC-Compiler
-----------------

QEC-Compiler 使用 ``uv`` 管理开发环境：

.. code-block:: bash

   cd QEC-compiler
   uv venv
   source .venv/bin/activate
   uv sync --all-extras
   uv run qec-compile --version

安装 pyqres
------------

.. code-block:: bash

   cd Quantum-Resource-Estimator
   python -m venv .venv
   source .venv/bin/activate
   pip install -e ".[test]"

跨项目导入 QEC-Compiler
-----------------------

如果 QEC-Compiler 没有安装成 site-package，可在运行 pyqres QEC 测试或脚本时指定：

.. code-block:: bash

   cd Quantum-Resource-Estimator
   PYTHONPATH=../QEC-compiler/src:. .venv/bin/python your_script.py

常用联调命令
------------

.. code-block:: bash

   cd Quantum-Resource-Estimator
   .venv/bin/pyqres compile
   .venv/bin/pyqres check
   PYTHONPATH=../QEC-compiler/src:. .venv/bin/pytest \
     tests/test_qec_examples_yaml.py \
     tests/test_qec_lowering.py \
     tests/test_intermediate_semantics.py \
     tests/test_qram_unimplemented.py -q

   cd ../QEC-compiler
   .venv/bin/python -m pytest \
     tests/test_arithmetic_decomposition.py \
     tests/test_arithmetic_truth_table.py -q
