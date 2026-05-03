# Quantum-Resource-Estimator (pyqres)

## 介绍

Quantum-Resource-Estimator 是一个基于 Python 的量子计算资源估计工具，专注于 **寄存器级编程范式**。

### 核心功能

- 在寄存器层级编写量子程序
- 估计量子程序的 `T-count` / `T-depth` / `Toffoli-count` / `Toffoli-depth`（可参数化）
- 利用 PySparQ C++ 模拟器对程序进行量子态模拟
- 生成交互式 HTML 调用树和寄存器级 circuit visualization
- 生成 Quantikz LaTeX 量子线路图
- DSL 系统支持 YAML 定义组合操作

## 架构

Quantum-Resource-Estimator 采用 Operation 树 + Visitor 模式：

- **Operation**: 所有操作的基类，支持 controller 链和 dagger
- **Primitive**: 叶节点，直接映射 PySparQ 操作（门、算术、寄存器操作等）
- **Composite**: 组合操作，通过 program_list 分解为子操作
- **Visitor**: TCounter / TDepthCounter / ToffoliCounter / SimulatorVisitor / TreeRenderer / PlainRenderer

## 安装

```bash
git clone https://github.com/Agony5757/Quantum-Resource-Estimator.git
cd Quantum-Resource-Estimator
pip install -e .
```

## 快速示例

```python
from pyqres.core.metadata import RegisterMetadata
from pyqres.core.simulator import SimulatorVisitor
from pyqres.primitives import Hadamard, X, CNOT

# 声明寄存器
RegisterMetadata.get_register_metadata().declare_register('q', 2)

# 构建操作树并模拟
sim = SimulatorVisitor()
Hadamard(['q']).traverse(sim)
X(['q'], [0]).traverse(sim)
print(f"State size: {sim.state.size()}")
```

## CLI 命令

```bash
# 资源估计（T-count, T-depth, Toffoli-count）
pyqres estimate Toffoli                      # T-count: 7
pyqres estimate Toffoli -m t_depth          # T-depth: 4
pyqres estimate Toffoli -m toffoli_count    # toffoli_count: 1

# 指定寄存器大小
pyqres estimate Add_UInt_UInt -r a:4,b:4,c:5
pyqres estimate Mult_UInt_ConstUInt -r a:4,b:4 -p const:5 -m t_count

# 使用原语集
pyqres estimate MyAlgorithm --primitive clifford_t

# 查看操作依赖树
pyqres show Swap --depth 3

# DSL 编译与检查
pyqres compile                              # 编译 YAML schema → Python 代码
pyqres compile --primitive toffoli          # 使用 Toffoli 原语集
pyqres compile --lib pyqres/lib/arithmetic/ # 加载库文件
pyqres check                                # 完整性检查（依赖、覆盖率）
```

## Visualization

pyqres 提供两类交互式 HTML visualization，输出文件是自包含 HTML，
可以直接用浏览器打开，不需要启动本地服务。

- **Call tree**：展示 `Operation` / `Composite` / `Primitive` 调用树。每个节点可以展开，详情里包含寄存器、参数、controller、dagger 状态和 submodule 信息。
- **Register-level circuit**：把操作树渲染为寄存器级时间线。侧边栏可以切换 call-tree/circuit 视图，调节 expansion depth，并选择某个 composite module 强制展开后重绘线路。

```python
from pyqres.core.metadata import RegisterMetadata
from pyqres.algorithms.block_encoding import BlockEncodingTridiagonal
from pyqres.visualization import write_call_tree_html, write_circuit_html

rm = RegisterMetadata.get_register_metadata()
rm.declare_register("main", 2, "UnsignedInteger")
rm.declare_register("anc_UA", 4, "UnsignedInteger")

op = BlockEncodingTridiagonal("main", "anc_UA", alpha=0.5, beta=0.3)

write_call_tree_html(op, "block_encoding_tree.html")
write_circuit_html(op, "block_encoding_circuit.html")
```

QDA-Tridiagonal 示例：

```bash
python examples/qda_tridiagonal_visualization.py
```

默认输出：

- `visualizations/qda_tridiagonal_tree.html`
- `visualizations/qda_tridiagonal_circuit.html`

## DSL 用法

Quantum-Resource-Estimator 提供了一套 DSL（领域特定语言），允许通过 YAML 文件定义组合操作，然后自动编译生成 Python 代码。

### YAML Schema 定义

在 `pyqres/dsl/schemas/composites/` 下创建 YAML 文件：

```yaml
# pyqres/dsl/schemas/composites/my_op.yml
name: MyOperation
description: "描述信息"
qregs:                          # 量子寄存器声明
  - {name: reg1, type: General}
  - {name: reg2, type: UnsignedInteger}
params:                         # 经典参数声明
  - {name: iterations, type: int}
  - {name: angles, type: array}
temp_regs:                      # 临时寄存器（可选）
  - {name: flag, size: 1}
computed_params:                # 计算参数（可选）
  - {name: computed_size, formula: "iterations * 2"}
impl:                           # 实现体
  - op: Hadamard
    qregs: [reg1]
```

### 寄存器类型

| 类型 | 用途 | 示例操作 |
|------|------|---------|
| `General` | 通用量子比特 | Hadamard, X, CNOT |
| `UnsignedInteger` | 无符号整数 | Add, Mult, Compare |
| `SignedInteger` | 有符号整数 | 算术运算 |
| `Boolean` | 布尔标志 | Compare 输出 |
| `Rational` | 有理数 | 特殊算术 |

### 参数类型

| 类型 | 说明 | 示例 |
|------|------|------|
| `int` | 整数 | 迭代次数、寄存器大小 |
| `float` | 浮点数 | 旋转角度 |
| `str` | 字符串 | 动态门名称 |
| `bool` | 布尔值 | 条件标志 |
| `array` | 数组 | 角度列表 |
| `symbol` | 符号表达式 | 参数化资源估计 |
| `object` | 通用对象 | 复杂配置 |

### 操作调用

```yaml
# 基本调用
- op: Hadamard
  qregs: [reg1]

# 带参数
- op: PhaseGate
  qregs: [reg1]
  params: [angle, 0.01]

# 带 dagger（逆操作）
- op: QRAM
  qregs: [addr, data]
  params: [0]
  dagger: true

# 带 controller（控制）
- op: X
  qregs: [target]
  controllers:
    all_ones: [control_reg]       # 全1控制
    nonzero: [flag_reg]           # 非0控制
    bit: [[flag, 1]]              # 比特控制
    value: [[addr, 5]]            # 值控制
```

### 控制流结构

#### loop - 正向循环

```yaml
- loop:
    iterations: n           # 整数或参数名
    body:
      - op: Hadamard
        qregs: [reg1]
```

生成的 Python 代码：
```python
for i in range(self.n):
    self.program_list.append(OperationRegistry.get_class("Hadamard")(reg_list=[self.reg1]))
```

#### loop_reverse - 逆向循环

```yaml
- loop_reverse:
    iterations: n
    body:
      - op: Hadamard
        qregs: [reg1]
```

生成的 Python 代码：
```python
for i in range(self.n - 1, -1, -1):
    self.program_list.append(OperationRegistry.get_class("Hadamard")(reg_list=[self.reg1]))
```

#### for_each - 遍历迭代

```yaml
# 遍历字面量列表
- for_each:
    var: angle
    items: [0.1, 0.2, 0.3]
    body:
      - op: PhaseGate
        qregs: [reg1]
        params: [$angle, 0.01]    # $var 引用迭代变量

# 遍历参数数组
- for_each:
    var: gate_name
    items: gate_names            # 引用 array 类型参数
    body:
      - op: DynamicGate
        qregs: [reg1]
        params: [$gate_name]
```

生成的 Python 代码：
```python
for angle in [0.1, 0.2, 0.3]:
    self.program_list.append(OperationRegistry.get_class("PhaseGate")(reg_list=[self.reg1], param_list=[angle, 0.01]))
```

#### if/else/elif - 条件分支

```yaml
# 基本 if
- if:
    condition: "self.mode == 'fast'"
    body:
      - op: FastOp
        qregs: [reg1]

# if-else
- if:
    condition: "self.flag"
    body:
      - op: Hadamard
        qregs: [reg1]
    else:
      - op: X
        qregs: [reg1]

# if-elif-else 链
- if:
    condition: "self.variant == 1"
    body:
      - op: Op1
        qregs: [reg1]
    elif:
      - condition: "self.variant == 2"
        body:
          - op: Op2
            qregs: [reg1]
    else:
      - op: DefaultOp
        qregs: [reg1]
```

> **注意**: `if` 是 Python 层面的经典控制流，不是量子控制。`condition` 是 Python 表达式，可以使用 `self.param_name` 引用参数。

#### python - 原生 Python 代码块

当 DSL 无法表达复杂逻辑时，可以直接插入 Python 代码：

```yaml
# 单行代码
- python: "self.program_list.append(OperationRegistry.get_class('X')(reg_list=[self.reg1]))"

# 多行代码
- python: |
    for i in range(3):
        self.program_list.append(
            OperationRegistry.get_class("X")(reg_list=[self.r1])
        )

# 访问内部状态
- python: |
    if self.mode == 'special':
        self._custom_flag = True
        self.program_list.append(OperationRegistry.get_class("Hadamard")(reg_list=[self.reg1]))
```

> **注意**: `python` 块中的代码由用户负责正确性，DSL 不会分析其中的依赖关系。

### 注释

```yaml
- comment: "这是一个注释，不会生成任何代码"
```

### 嵌套控制流

控制流可以任意嵌套：

```yaml
- loop:
    iterations: n
    body:
      - for_each:
          var: mode
          items: modes
          body:
            - if:
                condition: "mode == 'h'"
                body:
                  - op: Hadamard
                    qregs: [reg1]
                else:
                  - op: X
                    qregs: [reg1]
```

### 控制与逆操作（Control & Dagger）

Quantum-Resource-Estimator 提供了两种强大的量子操作变换机制：**控制（Control）** 和 **逆操作（Dagger）**。

#### 控制器链（Controller Chain）

控制器用于实现量子控制，即操作在满足特定条件时才执行。系统支持 4 种控制类型：

| 控制类型 | 方法 | 说明 |
|---------|------|------|
| `all_ones` | `control_by_all_ones(reg)` | 寄存器所有比特都为 1 时执行 |
| `nonzero` | `control_by_nonzero(reg)` | 寄存器值非零时执行 |
| `bit` | `control_by_bit((reg, bit))` | 指定比特为 1 时执行 |
| `value` | `control_by_value((reg, val))` | 寄存器等于指定值时执行 |

**流式 API 示例：**

```python
from pyqres.primitives import X, CNOT
from pyqres.core.metadata import RegisterMetadata

# 声明寄存器
RegisterMetadata.get_register_metadata().declare_register('ctrl', 2)
RegisterMetadata.get_register_metadata().declare_register('target', 1)

# 单控制：ctrl 全为 1 时翻转 target
X(['target']).control_by_all_ones(['ctrl'])

# 多控制：组合不同控制类型
X(['target']).control_by_all_ones(['ctrl1']).control_by_nonzero(['ctrl2'])
```

**在 YAML 中使用控制器：**

```yaml
impl:
  - op: X
    qregs: [target]
    controllers:
      all_ones: [ctrl_reg]           # 全 1 控制
      nonzero: [flag_reg]            # 非 0 控制
      bit: [[flag, 1]]               # 比特控制（flag 寄存器的第 1 位）
      value: [[addr, 5]]             # 值控制（addr == 5）
```

**控制器传播规则：**

控制器会自动向下传播到子操作。例如，控制一个组合操作时，所有子操作都会继承该控制条件：

```python
# Swap 受控时，其内部所有 CNOT 都会继承控制条件
swap = Swap(['a', 'b']).control_by_all_ones(['ctrl'])
```

#### 逆操作（Dagger）

逆操作实现量子门的厄米共轭（Hermitian adjoint），即 U†。使用 `.dagger()` 方法：

```python
# 创建逆操作
inverse_op = MyOperation(['reg']).dagger()

# dagger 可以链式调用，两次调用恢复原操作
original = op.dagger().dagger()  # 等价于 op
```

**Dagger 传播规则：**

1. **默认行为**：dagger 传播到子操作，子节点以**逆序**遍历
2. **自伴操作**：`__self_conjugate__ = True` 的操作在 dagger 时行为不变

```python
class Hadamard(Primitive):
    __self_conjugate__ = True  # H† = H，dagger 传播在此停止

class T(Primitive):
    __self_conjugate__ = False  # T† ≠ T，需要特殊处理
```

**自伴操作列表：**
- 单比特门：`Hadamard`, `X`, `Y`, `Z`
- 多比特门：`CNOT`, `Toffoli`, `Swap`

**非自伴操作列表：**
- 旋转门：`T`, `Rx(theta)`, `Ry(theta)`, `Rz(theta)`, `Phase(theta)`
- 这些门的 dagger 会取负角度

### 特殊配置

#### self_conjugate

标记操作是否自伴（U† = U）。自伴操作在 dagger 时行为不变：

```yaml
name: Swap
description: "Swap via 3 CNOTs"
qregs:
  - {name: reg1, type: General}
  - {name: reg2, type: General}
impl:
  - op: CNOT
    qregs: [reg1, reg2]
  - op: CNOT
    qregs: [reg2, reg1]
  - op: CNOT
    qregs: [reg1, reg2]
self_conjugate: true  # Swap† = Swap
```

#### control_override

某些组合操作的控制器传播需要特殊处理。以 **Swap = 3 CNOT** 为例：

**问题背景：**

Swap 操作由三个 CNOT 组成：
```
CNOT(a, b) → CNOT(b, a) → CNOT(a, b)
```

如果简单地让控制器传播到所有 CNOT，受控 Swap 会变成：
```
C-CNOT(a, b) → C-CNOT(b, a) → C-CNOT(a, b)
```

但这**不是**正确的受控 Swap！正确的受控 Swap 应该只控制"核心"操作——中间的 CNOT。

**解决方案：**

使用 `control_override: cnot_swap` 指定特殊的控制器传播模式：

```yaml
name: Swap
qregs:
  - {name: reg1, type: General}
  - {name: reg2, type: General}
impl:
  - op: CNOT
    qregs: [reg1, reg2]
  - op: CNOT
    qregs: [reg2, reg1]
  - op: CNOT
    qregs: [reg1, reg2]
control_override: cnot_swap  # 只有中间的 CNOT 接收控制器
self_conjugate: true
```

**生成的代码：**

```python
class Swap(StandardComposite):
    __self_conjugate__ = True

    def __init__(self, reg_list):
        ...

    def traverse_children(self, visitor, dagger_ctx=False, controllers_ctx=None):
        controllers_ctx = controllers_ctx or {}
        controllers = merge_controllers(self.controllers, controllers_ctx)
        self.program_list[0].traverse(visitor, False, {})          # 第一个 CNOT 无控制
        self.program_list[1].traverse(visitor, False, controllers)  # 中间 CNOT 受控
        self.program_list[2].traverse(visitor, False, {})          # 第三个 CNOT 无控制
```

**为什么这样是正确的？**

受控 Swap 的电路结构：
```
        ┌───┐
ctrl: ──┤   ├── ...
        │ S │
  a: ───┤ W ├── ...
        │ A │
  b: ───┤ P ├── ...
        └───┘
```

实际上等价于：
```
  a: ──■───────■──
        │       │
  b: ───┼───■───┼──
        │   │   │
ctrl: ──┼───■───┼──  ← 只有中间 CNOT 受控
        │       │
      ──┴───────┴──
```

第一个和第三个 CNOT 实现的是"交换首尾"的功能，不需要控制条件。只有中间的 CNOT 才是真正的"条件交换"。

**内置 control_override 模式：**

| 模式 | 用途 | 控制器传播行为 |
|------|------|---------------|
| `cnot_swap` | Swap 类操作 | 只有 `program_list[1]`（中间操作）接收控制器 |

**自定义 control_override：**

对于更复杂的控制器传播需求，可以手动实现 `traverse_children` 方法：

```python
from pyqres.core.operation import StandardComposite
from pyqres.core.utils import merge_controllers

class MyCustomOperation(StandardComposite):
    def traverse_children(self, visitor, dagger_ctx=False, controllers_ctx=None):
        controllers_ctx = controllers_ctx or {}
        controllers = merge_controllers(self.controllers, controllers_ctx)

        # 自定义控制器传播逻辑
        # 例如：奇偶索引的操作交替接收控制器
        for i, program in enumerate(self.program_list):
            ctrl = controllers if i % 2 == 1 else {}
            program.traverse(visitor, dagger_ctx, ctrl)
```

#### sum_t_count_formula

自定义 T-count 计算公式（用于复杂算法）：

```yaml
name: MyAlgorithm
sum_t_count_formula: custom
# 需要在生成的类中手动实现 sum_t_count 方法
```

### 编译与使用

```bash
# 编译所有 schema
pyqres compile

# 检查依赖完整性
pyqres check

# 查看操作依赖树
pyqres show GroverSearch --depth 3
```

```python
# 在 Python 中使用生成的操作
from pyqres.generated import MyOperation, GroverSearch
from pyqres.core.visitor import TCounter

# 实例化
op = GroverSearch(
    reg_list=[('addr_reg', 4), ('data_reg', 64), ('search_data_reg', 64)],
    param_list=[4, 2]  # n_qubits, n_repeats
)

# 资源估计
counter = TCounter()
op.traverse(counter)
print(f"T-count: {counter.get_result()}")
```

## QEC-Compiler 联调

pyqres 可以把支持的 `Operation` 树 lowering 为 QEC-Compiler 的
`AbstractCircuit`。推荐入口是：

```python
from pyqres.core.lowering import to_abstract_circuit
from pyqres.core.metadata import RegisterMetadata
from pyqres.primitives import Hadamard

RegisterMetadata.get_register_metadata().declare_register("q", 1)
circuit = to_abstract_circuit(Hadamard(["q"]))
```

底层由 `QECLoweringVisitor` 完成寄存器分配、controller/dagger 传播和
`AbstractGate` 生成。未实现的核心 primitive 会 fail closed，抛出
`UnsupportedQECPrimitive`，避免把 QRAM、自定义算术或未验证条件旋转静默当成
no-op。

### 中间层 primitive

当前 pyqres 公开导出的 QEC 中间层 primitive 包括：

| Primitive | QEC gate | 语义 |
|---|---|---|
| `MCX` | `MCX` | 多控制 X，最后一个寄存器是 target。 |
| `ADD` | `ADD(n)` | `|a>|b> -> |a>|a+b mod 2^n>`，QEC pass 分配 clean carry。 |
| `PLUS_ONE` | `PLUS_ONE(n)` | 寄存器加一，模 `2^n`。 |
| `REFLECT` | `REFLECT(n)` | 多比特反射。 |
| `MOD_ADD` | `MOD_ADD(N)` | clean modular add: `|a>|b>|0> -> |a>|a+b mod N>|0>`。 |
| `MOD_MUL` | `MOD_MUL(c,N)` | clean modular multiply: `|x>|0>|0> -> |c*x mod N>|0>|0>`。 |

controller 与 dagger context 在 lowering 时会变成显式 QEC gate：
`ADD_DAG` / `CADD` / `CADD_DAG`、`PLUS_ONE_DAG` / `CPLUS_ONE` /
`CPLUS_ONE_DAG`、`MOD_SUB` / `CMOD_ADD` / `CMOD_SUB`、`CMOD_MUL`。
`MOD_MUL.dagger()` 会把 multiplier 改写为 `c^-1 mod N`。
Shor `ExpMod` 仍使用兼容 gate `CMUL_MOD_N`。

这些 primitive 的 schema 位于：

```text
pyqres/dsl/schemas/primitives/intermediate.primitive.yaml
```

`MOD_ADD` / `MOD_MUL` 的 QEC lowering 目前采用 polynomial-size
ripple/comparator/modular-adder baseline，用于小规模 Shor/QDA 联调和正确性验证；
它不是最终性能优化实现。

### 验证流程

pyqres 侧的联调测试覆盖：

- `to_abstract_circuit()` 公开入口
- intermediate primitive 导出和 lowering
- unsupported primitive fail-closed
- Shor `ExpMod -> CMUL_MOD_N`
- QDA-Tridiagonal / `WalkS_Primitive` lowering 到 QEC pipeline

运行定向联调：

```bash
pytest tests/test_qec_lowering.py tests/test_qec_shor.py -q
```

这些测试需要当前环境能 import `qec_compiler`。在只安装
Quantum-Resource-Estimator 的 standalone CI 环境中，它们会作为跨仓库集成测试被
pytest skip；开发联调时请先安装或把 QEC-Compiler checkout 加入 `PYTHONPATH`。

运行 pyqres 全量回归：

```bash
pytest -q
```

QEC-Compiler 侧还会对 `ADD`、`ADD_DAG`、`PLUS_ONE`、`MOD_ADD`、`MOD_SUB`、
`MOD_MUL`、`CMOD_MUL`、`CMUL_MOD_N` 等做小规模 truth-table 检查。
修改中间层 primitive 或 QEC lowering contract 时，需要同时运行 QEC-Compiler
的 arithmetic 测试。

## 算法实现

Quantum-Resource-Estimator 实现了 QRAM-Simulator 文档中的主要量子算法，分为 **手写实现**（`algorithms/`）和 **DSL 生成**（`generated/`）两类。

### 手写算法 (`pyqres/algorithms/`)

手写算法包含复杂的数学公式和自定义逻辑，无法用简单的 YAML 表示。

#### Shor 量子因式分解 (`shor.py`)

半经典 Shor 算法，用于整数分解。核心函数：

```python
from pyqres.algorithms.shor import general_expmod, find_best_fraction, SemiClassicalShor

# 模幂运算（平方-乘法算法）
a_x_mod_N = general_expmod(a, x, N)

# 连分数展开提取周期
r, c = find_best_fraction(y, Q, N)

# 半经典 Shor 电路
shor = SemiClassicalShor(reg_list=[anc_reg], param_list=[a, N])
```

**数学原理：**
- 目标：找到 $a^x \mod N = 1$ 的周期 $r$
- 量子部分：迭代相位估计
- 经典部分：连分数展开恢复周期

#### CKS 线性系统求解 (`cks_solver.py`)

Childs-Kothari-Somma 量子线性系统求解器，时间复杂度 $O(\kappa \log(\kappa/\epsilon))$。

```python
from pyqres.algorithms.cks_solver import CKSLinearSolver, SparseMatrix

# 从稠密矩阵创建稀疏表示
mat = SparseMatrix.from_dense(A)

# Chebyshev 多项式系数
cheb = ChebyshevPolynomialCoefficient(b)
coef = cheb.coef(j)  # 第 j 个系数

# 求解线性系统 Ax = b
solver = CKSLinearSolver(reg_list=[anc_reg, b_reg], param_list=[kappa, eps])
```

**核心组件：**
- `SparseMatrix`: 稀疏矩阵表示，用于量子游走
- `ChebyshevPolynomialCoefficient`: Chebyshev 多项式系数计算
- `LCUContainer`: 线性组合酉算子容器

#### QDA 线性系统求解 (`qda_solver.py`)

量子离散绝热（Quantum Discrete Adiabatic）求解器，实现最优缩放 $O(\kappa \log(\kappa/\epsilon))$。

```python
from pyqres.algorithms.qda_solver import QDALinearSolver, compute_fs, chebyshev_T

# 计算插值参数 f(s)
fs = compute_fs(s, kappa, p=2)  # 公式 (69)

# Chebyshev 多项式
T_n = chebyshev_T(n, x)

# Dolph-Chebyshev 窗口函数
coeffs = dolph_chebyshev(eps, l, phi)

# 求解线性系统
solver = QDALinearSolver(reg_list=[main_reg, anc_reg], param_list=[kappa, eps])
```

**核心公式：**
- 插值参数：$f(s) = \frac{\kappa}{\kappa-1} \times (1 - (1 + s(\kappa^{p-1} - 1))^{1/(1-p)})$
- 旋转矩阵：$R_s = \frac{1}{\sqrt{(1-f)^2 + f^2}} \begin{pmatrix} 1-f & f \\ f & f-1 \end{pmatrix}$

### DSL 生成算法 (`pyqres/generated/`)

通过 YAML schema 定义并编译生成的算法。

#### GroverSearch - 量子搜索

```python
from pyqres.generated import GroverSearch

# 创建 Grover 搜索操作
grover = GroverSearch(
    reg_list=[('addr', 3), ('data', 64), ('search', 64)],
    param_list=[3, 1]  # [n_qubits, n_repeats]
)
```

**电路结构：**
1. Hadamard 初始化叠加态
2. 迭代 Oracle + 扩散算子
3. 测量地址寄存器

#### ShorFactor - Shor 因式分解

```python
from pyqres.generated import ShorFactor

shor = ShorFactor(
    reg_list=[('anc', 8), ('work', 1)],
    param_list=[15, 2]  # [N, a]
)
```

**电路结构：**
1. 初始化 ancilla 为 $|1\rangle$
2. 迭代相位估计（precision 次）
3. Hadamard + 受控模乘 + 相位修正 + 测量

#### CKSLinearSolver - CKS 线性求解器

```python
from pyqres.generated import CKSLinearSolver

cks = CKSLinearSolver(
    reg_list=[('anc', 3), ('b', 8)],
    param_list=[10.0, 0.01]  # [kappa, epsilon]
)
```

**电路结构：**
1. 块编码矩阵 A
2. 态制备 $|b\rangle$
3. Chebyshev 多项式迭代（5 次）

#### QDALinearSolver - QDA 线性求解器

```python
from pyqres.generated import QDALinearSolver

qda = QDALinearSolver(
    reg_list=[('main', 4), ('anc', 1)],
    param_list=[10.0, 0.01]  # [kappa, epsilon]
)
```

**电路结构：**
1. 初始化到 $H_0$ 本征态
2. 态制备 $|b\rangle$
3. 离散绝热演化（adiab_steps 次）
4. 测量

#### QuantumPhaseEstimation - 量子相位估计

```python
from pyqres.generated import QuantumPhaseEstimation

pe = QuantumPhaseEstimation(
    reg_list=[('prec', 4), ('eigen', 4)],
    param_list=[4, 'unitary_name']  # [n_precision, unitary_name]
)
```

**电路结构：**
1. Hadamard 初始化精度寄存器
2. 受控酉迭代
3. 逆 QFT

### 资源估计

所有生成的算法都支持资源估计：

```python
from pyqres.core.visitor import TCounter, TDepthCounter

# T-count 估计
counter = TCounter()
grover.traverse(counter)
print(f"Grover T-count: {counter.get_result()}")

# T-depth 估计
depth_counter = TDepthCounter()
shor.traverse(depth_counter)
print(f"Shor T-depth: {depth_counter.get_result()}")
```

### 自定义 DSL 算法

创建新的 DSL 算法只需编写 YAML 文件：

```yaml
# pyqres/dsl/schemas/composites/my_algorithm.yml
name: MyAlgorithm
description: "My custom quantum algorithm"
qregs:
  - {name: reg, type: General}
params:
  - {name: iterations, type: int}
temp_regs:
  - {name: flag, size: 1}
impl:
  - op: Hadamard
    qregs: [reg]

  - loop:
      iterations: iterations
      body:
        - op: X
          qregs: [reg]

        - op: Hadamard
          qregs: [reg]
```

然后运行 `pyqres compile` 生成 Python 代码。

## 原语集（Primitive Sets）

Quantum-Resource-Estimator 支持定义不同的原语集（gate sets），用于资源估计时指定哪些操作是"原子"的（不再分解）。

### 原语集定义

原语集通过 `.primitive.yaml` 文件定义：

```yaml
# pyqres/dsl/schemas/primitives/clifford_t.primitive.yaml
name: clifford_t
description: "Clifford+T gate set"
primitives:
  - Hadamard
  - S
  - T
  - CNOT
  - X
  - Y
  - Z
```

### 内置原语集

- `clifford_t`: Clifford+T 门集（H, S, T, CNOT, X, Y, Z）
- `toffoli`: Toffoli 门集（Toffoli, H, T）
- `qram`: QRAM 门集（QRAM, Toffoli, H, T）

### 使用原语集

```bash
# 使用 Clifford+T 门集编译
pyqres compile --primitive clifford_t

# 使用 Toffoli 门集进行资源估计
pyqres estimate MyAlgorithm --primitive toffoli
```

### 原语集验证

如果操作不在原语集中且没有分解定义，编译时会报错：

```bash
$ pyqres compile --primitive clifford_t
Error: Operation 'QRAM' is not in the active primitive set 'clifford_t' 
and has no decomposition defined.
```

## 库文件（Libraries）

Quantum-Resource-Estimator 提供预定义的操作库，用户可以直接导入使用。

### 内置库

```
pyqres/lib/
├── arithmetic/      # 算术操作
│   └── addition.yml
├── oracles/         # Oracle 操作
│   └── oracles.yml
└── state_prep/      # 态制备
    └── state_prep.yml
```

### 使用库

```bash
# 加载库文件
pyqres compile --lib pyqres/lib/arithmetic/ --lib pyqres/lib/oracles/

# 在 YAML 中引用库操作
# my_algorithm.yml
name: MyAlgorithm
impl:
  - op: Increment     # 来自 arithmetic 库
    qregs: [counter]
```

### 创建自定义库

库文件是标准的 YAML schema 文件：

```yaml
# my_libs/custom.yml
name: MyCustomOp
description: "My custom operation"
qregs:
  - {name: reg, type: General}
impl:
  - op: Hadamard
    qregs: [reg]
```

```bash
pyqres compile --lib my_libs/custom.yml
```
