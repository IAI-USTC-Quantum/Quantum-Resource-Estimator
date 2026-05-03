QEC 中间层 Primitive Contract
=============================

本页冻结 pyqres 与 QEC-compiler 第一版联调用中间层 primitive 的语义。
pyqres lowering、PySparQ reference simulation、QEC-compiler decomposition 必须共享这些约束。

通用约定
--------

* 所有多比特整数寄存器使用 little-endian bit order：bit 0 是最低位。
* 所有 modular arithmetic 只保证合法子空间语义，输入整数必须满足 ``0 <= x < N``。
* work、flag、predicate 等辅助 qubit 必须以 ``|0>`` 输入，并在操作结束后恢复到 ``|0>``。
* 不支持的 controlled 或 dagger lowering 必须显式报错，不能静默忽略控制条件或逆操作。
* composite dagger 使用标准规则：反向遍历 children，并对每个 child 应用 dagger context。

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

``MOD_MUL(x; c, N)``
    合法子空间 ``x < N`` 且 ``gcd(c, N) = 1`` 时执行
    ``|x>|0>|0> -> |c*x mod N>|0>|0>``。
    dagger 使用 ``c^-1 mod N`` 作为 multiplier。

QEC gate 变体
-------------

pyqres 公开的中间层 Python primitive 固定为 ``MCX``、``PLUS_ONE``、
``ADD``、``REFLECT``、``MOD_ADD``、``MOD_MUL``。在 lowering 到
QEC-compiler ``AbstractCircuit`` 时，controller 与 dagger context 会被显式
编码为 QEC gate 名称，而不是被静默消去：

* ``PLUS_ONE_DAG`` / ``CPLUS_ONE`` / ``CPLUS_ONE_DAG``
* ``ADD_DAG`` / ``CADD`` / ``CADD_DAG``
* ``MOD_SUB`` / ``CMOD_ADD`` / ``CMOD_SUB``
* ``CMOD_MUL``；``MOD_MUL`` 的 dagger 通过 ``c^-1 mod N`` 改写 multiplier

controlled gate 的 qubit 顺序统一为 ``controls...`` 后接原 primitive qubit。
``C*`` gate 的最后一个参数是 ``n_controls``，用于 QEC-compiler 从 qubit 列表
中拆分外部控制位。value-control 为 0 时，pyqres lowering 会在控制位前后插入
``X`` sandwich，使 QEC-compiler 仍只需要识别 all-ones control。

``CMUL_MOD_N(control, x; c, N)``
    Shor ``ExpMod`` 的兼容 gate。control 为 1 时执行 ``MOD_MUL``，否则 no-op。
    这是 pyqres Shor lowering 的历史路径；新中间层 primitive 的 controlled
    modular multiplication 使用 ``CMOD_MUL``。QEC lowering 可以为 work/flag
    分配 clean auxiliary qubit。

PySparQ reference 要求
--------------------------

pyqres 中间层 primitive 的 ``pyqsparse_object()`` 必须与上述 contract 一致。
如果 PySparQ 暂无等价 primitive，则该 reference 必须抛出 ``NotImplementedError``，
直到补齐正确实现；不能使用语义不同的 primitive 作为占位。
