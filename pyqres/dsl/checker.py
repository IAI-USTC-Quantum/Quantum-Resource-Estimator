"""
Completeness Checker for Quantum-Resource-Estimator DSL (composite-only).

Analyzes composite operation definitions to find:
- Missing operation references (not in primitives or composites)
- Circular dependencies
- Dependency ordering
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any
from pathlib import Path
import yaml

from ..core.registry import OperationRegistry


@dataclass
class DependencyNode:
    """Node in the operation dependency graph."""
    name: str
    is_primitive: bool
    is_defined: bool
    dependencies: Set[str] = field(default_factory=set)
    dependents: Set[str] = field(default_factory=set)
    definition_source: Optional[str] = None


@dataclass
class CompletenessReport:
    """Report on operation definition completeness."""
    total_defined: int
    composites_defined: int
    missing_operations: List[str]
    circular_dependencies: List[List[str]]
    is_valid: bool

    def __str__(self) -> str:
        lines = [
            "=== Quantum-Resource-Estimator DSL Completeness Report ===",
            f"Composites defined: {self.composites_defined}",
        ]

        if self.missing_operations:
            lines.append(f"\nMissing operations ({len(self.missing_operations)}):")
            for op in self.missing_operations[:10]:
                lines.append(f"  - {op}")
            if len(self.missing_operations) > 10:
                lines.append(f"  ... and {len(self.missing_operations) - 10} more")

        if self.circular_dependencies:
            lines.append(f"\nCircular dependencies ({len(self.circular_dependencies)}):")
            for cycle in self.circular_dependencies[:5]:
                lines.append(f"  - {' -> '.join(cycle)} -> {cycle[0]}")
            if len(self.circular_dependencies) > 5:
                lines.append(f"  ... and {len(self.circular_dependencies) - 5} more")

        return "\n".join(lines)


class CompletenessChecker:
    """
    Validates completeness of composite operation definitions.

    Checks that all referenced operations exist as either
    primitives (in OperationRegistry) or composites (defined in YAML).
    """

    def __init__(self):
        self.graph: Dict[str, DependencyNode] = {}
        self.definitions: Dict[str, Dict[str, Any]] = {}

    def _is_known_primitive(self, name: str) -> bool:
        """Check if an operation is a known primitive (not composite)."""
        if not OperationRegistry.has_class(name):
            return False
        try:
            from ..core.operation import Primitive
            cls = OperationRegistry.get_class(name)
            return issubclass(cls, Primitive)
        except Exception:
            return False

    def add_definition(self, defn: Dict[str, Any], source: Optional[str] = None):
        """Add a composite operation definition to the graph."""
        name = defn.get("name", "")
        if not name:
            return

        deps = self._extract_dependencies(defn)

        self.definitions[name] = defn
        self.graph[name] = DependencyNode(
            name=name,
            is_primitive=self._is_known_primitive(name),
            is_defined=True,
            dependencies=deps,
            dependents=set(),
            definition_source=source
        )

        # Update dependents and create placeholder nodes
        for dep in deps:
            if dep not in self.graph:
                self.graph[dep] = DependencyNode(
                    name=dep,
                    is_primitive=self._is_known_primitive(dep),
                    is_defined=self._is_known_primitive(dep),
                    dependencies=set(),
                    dependents={name},
                    definition_source="registry" if self._is_known_primitive(dep) else None
                )
            else:
                self.graph[dep].dependents.add(name)

    def add_definitions(self, definitions: List[Dict[str, Any]], source: Optional[str] = None):
        """Add multiple definitions."""
        for defn in definitions:
            self.add_definition(defn, source)

    def load_from_directory(self, schema_dir: str):
        """Load all definitions from a directory of YAML files.

        Skips subdirectories named 'demos/' (used for example schemas).
        """
        schema_path = Path(schema_dir)
        if not schema_path.exists():
            return

        for yml_file in sorted(schema_path.rglob("*.yml")):
            # Skip demo/example directories
            if any(part == "demos" for part in yml_file.parts):
                continue
            with open(yml_file, "r") as f:
                definitions = yaml.safe_load(f)
            if definitions is None:
                continue
            if not isinstance(definitions, list):
                definitions = [definitions]
            self.add_definitions(definitions, str(yml_file))

    def _extract_dependencies(self, defn: Dict[str, Any]) -> Set[str]:
        """Extract all operation names referenced in impl, including nested structures.

        Excludes declared operation parameters (type: operation) since these are
        expected to be provided at runtime by the caller.
        """
        deps = set()

        # Collect declared operation parameters
        declared_op_params = set()
        for param in defn.get("params", []):
            if isinstance(param, dict) and param.get("type") == "operation":
                declared_op_params.add(param["name"])

        for call in defn.get("impl", []):
            self._extract_deps_from_item(call, deps, declared_op_params)
        return deps

    def _extract_deps_from_item(self, item: Dict[str, Any], deps: Set[str],
                                  declared_op_params: Set[str] = None):
        """Recursively extract dependencies from an impl item."""
        if not isinstance(item, dict):
            return

        if declared_op_params is None:
            declared_op_params = set()

        # Extract direct operation reference (skip declared operation params)
        if "op" in item:
            op_name = item["op"]
            if op_name not in declared_op_params:
                deps.add(op_name)

        # Python blocks don't have dependencies we can analyze
        # (user is responsible for any operations they create)
        if "python" in item:
            return

        # Recurse into loop bodies
        if "loop" in item and "body" in item["loop"]:
            for body_item in item["loop"]["body"]:
                self._extract_deps_from_item(body_item, deps, declared_op_params)

        if "loop_reverse" in item and "body" in item["loop_reverse"]:
            for body_item in item["loop_reverse"]["body"]:
                self._extract_deps_from_item(body_item, deps, declared_op_params)

        # Recurse into for_each bodies
        if "for_each" in item and "body" in item["for_each"]:
            for body_item in item["for_each"]["body"]:
                self._extract_deps_from_item(body_item, deps, declared_op_params)

        # Recurse into if/else/elif bodies
        if "if" in item:
            if "body" in item["if"]:
                for body_item in item["if"]["body"]:
                    self._extract_deps_from_item(body_item, deps, declared_op_params)
            if "else" in item["if"]:
                for body_item in item["if"]["else"]:
                    self._extract_deps_from_item(body_item, deps, declared_op_params)
            if "elif" in item["if"]:
                for elif_def in item["if"]["elif"]:
                    if "body" in elif_def:
                        for body_item in elif_def["body"]:
                            self._extract_deps_from_item(body_item, deps, declared_op_params)

    def check(self) -> CompletenessReport:
        """Perform completeness check."""
        # Find missing operations
        missing_operations = []
        for name, node in self.graph.items():
            if not node.is_defined:
                missing_operations.append(name)

        # Detect circular dependencies
        circular = self._detect_cycles()

        composites_defined = len(self.definitions)

        return CompletenessReport(
            total_defined=composites_defined,
            composites_defined=composites_defined,
            missing_operations=sorted(missing_operations),
            circular_dependencies=circular,
            is_valid=len(missing_operations) == 0 and len(circular) == 0
        )

    def _detect_cycles(self) -> List[List[str]]:
        """Detect circular dependencies using DFS."""
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(node_name: str, path: List[str]):
            if node_name in rec_stack:
                cycle_start = path.index(node_name)
                cycle = path[cycle_start:] + [node_name]
                cycles.append(cycle)
                return

            if node_name in visited:
                return

            visited.add(node_name)
            rec_stack.add(node_name)
            path.append(node_name)

            node = self.graph.get(node_name)
            if node:
                for dep in node.dependencies:
                    dfs(dep, path)

            path.pop()
            rec_stack.remove(node_name)

        for name in self.graph:
            if name not in visited:
                dfs(name, [])

        return cycles

    def get_dependency_order(self) -> List[str]:
        """Get topological order for generating code."""
        visited = set()
        order = []

        def visit(name: str):
            if name in visited:
                return
            visited.add(name)

            node = self.graph.get(name)
            if node:
                for dep in node.dependencies:
                    visit(dep)

            if name in self.definitions:
                order.append(name)

        for name in self.definitions:
            visit(name)

        return order

    def get_tree(self, operation_name: str, depth: int = 0, max_depth: int = 10) -> str:
        """Get a tree representation of an operation's dependencies."""
        if depth > max_depth:
            return "  " * depth + "... (max depth reached)\n"

        lines = []
        node = self.graph.get(operation_name)

        if node is None:
            return "  " * depth + f"{operation_name} (undefined)\n"

        prefix = "  " * depth
        marker = "├─ " if depth > 0 else ""

        if node.is_primitive and node.is_defined:
            lines.append(prefix + marker + f"{operation_name} [primitive]\n")
        elif not node.is_defined:
            lines.append(prefix + marker + f"{operation_name} [UNDEFINED]\n")
        else:
            lines.append(prefix + marker + f"{operation_name}\n")
            for dep in sorted(node.dependencies):
                lines.append(self.get_tree(dep, depth + 1, max_depth))

        return "".join(lines)


def check_completeness(definitions: List[Dict[str, Any]]) -> CompletenessReport:
    """Convenience function to check completeness of definitions."""
    checker = CompletenessChecker()
    checker.add_definitions(definitions)
    return checker.check()


def check_directory(schema_dir: str) -> CompletenessReport:
    """Convenience function to check a directory of YAML files."""
    checker = CompletenessChecker()
    checker.load_from_directory(schema_dir)
    return checker.check()
