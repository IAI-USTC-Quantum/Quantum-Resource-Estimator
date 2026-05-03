Visualization
=============

Interactive HTML
----------------

``pyqres.visualization`` can write standalone HTML files for an already
constructed operation object.  The files contain inline CSS and JavaScript, so
they can be opened directly in a browser without running a local server.

The call-tree view renders every operation node as expandable ``details``
elements and shows registers, parameters, controllers, dagger state, and
submodules.

The circuit view renders a register-level timeline.  The sidebar lets you
switch between call-tree and circuit views, choose a maximum expansion depth,
and select specific composite module instances to expand.  Depth ``0`` keeps
the root module collapsed, depth ``1`` expands one module level, and each
larger value expands one more level.  Changing these controls redraws the
circuit in the browser.

.. code-block:: python

   from pyqres.core.metadata import RegisterMetadata
   from pyqres.algorithms.block_encoding import BlockEncodingTridiagonal
   from pyqres.visualization import write_call_tree_html, write_circuit_html

   rm = RegisterMetadata.get_register_metadata()
   rm.declare_register("main", 2, "UnsignedInteger")
   rm.declare_register("anc_UA", 4, "UnsignedInteger")

   op = BlockEncodingTridiagonal(
       main_reg="main",
       anc_UA="anc_UA",
       alpha=0.5,
       beta=0.3,
   )

   write_call_tree_html(op, "block_encoding_tree.html")
   write_circuit_html(op, "block_encoding_circuit.html")

There is also a small QDA-Tridiagonal example:

.. code-block:: bash

   python examples/qda_tridiagonal_visualization.py

It writes:

- ``visualizations/qda_tridiagonal_tree.html``
- ``visualizations/qda_tridiagonal_circuit.html``

API
---

.. autofunction:: pyqres.visualization.operation_to_tree_data
.. autofunction:: pyqres.visualization.render_call_tree_html
.. autofunction:: pyqres.visualization.render_circuit_html
.. autofunction:: pyqres.visualization.write_call_tree_html
.. autofunction:: pyqres.visualization.write_circuit_html


Quantikz 线路图
---------------

Quantum-Resource-Estimator 支持使用 Quantikz LaTeX 包生成量子线路图。

生成线路图
~~~~~~~~~~

.. code-block:: python

   from pyqres.quantikz import QuantumCircuit

   # 创建线路图
   circuit = QuantumCircuit()
   # ... 添加操作

   # 生成 LaTeX
   latex = circuit.to_latex()

依赖
~~~~

- LaTeX 系统（需安装 ``pdflatex``）
- ``quantikz2`` LaTeX 包
