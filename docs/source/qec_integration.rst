QEC Integration
===============

pyqres lowers ``Operation`` trees to QEC-Compiler ``AbstractCircuit`` objects
through a small intermediate-primitive contract.  The resulting circuits can
then be compiled through the full QEC-Compiler lattice-surgery pipeline to
produce QEOL JSON artifacts.

Overview
--------

.. code-block:: text

   pyqres YAML  →  generated Python  →  Operation tree
                                                  ↓
                                    QECLoweringVisitor
                                                  ↓
                                     AbstractCircuit (QEC-Compiler)
                                                  ↓
                                     LatticeSurgeryCompilation
                                                  ↓
                                         QEOL JSON artifact

The lowering visitor (``pyqres.core.qec_lowering.QECLoweringVisitor``) walks
the Operation tree, dispatching each node by class name to a ``_lower_{ClassName}``
handler that emits ``AbstractGate`` objects.

Supported Primitives
--------------------

Gate primitives
^^^^^^^^^^^^^^^

All standard gate primitives lower directly to their QEC gate names:

.. list-table::
   :header-rows: 1

   * - pyqres Primitive
     - QEC Gate
   * - ``Hadamard``
     - ``H``
   * - ``X``
     - ``X`` (or ``MCX`` when controlled)
   * - ``CNOT``
     - ``CNOT``
   * - ``Toffoli``
     - ``CCX``
   * - ``Rz``, ``Ry``, ``Rx``
     - ``RZ``, ``RY``, ``RX``
   * - ``PhaseGate``
     - ``PHASE``
   * - ``Reflection_Bool``
     - ``REFLECT``

Arithmetic primitives
^^^^^^^^^^^^^^^^^^^^^

Arithmetic operations emit intermediate QEC gate names that the QEC-Compiler
decomposes into surface-code operations:

.. list-table::
   :header-rows: 1

   * - pyqres Primitive
     - QEC Gate
     - Ancilla
   * - ``ADD``
     - ``ADD`` / ``CADD``
     - 3n anonymous (carry, maj, temp)
   * - ``PLUS_ONE``
     - ``PLUS_ONE`` / ``CPLUS_ONE``
     - 1 overflow qubit
   * - ``MOD_ADD``
     - ``MOD_ADD`` / ``CMOD_ADD``
     - 1 anonymous flag qubit
   * - ``MOD_MUL``
     - ``MOD_MUL`` / ``CMOD_MUL``
     - n work + 1 flag qubit

All arithmetic gates support dagger variants (``ADD_DAG``, ``PLUS_ONE_DAG``,
``MOD_SUB``, etc.) and controlled variants (``CADD``, ``CPLUS_ONE``,
``CMOD_ADD``, ``CMOD_MUL``).

Register management
^^^^^^^^^^^^^^^^^^^

``SplitRegister`` and ``CombineRegister`` are handled as bookkeeping operations
by the lowering visitor.  They modify the ``QubitAllocator`` to track which
qubit indices belong to which named register, but emit no QEC gates.

QEC IR primitives
^^^^^^^^^^^^^^^^^

QEC-facing YAML programs use named primitives that lower to QEC-Compiler
``AbstractGate`` objects: ``H``, ``Z``, ``SWAP``, ``CPHASE``, ``RX``, ``RY``,
``RZ``, ``CCX``, ``CMUL_MOD_N``, plus existing pyqres primitives such as
``X``, ``Y``, ``CNOT``, ``ADD``, ``MOD_ADD``, and ``MOD_MUL``.

Example::

    from pyqres.primitives import H, CPHASE

    h = H(reg_list=["q"], param_list=[0])
    phase = CPHASE(reg_list=["q"], param_list=[0, 1, 0.125])

End-to-End Example: GHZ to QEOL JSON
-------------------------------------

.. code-block:: python

   from pyqres.core.metadata import RegisterMetadata
   from pyqres.core.lowering import to_abstract_circuit
   from pyqres.generated import QECExampleGHZ
   from qec_compiler.compiler import QECCompiler
   import json

   meta = RegisterMetadata.get_register_metadata()
   meta.declare_register("q", 3)

   op = QECExampleGHZ(reg_list=["q"], param_list=[3])
   circuit = to_abstract_circuit(op)

   # Compile through QEC-Compiler
   compiler = QECCompiler()
   result = compiler.compile(circuit)

   # Save QEOL JSON
   with open("ghz_qeol.json", "w") as f:
       json.dump(result.qeol_program.to_dict(), f, indent=2)

The output ``ghz_qeol.json`` is a small (~14 KB) inspectable artifact
containing the surface-code layout, operation schedule, and syndrome channels.

YAML DSL QEC Examples
---------------------

YAML composites mirror QEC-Compiler benchmark builders for parity testing:

``QECExampleGHZ``
    GHZ state: ``H(q0) → CNOT(q0,q1) → CNOT(q1,q2)``
    Mirrors ``build_ghz_circuit(3)``.

``QECExampleBV``
    Bernstein-Vazirani (secret=0b101): ``H×3 → CNOT → CNOT → H×3``
    Mirrors ``build_bv_circuit(3, secret=5)``.

These are defined in ``pyqres/dsl/schemas/composites/qec_examples.yml`` and
compiled into ``pyqres/generated/QECExample*.py``.

QRAM Status
-----------

QRAM and QRAMFast primitives currently raise ``NotImplementedError`` on all
operational methods.  A written contract exists at ``docs/qram_contract.md``
that must be reviewed before implementation begins.

Running QEC Tests
-----------------

QEC integration tests require ``qec_compiler`` to be importable:

.. code-block:: bash

   # Install QEC-Compiler
   pip install -e /path/to/QEC-compiler

   # Run QEC tests
   pytest tests/test_qec_examples_yaml.py -v
   pytest tests/test_qda_tridiagonal_sizes.py -v
   pytest tests/test_arithmetic_lowering.py -v
   pytest tests/test_qeol_demo.py -v
