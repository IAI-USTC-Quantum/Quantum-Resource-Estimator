QDA-tridiagonal 工作流
======================

QDA-tridiagonal 是当前 pyqres 中最重要的 register-level 算法工作流之一。
它不使用 QRAM，而是通过 ``BlockEncodingTridiagonal`` 编码三对角矩阵。

组件
----

``BlockEncodingTridiagonal``
    手写 Python composite，位于 ``pyqres.algorithms.block_encoding``。
    它使用 ``SplitRegister``、``Rot_GeneralStatePrep``、``PlusOneOverflow``、
    ``Reflection_Bool`` 等 primitive 构造三对角矩阵 block encoding。

``WalkS_Primitive``
    手写 QDA walk operator，位于 ``pyqres.algorithms.qda_solver``。

``QDALinearSolver``
    YAML 生成的 composite，位于 ``pyqres.generated``。
    它接收 ``encode_A`` / ``encode_b`` operation 参数，并在 adiabatic steps 中调用 ``WalkS_Primitive``。

最小 QEC lowering 示例
----------------------

.. code-block:: python

   from pyqres.algorithms.block_encoding import BlockEncodingTridiagonal
   from pyqres.core.lowering import to_abstract_circuit
   from pyqres.core.metadata import RegisterMetadata
   from pyqres.generated import QDALinearSolver

   rm = RegisterMetadata.get_register_metadata()
   rm.declare_register("main", 2, "UnsignedInteger")
   rm.declare_register("anc_UA", 4, "UnsignedInteger")
   rm.declare_register("anc_1", 1, "Boolean")
   rm.declare_register("anc_2", 1, "Boolean")
   rm.declare_register("anc_3", 1, "Boolean")
   rm.declare_register("anc_4", 1, "Boolean")

   def make_enc_A(reg_list=None, param_list=None):
       return BlockEncodingTridiagonal(
           reg_list=reg_list,
           main_reg=reg_list[0],
           anc_UA=reg_list[1],
           alpha=0.5,
           beta=0.3,
       )

   op = QDALinearSolver(
       reg_list=["main", "anc_UA", "anc_1", "anc_2", "anc_3", "anc_4"],
       param_list=[2.0, 1.0],
       operations=[make_enc_A],
   )
   circuit = to_abstract_circuit(op)

矩阵尺寸
--------

``main`` register 的 bit 数决定矩阵维度：

.. list-table::
   :widths: 20 20 60
   :header-rows: 1

   * - ``main_bits``
     - 矩阵维度
     - 当前测试状态
   * - 1
     - 2 x 2
     - 可自动 lowering 到 ``AbstractCircuit`` 并进入 ``lower_to_logical``。
   * - 2
     - 4 x 4
     - 可自动 lowering 到 ``AbstractCircuit`` 并进入 ``lower_to_logical``。
   * - 3
     - 8 x 8
     - 可自动 lowering 到 ``AbstractCircuit`` 并进入 ``lower_to_logical``。

验证命令
--------

.. code-block:: bash

   PYTHONPATH=../QEC-compiler/src:. .venv/bin/pytest \
     tests/test_qec_lowering.py -q

相关测试包括：

* ``test_walks_with_tridiagonal_compiles``
* ``test_generated_qda_tridiagonal_lowers_for_matrix_sizes``
* ``test_block_encoding_tridiagonal_produces_gates``

注意事项
--------

* 当前 QDA-tridiagonal 测试是 compile/lowering smoke，不等价于完整 QDA 数值正确性证明。
* ``encode_b`` 如果未传入，会走 ``WalkS_Primitive`` 的 Hadamard fallback。
* QRAM-based QDA 当前不属于支持路径。
