# QRAM Contract

**Status**: Draft — pending review before implementation begins.

This document defines the QRAM primitive contract for pyqres. Both `QRAM` and
`QRAMFast` remain `NotImplementedError` until this contract is reviewed and
accepted.

---

## 1. Dual-mode design

QRAM operates in **two distinct modes**:

| Mode | Purpose | Backend |
|------|---------|---------|
| **Simulation** | Sparse-state simulation via PySparQ | `pysparq.QRAMCircuit_qutrit` |
| **Compilation** | QEC resource estimation / QEOL emission | QEC-Compiler `AbstractGate("QRAM_LOAD", ...)` |

The two modes share no runtime state. Simulation uses PySparQ's C++ engine;
compilation emits an opaque `QRAM_LOAD` gate for downstream QEC passes.

---

## 2. Register conventions

### Address register (`addr_reg`)

- Type: `UnsignedInteger`
- Size: `n_addr` qubits (encodes addresses `0` to `2^n_addr - 1`)
- Declared via `RegisterMetadata.declare_register(name, n_addr, "UnsignedInteger")`

### Data register (`data_reg`)

- Type: `UnsignedInteger`
- Size: `n_data` qubits (holds values `0` to `2^n_data - 1`)
- Initialized to `|0>` before the load

### Memory (classical parameter)

- Type: `list[int]` or `tuple[int, ...]`
- Length: must equal `2^n_addr`
- Each element: integer in `[0, 2^n_data)`
- Memory is **classical read-only data**, not a reversible oracle
- Passed as `param_list[0]` to the QRAM constructor

---

## 3. Semantic contract

### Load operation

```
|addr>|0>  →  |addr>|memory[addr]>
```

The address register is **not** entangled with the data register after the
load (in the ideal noiseless case). The operation is its own inverse when
memory is a permutation; otherwise it is not unitary and requires ancilla.

### QRAM vs QRAMFast

| Property | QRAM | QRAMFast |
|----------|------|----------|
| Protocol | Explicit QROM decomposition | Bucket-brigade routing |
| T-count | O(n_addr * n_data) | O(sqrt(2^n_addr) * n_data) |
| Ancilla | O(n_addr) routing qubits | O(2^n_addr) bucket qubits |
| Use case | Small memory tables | Large sparse memories |

---

## 4. Simulation behavior

In simulation mode, `QRAM.pyqsparse_object()` returns a PySparQ operation
that performs the load on a `SparseState`:

```python
import pysparq as ps

def pyqsparse_object(self, dagger_ctx=False, controllers_ctx=None):
    qram = ps.QRAMCircuit_qutrit(
        addr_size=self.n_addr,
        data_size=self.n_data,
        memory=list(self.memory),  # must be plain list, not numpy
    )
    return ps.QRAMLoad(qram, self.addr_reg, self.data_reg)
```

**Key constraints**:
- `memory` must be a Python `list` or `tuple`, not a numpy array
- `QRAMLoad` takes the circuit object and register name strings
- Dagger is a no-op for QRAM (the load is not reversible in general)

---

## 5. Compilation behavior

In compilation mode, `QRAM.to_abstract_gates()` emits a single opaque gate:

```python
def to_abstract_gates(self, qubit_map):
    from qec_compiler.ir import AbstractGate
    addr_qubits = qubit_map[self.addr_reg]
    data_qubits = qubit_map[self.data_reg]
    return [AbstractGate(
        name="QRAM_LOAD",
        qubits=tuple(addr_qubits) + tuple(data_qubits),
        params=(len(self.memory),),
    )]
```

The QEC-Compiler is responsible for decomposing `QRAM_LOAD` into surface-code
operations. This is **not** implemented yet — the gate is opaque.

---

## 6. Tiny memory-load example

**Setup**:
- `n_addr = 2` (addresses 0..3)
- `n_data = 2` (values 0..3)
- `memory = [1, 3, 0, 2]`

**Registers**:
```python
RegisterMetadata.get_register_metadata().declare_register("addr", 2, "UnsignedInteger")
RegisterMetadata.get_register_metadata().declare_register("data", 2, "UnsignedInteger")
```

**Operation**:
```python
qram = QRAM(reg_list=["addr", "data"], param_list=[[1, 3, 0, 2]])
```

**Expected simulation behavior**:
```
|00>|00>  →  |00>|01>   (memory[0] = 1)
|01>|00>  →  |01>|11>   (memory[1] = 3)
|10>|00>  →  |10>|00>   (memory[2] = 0)
|11>|00>  →  |11>|10>   (memory[3] = 2)
```

**Expected compilation output**:
```
AbstractGate(name="QRAM_LOAD", qubits=(0,1,2,3), params=(4,))
```

---

## 7. Implementation prerequisites

Before implementing QRAM:

1. [ ] This contract document is reviewed and accepted
2. [ ] PySparQ `QRAMCircuit_qutrit` API is verified with a manual test
3. [ ] QEC-Compiler's position on `QRAM_LOAD` decomposition is confirmed
4. [ ] Test: `QRAM.pyqsparse_object()` loads `memory = [1, 3, 0, 2]` correctly
5. [ ] Test: `QRAM.to_abstract_gates()` emits `QRAM_LOAD` with correct qubits
6. [ ] Test: `QRAM.t_count()` returns 0 (opaque gate, no T-gate decomposition)
7. [ ] Test: `QRAMFast` raises `NotImplementedError` until bucket-brigade is implemented

---

## 8. Open questions

1. **QEC decomposition**: Should `QRAM_LOAD` decompose into explicit QROM
   (multi-controlled X gates) or remain opaque for a higher-level QRAM pass?

2. **Controlled QRAM**: Should `QRAM.control_by_all_ones()` produce a
   controlled load, or is control handled at the QEC level?

3. **Dagger semantics**: For non-permutation memory, the load is not unitary.
   Should `dagger()` raise `ValueError`, or should it uncompute via
   `|addr>|memory[addr]> → |addr>|0>` (which requires the memory to be known)?

4. **Sparse memory**: For memories with many zero entries, should `QRAMFast`
   use a different protocol than the full bucket-brigade?
