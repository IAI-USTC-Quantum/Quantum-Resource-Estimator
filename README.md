# Quantum-Resource-Estimator (pyqres)

Quantum-Resource-Estimator is a register-level quantum algorithm authoring,
simulation, resource-estimation, and QEC-Compiler integration toolkit.

Algorithms are written as YAML-generated or hand-written pyqres `Operation`
trees, verified with PySparQ when a faithful reference exists, lowered to
QEC-Compiler `AbstractCircuit`, and compiled into QEC-level layout, schedule,
and QEOL artifacts.

```text
pyqres YAML DSL / Python Operation tree
  -> PySparQ register-level simulation when supported
  -> pyqres QEC lowering
  -> QEC-Compiler AbstractCircuit
  -> logical lowering / lattice surgery / QEOL JSON
```

## What It Does

- Defines quantum programs as `Operation` trees with `Primitive` and `Composite` nodes.
- Compiles YAML DSL composite schemas to Python classes under `pyqres.generated`.
- Supports controller and dagger propagation through operation trees.
- Runs register-level simulation through PySparQ for supported primitives.
- Estimates coarse `T-count`, `T-depth`, `Toffoli-count`, and `Toffoli-depth`.
- Emits interactive HTML call-tree and register-level circuit visualizations.
- Lowers supported operations to QEC-Compiler `AbstractCircuit`.
- Provides YAML mirrors of QEC-Compiler benchmark examples for gate-level parity tests.

## Repository Layout

```text
pyqres/
  core/                  Operation, visitors, metadata, lowering, QEC lowering
  primitives/            PySparQ-facing primitives and QEC intermediate primitives
  algorithms/            Hand-written algorithms and QEC example helpers
  dsl/                   YAML schema validation and code generation
  generated/             DSL-generated operation classes
  visualization/         Standalone HTML call-tree and circuit renderers
  quantikz/              LaTeX Quantikz circuit diagram generation
docs/source/             Sphinx documentation
docs/qram_contract.md    QRAM primitive contract (draft)
examples/                Small runnable examples
tests/                   Unit, integration, QEC lowering, YAML mirror, visualization tests
runs/                    QEOL output artifacts (gitignored)
```

## Install

```bash
git clone git@github.com:IAI-USTC-Quantum/Quantum-Resource-Estimator.git
cd Quantum-Resource-Estimator
python -m venv .venv
source .venv/bin/activate
pip install -e ".[test]"
```

`pysparq` is installed from QRAM-Simulator as declared in `pyproject.toml`.
QEC integration additionally requires `qec_compiler` to be importable. In a
side-by-side checkout, use:

```bash
PYTHONPATH=../QEC-compiler/src:. .venv/bin/python your_script.py
```

QEC-Compiler itself uses `uv`:

```bash
cd ../QEC-compiler
uv venv
source .venv/bin/activate
uv sync --all-extras
```

## Minimal Simulation Example

```python
import pysparq as ps

from pyqres.core.metadata import RegisterMetadata
from pyqres.core.simulator import SimulatorVisitor
from pyqres.primitives import Hadamard, X

rm = RegisterMetadata.get_register_metadata()
rm.declare_register("q", 2, "UnsignedInteger")

sim = SimulatorVisitor()
Hadamard(["q"]).traverse(sim)
X(["q"], [0]).traverse(sim)

print(ps.StatePrint(sim.state, ps.StatePrintDisplay.Detail))
```

## Minimal QEC Lowering Example

```python
from pyqres.core.lowering import to_abstract_circuit
from pyqres.core.metadata import RegisterMetadata
from pyqres.primitives import Hadamard, CNOT

rm = RegisterMetadata.get_register_metadata()
rm.declare_register("q0", 1, "Boolean")
rm.declare_register("q1", 1, "Boolean")

class BellProgram:
    def __init__(self):
        self.program_list = [Hadamard(["q0"]), CNOT(["q0", "q1"], [0, 0])]

    def traverse(self, visitor, dagger_ctx=False, controllers_ctx=None):
        for op in self.program_list:
            op.traverse(visitor, dagger_ctx, controllers_ctx or {})

circuit = to_abstract_circuit(BellProgram())
print(circuit.num_qubits)         # 2
print([g.name for g in circuit.gates])  # ['H', 'CNOT']
```

## CLI

```bash
# Compile YAML DSL schemas to Python classes
pyqres compile

# Check schema dependency coverage
pyqres check

# Inspect an operation dependency tree
pyqres show QECExampleQFT --depth 3
pyqres show Swap --depth 3

# Estimate coarse resources
pyqres estimate Toffoli
pyqres estimate Toffoli -m t_depth
pyqres estimate Add_UInt_UInt -r a:4,b:4,c:4
```

See `docs/source/cli/index.rst` for the full CLI reference.

## YAML DSL

Composite operations are described in YAML and compiled to Python classes.
Built-in schemas live under:

```text
pyqres/dsl/schemas/composites/    composite operation definitions
pyqres/dsl/schemas/primitives/    primitive set definitions
pyqres/lib/                       predefined operation library
```

Example composite:

```yaml
- name: QECExampleQFT
  qregs:
    - {name: q, type: General}
  params:
    - {name: n, type: int}
  impl:
    - python: |
        from ..algorithms.qec_examples import build_qec_qft
    - python: |
        build_qec_qft(self.program_list, self.q, self.n)
```

The generated class can lower to QEC-Compiler `AbstractCircuit`:

```python
from pyqres.core.lowering import to_abstract_circuit
from pyqres.core.metadata import RegisterMetadata
from pyqres.generated import QECExampleQFT

RegisterMetadata.get_register_metadata().declare_register("q", 4, "General")
circuit = to_abstract_circuit(QECExampleQFT(["q"], [4]))
```

The DSL supports register declarations, classical parameters, temporary
registers, loops, `for_each`, Python-level `if`/`elif`/`else`, inline Python
blocks, operation comments, controllers, and dagger annotations.

## Supported Algorithm Workflows

Gate-level YAML mirrors currently match QEC-Compiler benchmark builders for:

- GHZ and W-state preparation
- Bernstein-Vazirani and Deutsch-Jozsa
- Grover
- QFT and QPE
- QAOA, VQE, and Ising
- SWAP-test
- Small Shor fixtures for `N=15` and `N=21`

Register-level algorithm workflows include:

- `BlockEncodingTridiagonal` (tridiagonal matrix block encoding)
- `QDALinearSolver` (quantum discrete adiabatic linear solver, 2x2 to 8x8)
- Hand-written Shor / `ExpMod` lowering via `CMUL_MOD_N`
- Grover search with oracle + diffusion
- CKS linear solver

QDA-tridiagonal is tested for multiple matrix sizes (`main_bits = 1, 2, 3`)
through `AbstractCircuit` lowering and QEC logical lowering.

## QEC Intermediate Contract

The first shared primitive contract with QEC-Compiler:

| pyqres primitive | QEC gate family | Notes |
|---|---|---|
| `MCX` | `MCX` | Multi-control X. |
| `PLUS_ONE` | `PLUS_ONE`, `PLUS_ONE_DAG`, `CPLUS_ONE`, `CPLUS_ONE_DAG` | Increment/decrement modulo `2^n`. |
| `ADD` | `ADD`, `ADD_DAG`, `CADD`, `CADD_DAG` | Equal-width in-place addition modulo `2^n`. |
| `REFLECT` | `REFLECT` | Multi-controlled phase reflection. |
| `MOD_ADD` | `MOD_ADD`, `MOD_SUB`, `CMOD_ADD`, `CMOD_SUB` | Clean modular add/subtract on the valid subspace. |
| `MOD_MUL` | `MOD_MUL`, `CMOD_MUL` | Clean modular multiply; dagger uses `c^-1 mod N`. |
| `QECGate` | arbitrary QEC gate name | Compiler-only adapter for YAML benchmark mirrors. |

Shor `ExpMod` emits the compatibility gate `CMUL_MOD_N`.

Lowering is implemented by `pyqres.core.qec_lowering.QECLoweringVisitor`.
Unsupported primitives fail closed with `UnsupportedQECPrimitive` instead of
silently becoming no-ops.

## QEC End-to-End: QEOL JSON

The full integration spine — from a pyqres YAML composite to a QEC-Compiler
QEOL JSON artifact — works end-to-end:

```python
from pyqres.core.metadata import RegisterMetadata
from pyqres.core.lowering import to_abstract_circuit
from pyqres.generated import QECExampleGHZ
from qec_compiler.compiler import QECCompiler
import json

meta = RegisterMetadata.get_register_metadata()
meta.declare_register("q0", 1)
meta.declare_register("q1", 1)
meta.declare_register("q2", 1)

op = QECExampleGHZ(reg_list=["q0", "q1", "q2"], param_list=[3])
circuit = to_abstract_circuit(op)

compiler = QECCompiler()
result = compiler.compile(circuit)

with open("runs/ghz_qeol.json", "w") as f:
    json.dump(result.qeol_program.to_dict(), f, indent=2)
```

The resulting QEOL JSON (~14 KB for GHZ) contains the surface-code layout,
operation schedule, and syndrome channels.

## QRAM Status

QRAM and QRAMFast primitives are intentionally disabled (raise
`NotImplementedError`).  A written contract defining register conventions,
memory layout, and simulation vs. compilation behavior exists at
`docs/qram_contract.md`.  Implementation will begin after the contract is
reviewed.

Direct PySparQ QRAM experiments are still possible outside pyqres.

## Visualization

pyqres can write standalone HTML visualizations for an already constructed
operation object.  The files contain inline CSS and JavaScript and can be
opened directly in a browser.

```python
from pyqres.algorithms.block_encoding import BlockEncodingTridiagonal
from pyqres.core.metadata import RegisterMetadata
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
```

For LaTeX output, `pyqres.quantikz.QuantikzVisitor` compiles an `Operation`
tree into register-level Quantikz:

```python
from pyqres.quantikz import QuantikzVisitor

visitor = QuantikzVisitor()
op.traverse(visitor)
latex = visitor.to_latex()
```

See `docs/source/visualization/index.rst` for details.

## Tests

410 tests, PySparQ simulation tests auto-skip when pysparq is absent.

```bash
# All tests
pytest -q

# QEC lowering and integration
pytest tests/test_qec_lowering.py tests/test_qec_shor.py -q
pytest tests/test_qec_examples_yaml.py -v
pytest tests/test_arithmetic_lowering.py -v

# QDA tridiagonal (2x2, 4x4, 8x8)
pytest tests/test_qda_tridiagonal_sizes.py -v

# QEOL end-to-end demo
pytest tests/test_qeol_demo.py -v

# QRAM fail-closed
pytest tests/test_qram_unimplemented.py -v

# Visualization
pytest tests/test_visualization_html.py -q

# Build Sphinx docs
sphinx-build -b html docs/source docs/_build/html
```

If `qec_compiler` is not importable, cross-repository QEC tests are skipped by
design in standalone pyqres environments.

## Documentation

- `docs/source/getting_started/` — installation and quickstart
- `docs/source/core_concepts/` — Operation hierarchy, register model, visitor pattern
- `docs/source/defining_operations/` — YAML DSL and hand-written composites
- `docs/source/qec_integration.rst` — QEC lowering reference and QEOL workflow
- `docs/qram_contract.md` — QRAM primitive contract (draft)
- `docs/source/visualization/` — HTML and Quantikz output
- `docs/source/simulation/` — PySparQ simulation guide
- `docs/source/api/` — API reference

## License

MIT. See `LICENSE`.
