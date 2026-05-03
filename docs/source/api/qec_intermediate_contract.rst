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

``CMUL_MOD_N(control, x; c, N)``
    controlled modular multiplication。control 为 1 时执行 ``MOD_MUL``，否则 no-op。
    QEC lowering 可以为 work/flag 分配 clean auxiliary qubit。

PySparQ reference 要求
---------------------

pyqres 中间层 primitive 的 ``pyqsparse_object()`` 必须与上述 contract 一致。
如果 PySparQ 暂无等价 primitive，则该 reference 必须抛出 ``NotImplementedError``，
直到补齐正确实现；不能使用语义不同的 primitive 作为占位。
