QRAM 当前策略
=============

当前 pyqres/QEC 联调主线明确暂不支持 QRAM wrapper。

实际行为
--------

``pyqres.primitives.QRAM`` 和 ``pyqres.primitives.QRAMFast`` 仍保留类名，保证历史 YAML/Python import 不崩溃；但它们的语义入口全部显式报错：

.. code-block:: text

   QRAM.pyqsparse_object()      -> NotImplementedError
   QRAM.t_count()               -> NotImplementedError
   QRAMFast.pyqsparse_object()  -> NotImplementedError
   QRAMFast.t_count()           -> NotImplementedError

为什么不能用 dummy memory
-------------------------

QRAM 是强语义 primitive：address/data width、memory layout、load/unload 是否 self-adjoint、
clean ancilla contract、QEC lowering 资源模型都必须明确。用 dummy memory 或普通 arithmetic primitive
冒充会让 PySparQ reference 与 QEC contract 不一致。

因此当前策略是 fail closed：

* 不提供近似 PySparQ reference。
* 不提供 T-count 占位数。
* 不进入 QEC lowering 主路径。

测试记录
--------

.. code-block:: bash

   .venv/bin/pytest tests/test_qram_unimplemented.py -q

测试使用 strict ``xfail``，表示当前预期行为就是 ``NotImplementedError``。未来 QRAM contract 修复后，应删除 xfail 并补充正向 reference tests。

直接 PySparQ QRAM
-----------------

如果只是实验 QRAM-Simulator 本体，可以直接使用 PySparQ API；这不代表 pyqres QRAM wrapper 已经进入稳定 workflow。

.. code-block:: python

   import pysparq as ps

   ps.System.clear()
   state = ps.SparseState()
   ps.AddRegister("addr", ps.UnsignedInteger, 2)(state)
   ps.AddRegister("data", ps.UnsignedInteger, 3)(state)
   ps.Hadamard_Int("addr", 2)(state)

   qram = ps.QRAMCircuit_qutrit(2, 3, [0, 2, 4, 6])
   ps.QRAMLoad(qram, "addr", "data")(state)
