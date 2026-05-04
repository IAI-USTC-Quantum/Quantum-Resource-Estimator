支持的量子算法与当前状态
========================

pyqres 中算法分为三类：

* YAML DSL 定义并生成到 ``pyqres.generated`` 的 composite。
* ``pyqres.algorithms`` 中手写的复杂算法模块。
* 为 QEC-Compiler examples 做 gate-level parity 的 YAML mirror。

当前支持矩阵
------------

.. list-table::
   :widths: 24 24 24 28
   :header-rows: 1

   * - 算法/家族
     - pyqres 表达方式
     - QEC AbstractCircuit
     - 说明
   * - GHZ / W state
     - YAML mirror ``QECExampleGHZ`` / ``QECExampleW``
     - 已逐门匹配 QEC-Compiler builder
     - 用于 state-prep benchmark parity。
   * - Bernstein-Vazirani
     - YAML mirror ``QECExampleBV``
     - 已逐门匹配
     - 覆盖 oracle CNOT 结构。
   * - Deutsch-Jozsa
     - YAML mirror ``QECExampleDJ``
     - 已逐门匹配
     - 覆盖 balanced/constant oracle gate pattern。
   * - Grover
     - YAML mirror ``QECExampleGrover`` 和已有 ``GroverSearch``
     - mirror 已逐门匹配
     - ``GroverSearch`` 是更高层 DSL 算法；mirror 用于 QEC examples parity。
   * - QFT / QPE
     - YAML mirror ``QECExampleQFT`` / ``QECExampleQPE``
     - 已逐门匹配
     - 覆盖 ``H``、``CPHASE``、``SWAP``。
   * - QAOA / VQE / Ising
     - YAML mirror
     - 已逐门匹配
     - 覆盖 rotation-heavy benchmark。
   * - SWAP-test
     - YAML mirror ``QECExampleSwapTest``
     - 已逐门匹配
     - 覆盖 Fredkin/CCX-style 结构。
   * - small Shor fixture
     - YAML mirror ``QECExampleSmallShor`` 和 hand-written Shor
     - 已逐门匹配 QEC fixture；pyqres Shor 可 lower
     - ``CMUL_MOD_N`` 是 legacy compatibility gate。
   * - QDA-tridiagonal
     - hand-written ``BlockEncodingTridiagonal`` + generated ``QDALinearSolver``
     - 多尺寸 smoke 已通过
     - 当前测试覆盖 ``main_bits = 1, 2, 3``。
   * - QRAM-based algorithms
     - YAML/hand-written definitions may import QRAM wrappers
     - 暂不支持
     - QRAM wrappers 显式抛 ``NotImplementedError``。

为什么有 YAML mirror
-------------------

QEC-Compiler 的 curated examples 原本直接构造 ``AbstractCircuit``。为了验证
“pyqres YAML DSL -> generated Python -> AbstractCircuit”这一步，pyqres 提供一组
``QECExample*`` YAML mirror。它们通过显式 QEC IR primitives 发出与
QEC-Compiler builder 完全相同的 gate name、qubit order 和 params。

这条路径的目的很明确：

* 证明 YAML DSL 可以承载 QEC examples 的 gate-level 工作流。
* 避免把 measurement/metadata 和 PySparQ reference 混在一起。
* 为后续把 gate-level mirror 逐步提升为 register-level algorithm 提供回归基线。

限制
----

* 当前 parity 测试比较 ``num_qubits``、``gates``、``qubits``、``params``。
* pyqres QEC lowering 目前不表达 QEC-Compiler examples 的 measurements 和 metadata。
* 部分 QEC IR primitives 只定义 ``AbstractCircuit`` lowering；资源统计交给 QEC-Compiler。
