# Quantum-Resource-Estimator (pyqres)

Quantum-Resource-Estimator is a register-level quantum algorithm programming
and resource-estimation toolkit.  The current project focus is to use pyqres as
the algorithm authoring layer for QEC-Compiler integration: algorithms are
written as pyqres `Operation` trees, verified with PySparQ when possible,
visualized as interactive HTML, and lowered to QEC-Compiler `AbstractCircuit`
through a small intermediate primitive contract.

## What It Does

- Defines quantum programs as an `Operation` tree with `Primitive` and
  `Composite` nodes.
- Supports controller and dagger propagation through the tree.
- Provides a YAML DSL that compiles composite operation schemas to Python
  classes under `pyqres.generated`.
- Runs register-level simulation through PySparQ for supported primitives.
- Estimates coarse `T-count`, `T-depth`, `Toffoli-count`, and
  `Toffoli-depth`.
- Emits interactive HTML call-tree and register-level circuit visualizations.
- Lowers supported operations to QEC-Compiler `AbstractCircuit`.

## Repository Layout

```text
pyqres/
  core/                  Operation, visitors, metadata, lowering
  primitives/            PySparQ-facing and QEC intermediate primitives
  algorithms/            Hand-written algorithms such as Shor, QDA, CKS, Grover
  dsl/                   YAML schema validation and code generation
  generated/             DSL-generated operation classes
  visualization/         Standalone HTML call-tree and circuit renderers
docs/source/             Sphinx documentation
examples/                Small runnable examples
tests/                   Unit, integration, QEC lowering, and visualization tests
```

## Install

```bash
git clone git@github.com:IAI-USTC-Quantum/Quantum-Resource-Estimator.git
cd Quantum-Resource-Estimator
python -m venv .venv
source .venv/bin/activate
pip install -e ".[test]"
```

`pysparq` is installed from the QRAM-Simulator repository as declared in
`pyproject.toml`.  QEC integration tests additionally require
`qec_compiler` to be importable, either by installing QEC-Compiler or by adding
its checkout to `PYTHONPATH`.

## Minimal Example

```python
from pyqres.core.metadata import RegisterMetadata
from pyqres.core.simulator import SimulatorVisitor
from pyqres.primitives import Hadamard, X

RegisterMetadata.get_register_metadata().declare_register("q", 2)

sim = SimulatorVisitor()
Hadamard(["q"]).traverse(sim)
X(["q"], [0]).traverse(sim)

print(sim.state.size())
```

## CLI

```bash
# Compile YAML DSL schemas to Python classes
pyqres compile

# Check schema dependency coverage
pyqres check

# Inspect an operation dependency tree
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
pyqres/dsl/schemas/composites/
pyqres/dsl/schemas/primitives/
pyqres/lib/
```

Example shape:

```yaml
name: MyOperation
description: "Small composite operation"
qregs:
  - {name: q, type: General}
params:
  - {name: repeats, type: int}
impl:
  - loop:
      iterations: repeats
      body:
        - op: Hadamard
          qregs: [q]
```

The DSL supports register declarations, classical parameters, temporary
registers, loops, reverse loops, `for_each`, Python-level `if`/`elif`/`else`,
inline Python blocks, operation comments, controllers, and dagger annotations.
The detailed schema reference is in `docs/source/defining_operations/` and
`docs/source/dsl_schema/`.

## QEC-Compiler Integration

The recommended entry point is:

```python
from pyqres.core.lowering import to_abstract_circuit
from pyqres.core.metadata import RegisterMetadata
from pyqres.primitives import Hadamard

RegisterMetadata.get_register_metadata().declare_register("q", 1)
circuit = to_abstract_circuit(Hadamard(["q"]))
```

Lowering is implemented by `pyqres.core.qec_lowering.QECLoweringVisitor`.
Unsupported primitives fail closed with `UnsupportedQECPrimitive` instead of
silently becoming no-ops.

The frozen first-pass intermediate primitive set is:

| pyqres primitive | QEC gate family | Notes |
|---|---|---|
| `MCX` | `MCX` | Multi-control X. |
| `PLUS_ONE` | `PLUS_ONE`, `PLUS_ONE_DAG`, `CPLUS_ONE`, `CPLUS_ONE_DAG` | Modular increment/decrement. |
| `ADD` | `ADD`, `ADD_DAG`, `CADD`, `CADD_DAG` | Equal-width in-place addition modulo `2^n`. |
| `REFLECT` | `REFLECT` | Multi-controlled phase reflection. |
| `MOD_ADD` | `MOD_ADD`, `MOD_SUB`, `CMOD_ADD`, `CMOD_SUB` | Clean modular add/subtract on the valid subspace. |
| `MOD_MUL` | `MOD_MUL`, `CMOD_MUL` | Clean modular multiply; dagger uses `c^-1 mod N`. |

Shor `ExpMod` still emits the compatibility gate `CMUL_MOD_N`.  The full
contract is documented in `docs/source/api/qec_intermediate_contract.rst`.

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

The circuit view supports expansion depth and per-module expansion overrides.
For a QDA-Tridiagonal example:

```bash
python examples/qda_tridiagonal_visualization.py
```

See `docs/source/visualization/index.rst` for details.

## Tests And Docs

```bash
pytest -q
pytest tests/test_qec_lowering.py tests/test_qec_shor.py -q
pytest tests/test_visualization_html.py -q
sphinx-build -b html docs/source docs/_build/html
```

If `qec_compiler` is not importable, cross-repository QEC tests are skipped by
design in standalone pyqres environments.

## Documentation

The Sphinx documentation is the source of truth for detailed usage:

- `docs/source/getting_started/`
- `docs/source/defining_operations/`
- `docs/source/api/`
- `docs/source/visualization/`
- `docs/source/simulation/`

## License

MIT. See `LICENSE`.
