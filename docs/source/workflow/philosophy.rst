设计哲学：从算法实现到 QEC 资源计算
====================================

Quantum-Resource-Estimator 当前的定位不是单纯统计 T-count 或 Toffoli-count。
它是一个量子算法 authoring layer，目标是把算法程序逐步推进到 QEC 编译器：

.. code-block:: text

   pyqres YAML DSL
      -> generated Python Composite
      -> pyqres Operation tree
      -> PySparQ register-level simulation
      -> pyqres QEC lowering
      -> QEC-Compiler AbstractCircuit
      -> logical lowering / layout / schedule
      -> QEOL JSON and QEC-level resource artifacts

三个项目的职责边界
------------------

``Quantum-Resource-Estimator`` / ``pyqres``
    算法入口。负责 YAML DSL、Operation tree、visitor、coarse resource estimator、
    PySparQ simulation visitor、QEC lowering 和 intermediate primitive contract。

``QRAM-Simulator`` / ``PySparQ``
    语义虚拟机。负责 register-level sparse-state simulation，用于小规模算法和 primitive
    的 correctness smoke/reference。PySparQ reference 必须语义等价；没有等价 reference
    时必须抛 ``NotImplementedError``，不能用近似 primitive 冒充。

``QEC-Compiler``
    QEC 编译器。接收 ``AbstractCircuit``，执行 arithmetic/MCX/CCZ/Pauli-product lowering、
    lattice-surgery layout、schedule 和 QEOL 输出。

工程原则
--------

* pyqres 程序保持 register-level 结构，不强迫用户手写底层门序列。
* QEC lowering 必须 fail closed：未知 primitive 抛 ``UnsupportedQECPrimitive``。
* controlled/dagger 语义必须显式进入 QEC gate name 或显式拒绝。
* modular arithmetic 只在声明的 valid subspace 上保证语义。
* QEC 资源计算不是“估一个数字”，而是生成可检查的 IR、schedule、QEOL artifacts。

当前阶段判定
------------

已经稳定的闭环是：

* YAML DSL 可以生成 Python ``Composite``。
* pyqres 可以生成 QEC-Compiler ``AbstractCircuit``。
* QEC examples 的 gate-level YAML mirrors 可以逐门匹配 QEC-Compiler builders。
* QDA-tridiagonal 可以在多个矩阵尺寸下自动 lowering 到 ``AbstractCircuit``。
* ``MOD_ADD``/``MOD_MUL`` 等第一批 intermediate primitive 可以进入 QEC arithmetic lowering。

尚未宣称完成的是：

* QRAM 的 pyqres wrapper 语义。
* 所有高层算法的完整 statevector 对拍。
* 大规模优化级 arithmetic implementation。
