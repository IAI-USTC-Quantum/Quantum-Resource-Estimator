# Quantum-Resource-Estimator (pyqres)

Quantum-Resource-Estimator is a register-level quantum algorithm authoring,
simulation, resource-estimation, and QEC-Compiler integration toolkit.

The current project focus is larger than coarse resource estimation: pyqres is
the algorithm entry point in a three-project workflow. Algorithms are written as
YAML-generated or hand-written pyqres `Operation` trees, verified with PySparQ
when a faithful reference exists, lowered to QEC-Compiler `AbstractCircuit`, and
then compiled into QEC-level layout/schedule/QEOL artifacts.

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
  core/                  Operation, visitors, metadata, lowering
  primitives/            PySparQ-facing primitives and QEC intermediate primitives
  algorithms/            Hand-written algorithms and QEC example helpers
  dsl/                   YAML schema validation and code generation
  generated/             DSL-generated operation classes
  visualization/         Standalone HTML call-tree and circuit renderers
docs/source/             Sphinx documentation
examples/                Small runnable examples
tests/                   Unit, integration, QEC lowering, YAML mirror, visualization tests
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
print(circuit.num_qubits)
print([gate.name for gate in circuit.gates])
```

## YAML DSL

Compile built-in YAML schemas:

```bash
pyqres compile
pyqres check
pyqres show QECExampleQFT --depth 2
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

## Supported Algorithm Workflows

Gate-level YAML mirrors currently match QEC-Compiler benchmark builders for:

- GHZ and W-state preparation
- Bernstein-Vazirani and Deutsch-Jozsa
- Grover
- QFT and QPE
- QAOA, VQE, and Ising
- SWAP-test
- small Shor fixtures for `N=15` and `N=21`

Register-level algorithm workflows include:

- `BlockEncodingTridiagonal`
- generated `QDALinearSolver` with tridiagonal block encoding
- hand-written Shor / `ExpMod` lowering via `CMUL_MOD_N`
- intermediate arithmetic primitives: `MCX`, `PLUS_ONE`, `ADD`, `REFLECT`, `MOD_ADD`, `MOD_MUL`

QDA-tridiagonal is tested for multiple matrix sizes (`main_bits = 1, 2, 3`) through
`AbstractCircuit` lowering and QEC logical lowering.

## QEC Intermediate Contract

The first shared primitive contract with QEC-Compiler includes:

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

## QRAM Status

pyqres QRAM wrappers are intentionally disabled in the current QEC workflow:

- `QRAM.pyqsparse_object()` raises `NotImplementedError`.
- `QRAMFast.pyqsparse_object()` raises `NotImplementedError`.
- `t_count()` for QRAM wrappers also raises `NotImplementedError`.

Direct PySparQ QRAM experiments are still possible outside pyqres. The pyqres
QRAM contract will be defined later.

## Tests And Docs

```bash
# pyqres targeted integration
PYTHONPATH=../QEC-compiler/src:. .venv/bin/pytest \
  tests/test_qec_examples_yaml.py \
  tests/test_qec_lowering.py \
  tests/test_intermediate_semantics.py \
  tests/test_qram_unimplemented.py -q

# QEC arithmetic side
cd ../QEC-compiler
.venv/bin/python -m pytest \
  tests/test_arithmetic_decomposition.py \
  tests/test_arithmetic_truth_table.py -q

# docs
cd ../Quantum-Resource-Estimator
sphinx-build -b html docs/source docs/_build/html
```

## Documentation

The Sphinx documentation is the source of truth for detailed usage:

- `docs/source/workflow/`
- `docs/source/defining_operations/yaml_dsl.rst`
- `docs/source/api/qec_intermediate_contract.rst`
- `docs/source/simulation/`
- `docs/source/visualization/`

## License

MIT. See `LICENSE`.
