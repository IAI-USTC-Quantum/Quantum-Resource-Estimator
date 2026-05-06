"""
DSL Compiler for Quantum-Resource-Estimator (composite-only).

Compiles YAML composite operation definitions to Python source files.
Orchestrates: loading YAML -> validation -> code generation -> file writing.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any, Set
import yaml

from ..core.registry import OperationRegistry
from .schema import SchemaValidator, ValidationError
from .codegen import CodeGenerator, GeneratedClass


class CompilationError(Exception):
    """Raised when compilation fails."""
    pass


class DSLCompiler:
    """
    Compiles YAML composite definitions to Python source files.

    Usage:
        compiler = DSLCompiler()
        result = compiler.compile_directory("schemas/composites/")

    With libraries:
        compiler = DSLCompiler(library_paths=["pyqres/lib/arithmetic/"])
        result = compiler.compile_file("my_algorithm.yml")
    """

    def __init__(self, library_paths: Optional[List[str]] = None):
        self.validator = SchemaValidator()
        self.generator = CodeGenerator()
        self.warnings: List[str] = []
        self.library_definitions: Dict[str, Dict[str, Any]] = {}
        self._import_stack: List[str] = []  # Track import stack for cycle detection

        # Load library definitions if provided
        if library_paths:
            for path in library_paths:
                self._load_library(path)

    def _load_library(self, path: str):
        """Load library definitions from a file or directory."""
        lib_path = Path(path)
        if lib_path.is_file():
            definitions = self._load_definitions_from_file(lib_path)
            for defn in definitions:
                name = defn.get("name", "")
                if name:
                    self.library_definitions[name] = defn
        elif lib_path.is_dir():
            for yml_file in lib_path.rglob("*.yml"):
                # Skip demo/example directories in libraries
                if any(part == "demos" for part in yml_file.parts):
                    continue
                definitions = self._load_definitions_from_file(yml_file)
                for defn in definitions:
                    name = defn.get("name", "")
                    if name:
                        self.library_definitions[name] = defn

    def _load_definitions_from_file(self, path: Path) -> List[Dict[str, Any]]:
        """Load definitions from a single YAML file."""
        with open(path) as f:
            definitions = yaml.safe_load(f)
        if definitions is None:
            return []
        if not isinstance(definitions, list):
            definitions = [definitions]
        return definitions

    def _resolve_imports(self, definitions: List[Dict[str, Any]],
                         source_path: Path) -> List[Dict[str, Any]]:
        """Resolve 'imports' field in definitions, recursively expanding them.

        Supports two syntaxes:
        - List of strings: imports: [file1.yml, file2.yml]
        - List of dicts: imports: [{file: file.yml, name: AliasName}]

        Args:
            definitions: YAML definitions list
            source_path: Path of the file containing these definitions (for relative resolution)

        Returns:
            Flattened definitions with imports expanded inline
        """
        resolved = []
        for defn in definitions:
            if "imports" in defn:
                import_specs = defn["imports"]
                if not isinstance(import_specs, list):
                    self.warnings.append(
                        f"'imports' in '{defn.get('name', '?')}' must be a list, got {type(import_specs).__name__}")
                    resolved.append(defn)
                    continue

                for spec in import_specs:
                    # Parse import spec: string path or dict {file: path, name: alias}
                    if isinstance(spec, str):
                        import_path = spec
                        alias = None
                    elif isinstance(spec, dict):
                        import_path = spec.get("file", "")
                        alias = spec.get("name")
                    else:
                        self.warnings.append(
                            f"Invalid import spec: {spec}, expected string or dict")
                        continue

                    if not import_path:
                        self.warnings.append(f"Empty import path in '{defn.get('name', '?')}'")
                        continue

                    # Resolve relative path from source file's directory
                    try:
                        resolved_path = (source_path.parent / import_path).resolve()
                    except Exception as e:
                        self.warnings.append(f"Invalid import path '{import_path}': {e}")
                        continue

                    resolved_path_str = str(resolved_path)

                    # Cycle detection
                    if resolved_path_str in self._import_stack:
                        raise CompilationError(
                            f"Circular import detected: {resolved_path} "
                            f"(import stack: {' -> '.join(self._import_stack + [resolved_path_str])})"
                        )

                    # Load imported definitions
                    self._import_stack.append(resolved_path_str)
                    try:
                        imported_defs = self._load_definitions_from_file(resolved_path)
                        # Recursively resolve nested imports
                        imported_defs = self._resolve_imports(imported_defs, resolved_path)
                    finally:
                        self._import_stack.pop()

                    # Add imported definitions (with optional alias)
                    for imp_def in imported_defs:
                        if alias:
                            # Create a renamed copy
                            renamed = dict(imp_def)
                            renamed["name"] = alias
                            resolved.append(renamed)
                        else:
                            resolved.append(imp_def)

            # Add the definition itself (after processing its imports)
            resolved.append(defn)

        return resolved

    def get_library_operation(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a library operation definition by name."""
        return self.library_definitions.get(name)

    def _get_known_operations(self) -> Set[str]:
        """Get all known operation names (primitives + previously registered)."""
        return set(OperationRegistry.all_names())

    def compile_file(self, yaml_path: str, output_dir: Optional[str] = None) -> List[GeneratedClass]:
        """Compile a single YAML file to Python classes."""
        path = Path(yaml_path)
        if not path.exists():
            raise CompilationError(f"File not found: {yaml_path}")

        with open(path, "r") as f:
            definitions = yaml.safe_load(f)

        if definitions is None:
            raise CompilationError(f"Empty YAML file: {yaml_path}")

        if not isinstance(definitions, list):
            definitions = [definitions]

        # Resolve imports (relative to the source file's directory)
        definitions = self._resolve_imports(definitions, source_path=path)

        return self._compile_definitions(definitions, output_dir)

    def compile_directory(self, schema_dir: str, output_dir: Optional[str] = None) -> List[GeneratedClass]:
        """Compile all YAML files in a directory."""
        schema_path = Path(schema_dir)
        if not schema_path.exists():
            raise CompilationError(f"Directory not found: {schema_dir}")

        all_definitions = self._load_directory_definitions(str(schema_path))
        if not all_definitions:
            self.warnings.append(f"No definitions found in {schema_dir}")
            return []

        return self._compile_definitions(all_definitions, output_dir)

    def compile_all(self, schema_base_dir: Optional[str] = None,
                    output_dir: Optional[str] = None) -> List[GeneratedClass]:
        """
        Compile all YAML composite definitions.

        Args:
            schema_base_dir: Base directory containing schemas/ subdirectory.
            output_dir: Directory to write generated files to.
        """
        if schema_base_dir is None:
            schema_base_dir = Path(__file__).parent / "schemas"
        else:
            schema_base_dir = Path(schema_base_dir)

        all_definitions = []

        composites_dir = schema_base_dir / "composites"
        if composites_dir.exists():
            all_definitions.extend(self._load_directory_definitions(str(composites_dir)))

        if not all_definitions:
            self.warnings.append(f"No definitions found in {schema_base_dir}")
            return []

        return self._compile_definitions(all_definitions, output_dir)

    def _load_directory_definitions(self, schema_dir: str) -> List[Dict[str, Any]]:
        """Load all definitions from a directory."""
        schema_path = Path(schema_dir)
        if not schema_path.exists():
            return []

        all_definitions = []
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
            all_definitions.extend(definitions)

        return all_definitions

    def _compile_definitions(self, definitions: List[Dict[str, Any]],
                             output_dir: Optional[str] = None) -> List[GeneratedClass]:
        """Compile definitions: validate -> generate -> write."""
        # Validate with known operations (including imported definitions)
        known_ops = self._get_known_operations()
        # Add all definition names to known_ops for cross-referencing
        for defn in definitions:
            if "name" in defn:
                known_ops.add(defn["name"])
        errors = self.validator.validate(definitions, known_ops)
        if errors:
            error_msgs = [str(e) for e in errors]
            raise CompilationError(
                f"Validation failed with {len(errors)} error(s):\n" +
                "\n".join(f"  {msg}" for msg in error_msgs))

        # Generate
        results = []
        for defn in definitions:
            try:
                gen_class = self.generator.generate(defn)
                results.append(gen_class)
            except Exception as e:
                raise CompilationError(
                    f"Failed to generate class for '{defn.get('name', '?')}': {e}")

        # Write to files if output_dir specified
        if output_dir:
            self._write_generated_files(results, output_dir)

        return results

    def _write_generated_files(self, results: List[GeneratedClass], output_dir: str):
        """Write generated classes to Python files."""
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        for gen_class in results:
            file_path = out_path / f"{gen_class.name}.py"
            content = self.generator.generate_file_content(gen_class)
            with open(file_path, "w") as f:
                f.write(content)

        # Generate __init__.py
        self._write_init_file(results, out_path)

    def _write_init_file(self, results: List[GeneratedClass], output_dir: Path):
        """Generate __init__.py with all class imports."""
        init_path = output_dir / "__init__.py"

        lines = ["# Auto-generated by Quantum-Resource-Estimator DSL compiler", ""]

        for gen_class in results:
            lines.append(f"from .{gen_class.name} import {gen_class.name}")

        lines.append("")
        lines.append("__all__ = [")
        for gen_class in results:
            lines.append(f'    "{gen_class.name}",')
        lines.append("]")

        with open(init_path, "w") as f:
            f.write("\n".join(lines))


def compile_yaml(yaml_path: str, output_dir: Optional[str] = None) -> List[GeneratedClass]:
    """Convenience function to compile a YAML file."""
    compiler = DSLCompiler()
    return compiler.compile_file(yaml_path, output_dir)


def compile_all_schemas(output_dir: Optional[str] = None) -> List[GeneratedClass]:
    """Convenience function to compile all schemas."""
    compiler = DSLCompiler()
    return compiler.compile_all(output_dir=output_dir)
