QEC 中间层 Primitive Contract
=============================

本页冻结 pyqres 与 QEC-Compiler 第一版联调用中间层 primitive 的语义。
pyqres lowering、PySparQ reference simulation、QEC-Compiler decomposition 必须共享这些约束。

通用约定
--------

* 所有多比特整数寄存器使用 little-endian bit order：bit 0 是最低位。
* modular arithmetic 只保证合法子空间语义，输入整数必须满足 ``0 <= x < N``。
* work、flag、predicate 等辅助 qubit 必须以 ``|0>`` 输入，并在操作结束后恢复到 ``|0>``。
* 不支持的 controlled 或 dagger lowering 必须显式报错，不能静默忽略控制条件或逆操作。
* composite dagger 使用标准规则：反向遍历 children，并对每个 child 应用 dagger context。
* PySparQ reference 必须语义等价；没有等价实现时必须抛 ``NotImplementedError``。

Primitive 语义
--------------

``MCX(controls..., target)``
    当且仅当所有 control qubit 为 1 时翻转 target。自伴。

``PLUS_ONE(x)``
    ``|x> -> |x + 1 mod 2^n>``。dagger 为 ``|x> -> |x - 1 mod 2^n>``。

``ADD(a, b)``
    等宽 in-place 加法：``|a>|b>|0> -> |a>|a + b mod 2^n>|0>``。
    QEC lowering 可以自行分配 clean carry qubit。dagger 为模 ``2^n`` 减法。

``REFLECT(qs...)``
    对所有输入 qubit 同时为 1 的 basis state 施加负号。自伴。

``MOD_ADD(a, b; N)``
    合法子空间 ``a,b < N`` 上执行 ``|a>|b>|0> -> |a>|a + b mod N>|0>``。
    dagger 为 ``|a>|b>|0> -> |a>|b - a mod N>|0>``。
    pyqres QEC lowering 会自动分配一个 clean flag ancilla，并计入 ``AbstractCircuit.num_qubits``。

``MOD_MUL(x; c, N)``
    合法子空间 ``x < N`` 且 ``gcd(c, N) = 1`` 时执行
    ``|x>|0>|0> -> |c*x mod N>|0>|0>``。
    dagger 使用 ``c^-1 mod N`` 作为 multiplier。

QEC gate 变体
-------------

pyqres 公开的中间层 Python primitive 固定为 ``MCX``、``PLUS_ONE``、
``ADD``、``REFLECT``、``MOD_ADD``、``MOD_MUL``。在 lowering 到
QEC-Compiler ``AbstractCircuit`` 时，controller 与 dagger context 会被显式
编码为 QEC gate 名称，而不是被静默消去：

* ``PLUS_ONE_DAG`` / ``CPLUS_ONE`` / ``CPLUS_ONE_DAG``
* ``ADD_DAG`` / ``CADD`` / ``CADD_DAG``
* ``MOD_SUB`` / ``CMOD_ADD`` / ``CMOD_SUB``
* ``CMOD_MUL``；``MOD_MUL`` 的 dagger 通过 ``c^-1 mod N`` 改写 multiplier

controlled gate 的 qubit 顺序统一为 ``controls...`` 后接原 primitive qubit。
``C*`` gate 的最后一个参数是 ``n_controls``，用于 QEC-Compiler 从 qubit 列表
中拆分外部控制位。value-control 为 0 时，pyqres lowering 会在控制位前后插入
``X`` sandwich，使 QEC-Compiler 仍只需要识别 all-ones control。

``CMUL_MOD_N(control, x; c, N)``
    Shor ``ExpMod`` 的兼容 gate。control 为 1 时执行 ``MOD_MUL``，否则 no-op。
    这是 pyqres Shor lowering 的历史路径；新中间层 primitive 的 controlled
    modular multiplication 使用 ``CMOD_MUL``。QEC lowering 可以为 work/flag
    分配 clean auxiliary qubit。

QEC IR primitives
-----------------

YAML-defined QEC examples 使用一组显式 primitive 对接 QEC-Compiler
``AbstractCircuit``，而不是通过任意 gate adapter 注入 payload。当前直接对齐的
primitive 包括：

``H`` / ``Z`` / ``SWAP`` / ``CPHASE`` / ``RX`` / ``RY`` / ``RZ`` / ``CCX``
    发出同名 ``AbstractGate``。这些 primitive 使用单个 register 加 register-local
    qubit index 参数，例如 ``CPHASE(["q"], [0, 1, theta])``。

``CMUL_MOD_N``
    发出 QEC-Compiler small-Shor/legacy modular exponentiation 使用的
    ``AbstractGate("CMUL_MOD_N")``。参数为 ``[qubits, multiplier, modulus]``。

``X`` / ``Y`` / ``CNOT`` 以及 ``ADD`` / ``MOD_ADD`` / ``MOD_MUL``
    继续作为普通 pyqres primitive 经 ``QECLoweringVisitor`` 降到 QEC IR。

PySparQ reference 状态
---------------------

.. list-table::
   :widths: 24 28 48
   :header-rows: 1

   * - Primitive
     - PySparQ reference
     - 说明
   * - ``MCX`` / ``ADD`` / ``PLUS_ONE`` / ``REFLECT``
     - 有参考路径或可由现有 PySparQ primitive 表达
     - 用于小规模语义 smoke。
   * - ``MOD_ADD``
     - 暂无
     - 必须抛 ``NotImplementedError``，不能用普通 add 冒充 modular add。
   * - ``MOD_MUL``
     - 有 PySparQ modular multiplication reference
     - dagger 使用 modular inverse multiplier。
   * - ``H`` / ``Z`` / ``SWAP`` / ``CPHASE`` / ``RX`` / ``RY`` / ``RZ`` / ``CCX`` / ``CMUL_MOD_N``
     - 暂无通用 PySparQ reference
     - 作为 QEC IR primitive 直接 lowering 到 ``AbstractGate``。
   * - ``QRAM`` / ``QRAMFast``
     - 当前禁用
     - pyqres wrappers 全部显式抛 ``NotImplementedError``。

QRAM 策略
---------

QRAM 暂时不进入 pyqres/QEC 联调主线。直接 PySparQ QRAM 实验仍可进行，但 pyqres
``QRAM`` 和 ``QRAMFast`` wrapper 不提供 dummy memory、不提供 T-count 占位、不提供 QEC lowering。
未来需要单独定义 address/data width、memory layout、load/unload、clean ancilla 和 QEC resource contract。
