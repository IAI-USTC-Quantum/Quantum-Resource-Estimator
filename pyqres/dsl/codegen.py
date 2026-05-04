"""
Code Generator for Quantum-Resource-Estimator DSL (composite-only).

Generates Python Composite subclasses from YAML composite operation definitions.
Handles loops, conditionals, and computed parameters.
"""

from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class GeneratedClass:
    """Container for a generated Python class."""
    name: str
    base_class: str  # Composite, StandardComposite, AbstractComposite
    imports: List[str]
    class_code: str
    dependencies: List[str]  # Other operations referenced


class CodeGenerator:
    """
    Generate Python Composite subclasses from YAML composite definitions.

    Handles:
    - $name variable substitution
    - Controllers (all_ones, nonzero, bit, value)
    - Dagger modifiers
    - Temporary registers lifecycle
    - Computed parameters
    - traverse_override for special patterns
    - Loops (loop, loop_reverse)
    - Conditionals (if)
    - Comments
    """

    STANDARD_IMPORTS = [
        "from ..core.operation import {base_class}",
        "from ..core.registry import OperationRegistry",
        "from ..core.utils import merge_controllers",
        "import math",
    ]

    def generate(self, definition: Dict[str, Any]) -> GeneratedClass:
        """Generate a Python class from a YAML composite definition."""
        return self._generate_composite(definition)

    def _generate_composite(self, defn: Dict[str, Any]) -> GeneratedClass:
        """Generate a Composite subclass for a composed operation."""
        name = defn["name"]
        has_custom_sum = defn.get("sum_t_count_formula") == "custom"
        base_class = "AbstractComposite" if has_custom_sum else "StandardComposite"
        # Store param type map for for_each range() vs direct-iteration decisions
        self._param_type_map = {p["name"]: p.get("type", "int") for p in defn.get("params", [])}

        # Store declared operation params for symbol lookup
        # When op name matches a declared 'type: operation' param, generate self.{name}() instead of OperationRegistry.get_class()
        self._declared_op_params = {
            p["name"] for p in defn.get("params", [])
            if isinstance(p, dict) and p.get("type") == "operation"
        }

        imports = self._generate_imports(base_class, defn)

        # Extract dependencies from impl
        dependencies = []
        for call in defn.get("impl", []):
            if "op" in call:
                dependencies.append(call["op"])

        # Build class code
        lines = []
        lines.append(f"class {name}({base_class}):")

        # Self-conjugate attribute
        if defn.get("self_conjugate", False):
            lines.append("    __self_conjugate__ = True")

        # Docstring
        desc = defn.get("description", f"{name} composite operation")
        lines.append(f'    """{desc}"""')

        # __init__ with program_list
        init_code = self._generate_init(defn, base_class)
        lines.extend(init_code)

        # Check if impl has complex structures (loops/conditionals)
        impl = defn.get("impl", [])
        has_complex_impl = any(self._is_complex_impl_item(item) for item in impl)

        # For complex implementations, generate the execute method
        if has_complex_impl:
            body_code = self._generate_class_body(defn)
            lines.extend(body_code)

        # Optional: control_children override
        control_override = defn.get("control_override")
        if control_override:
            control_code = self._generate_control_override(control_override)
            lines.extend(control_code)

        class_code = "\n".join(lines)

        return GeneratedClass(
            name=name,
            base_class=base_class,
            imports=imports,
            class_code=class_code,
            dependencies=dependencies
        )

    def _generate_imports(self, base_class: str, defn: Dict[str, Any] = None) -> List[str]:
        """Generate import statements for the generated file.

        Args:
            base_class: Base class (StandardComposite, AbstractComposite)
            defn: YAML definition dict (used to detect needed imports)
        """
        imports = [imp.format(base_class=base_class) for imp in self.STANDARD_IMPORTS]

        # Add pysparq import if any param uses qram type
        if defn:
            for param in defn.get("params", []):
                if isinstance(param, dict) and param.get("type") == "qram":
                    if "import pysparq as ps" not in imports:
                        imports.append("import pysparq as ps")
                    break
            # Add callable imports based on referenced function names
            for param in defn.get("params", []):
                if isinstance(param, dict) and param.get("type") == "callable":
                    func_name = param.get("name", "")
                    if func_name in ("make_func", "make_func_inv"):
                        if "from ..algorithms.state_prep import make_func, make_func_inv" not in imports:
                            imports.append("from ..algorithms.state_prep import make_func, make_func_inv")

            # Extract imports from python: blocks in impl (including nested loop.body)
            seen = set(imports)
            for item in self._flatten_impl_items(defn.get("impl", [])):
                if isinstance(item, dict) and "python" in item:
                    for line in item["python"].strip().split("\n"):
                        stripped = line.strip()
                        if stripped.startswith("from ") or stripped.startswith("import "):
                            if stripped not in seen:
                                imports.append(stripped)
                                seen.add(stripped)

        return imports

    def _generate_init(self, defn: Dict[str, Any], base_class: str = "StandardComposite") -> List[str]:
        """Generate __init__ for a composite operation."""
        lines = []

        qregs = defn.get("qregs", [])
        params = defn.get("params", [])
        temp_regs = defn.get("temp_regs", [])
        computed_params = defn.get("computed_params", [])

        has_params = len(params) > 0
        has_temp = len(temp_regs) > 0

        # Check if impl has any loops or conditionals (requires special handling)
        impl = defn.get("impl", [])
        has_complex_impl = any(self._is_complex_impl_item(item) for item in impl)

        # Build signature
        sig_parts = ["reg_list"]
        if has_params:
            sig_parts.append("param_list=None")
        if has_temp:
            temp_default = "[" + ", ".join(
                f"('{r['name']}', {r['size']})" for r in temp_regs
            ) + "]"
            sig_parts.append(f"temp_reg_list={temp_default}")
        sig_parts.append("operations=None")

        lines.append(f"    def __init__(self, {', '.join(sig_parts)}):")

        # Handle optional param_list
        if has_params:
            lines.append("        if param_list is None:")
            lines.append("            param_list = []")

        # super().__init__ call using base_class directly
        super_args = ["self", "reg_list=reg_list"]
        if has_params:
            super_args.append("param_list=param_list")
        if has_temp:
            super_args.append("temp_reg_list=temp_reg_list")
        super_args.append("operations=operations")
        lines.append(f"        {base_class}.__init__({', '.join(super_args)})")

        # Register attributes
        for i, qr in enumerate(qregs):
            lines.append(f"        self.{qr['name']} = reg_list[{i}]")

        # Param attributes (skip operation params — those are stored from operations list instead)
        if has_params:
            for i, p in enumerate(params):
                if isinstance(p, dict) and p.get("type") == "operation":
                    continue  # stored from operations list below
                lines.append(f"        self.{p['name']} = param_list[{i}]")

        # Computed params - use self. prefix for self references
        # Only replace exact word matches for parameter names (not substrings)
        param_names_set = {p["name"] for p in params}
        computed_names_set = {cp["name"] for cp in computed_params}
        import re
        for idx, cp in enumerate(computed_params):
            formula = cp.get("formula", "")
            # Replace param names first
            for pname in param_names_set:
                pattern = r'\b' + re.escape(pname) + r'\b'
                formula = re.sub(pattern, f"self.{pname}", formula)
            # Replace earlier computed param names (only those defined before this one)
            for prev_cp in computed_params[:idx]:
                cpname = prev_cp["name"]
                pattern = r'\b' + re.escape(cpname) + r'\b'
                formula = re.sub(pattern, f"self.{cpname}", formula)
            lines.append(f"        self.{cp['name']} = {formula.strip()}")

        # Temp register attributes (stored as dict for easy lookup)
        if has_temp:
            lines.append("        # Store temp registers as instance attributes")
            lines.append("        self._temp_reg_dict = {}")
            for temp_reg in temp_regs:
                name = temp_reg['name']
                size = temp_reg['size']
                lines.append(f"        self._temp_reg_dict['{name}'] = ('{name}', {size})")
                lines.append(f"        self.{name} = '{name}'")

        # Store operation params (type: operation) as instance attributes from the operations list
        op_names = [
            p["name"] for p in params
            if isinstance(p, dict) and p.get("type") == "operation"
        ]
        if op_names:
            lines.append("        if operations is None:")
            lines.append("            operations = []")
            for i, name in enumerate(op_names):
                lines.append(f"        self.{name} = operations[{i}] if {i} < len(operations) else None")

        # Build program_list (only for simple implementations without loops/conditionals)
        if impl and not has_complex_impl:
            lines.append("        self.program_list = [")
            for call in impl:
                item_code = self._generate_impl_item(call)
                lines.append(f"            {item_code},")
            lines.append("        ]")
            lines.append("        self.declare_program_list()")
        elif has_complex_impl:
            # For complex implementations, store the impl structure and generate execute method
            lines.append("        # Complex implementation with loops/conditionals")
            lines.append("        self._impl_structure = " + self._serialize_impl(impl))
            lines.append("        self._build_execute_method()")

        return lines

    def _flatten_impl_items(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Recursively flatten impl items, including those nested in loop.body/for_each.body."""
        flat = []
        for item in items:
            if isinstance(item, dict):
                if "loop" in item:
                    flat.extend(self._flatten_impl_items(item.get("loop", {}).get("body", [])))
                elif "loop_reverse" in item:
                    flat.extend(self._flatten_impl_items(item.get("loop_reverse", {}).get("body", [])))
                elif "for_each" in item:
                    flat.extend(self._flatten_impl_items(item.get("for_each", {}).get("body", [])))
                elif "if" in item:
                    flat.extend(self._flatten_impl_items(item.get("if", {}).get("then", [])))
                    flat.extend(self._flatten_impl_items(item.get("if", {}).get("else", [])))
                else:
                    flat.append(item)
        return flat

    def _is_complex_impl_item(self, item: Dict[str, Any]) -> bool:
        """Check if an impl item requires complex handling (loops, conditionals, etc.)."""
        return any(k in item for k in ("loop", "loop_reverse", "if", "comment", "for_each", "python"))

    def _serialize_impl(self, impl: List[Dict[str, Any]]) -> str:
        """Serialize the impl structure for storage."""
        import json
        # Convert to JSON-serializable form
        serializable = self._make_serializable(impl)
        return json.dumps(serializable)

    def _make_serializable(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert impl items to JSON-serializable format."""
        result = []
        for item in items:
            if "comment" in item and "op" not in item:
                result.append({"_type": "comment", "text": item["comment"]})
            elif "loop" in item:
                result.append({"_type": "loop", "iterations": item["loop"]["iterations"], "body": self._make_serializable(item["loop"]["body"])})
            elif "loop_reverse" in item:
                result.append({"_type": "loop_reverse", "iterations": item["loop_reverse"]["iterations"], "body": self._make_serializable(item["loop_reverse"]["body"])})
            elif "for_each" in item:
                result.append({
                    "_type": "for_each",
                    "var": item["for_each"]["var"],
                    "items": item["for_each"]["items"],
                    "body": self._make_serializable(item["for_each"]["body"])
                })
            elif "if" in item:
                if_data = {"_type": "if", "condition": item["if"]["condition"], "body": self._make_serializable(item["if"]["body"])}
                if "else" in item["if"]:
                    if_data["else"] = self._make_serializable(item["if"]["else"])
                if "elif" in item["if"]:
                    if_data["elif"] = [{"condition": e["condition"], "body": self._make_serializable(e["body"])} for e in item["if"]["elif"]]
                result.append(if_data)
            elif "python" in item:
                result.append({"_type": "python", "code": item["python"]})
            elif "op" in item:
                new_item = {"_type": "op", "op": item["op"]}
                if "qregs" in item:
                    new_item["qregs"] = item["qregs"]
                if "params" in item:
                    new_item["params"] = item["params"]
                if "dagger" in item:
                    new_item["dagger"] = item["dagger"]
                if "controllers" in item:
                    new_item["controllers"] = item["controllers"]
                result.append(new_item)
        return result

    def _generate_class_body(self, defn: Dict[str, Any]) -> List[str]:
        """Generate the class body with execute method for complex implementations."""
        impl = defn.get("impl", [])
        params = defn.get("params", [])
        computed_params = defn.get("computed_params", [])
        param_names = [p["name"] for p in params] + [p["name"] for p in computed_params]

        lines = []

        # Generate _build_execute_method
        lines.append("")
        lines.append("    def _build_execute_method(self):")
        lines.append("        # Build program_list by expanding loops and conditionals")
        lines.append("        self.program_list = []")

        for call in impl:
            # Skip top-level python: blocks that contain only import statements
            # (those are handled by _generate_imports and don't need to be in the method body)
            if isinstance(call, dict) and call.get("python") is not None:
                code = call["python"]
                non_import_lines = [l.strip() for l in code.strip().split("\n")
                                    if l.strip() and not l.strip().startswith(("from ", "import "))]
                if not non_import_lines:
                    continue
            self._add_impl_lines(lines, call, "        ", depth=1, param_names=param_names)

        lines.append("        self.declare_program_list()")

        return lines

    def _add_impl_lines(self, lines: List[str], call: Dict[str, Any], indent: str, depth: int,
                        param_names: List[str] = None, local_vars: Dict[str, str] = None):
        """Add implementation lines recursively."""
        prefix = indent * depth

        # Handle standalone comments (not inside an op)
        if "comment" in call and "op" not in call and len(call) == 1:
            lines.append(f"{prefix}# {call['comment']}")
            return

        # Handle python code blocks - insert code directly
        if "python" in call:
            python_code = call["python"]
            # Handle multi-line code, substituting $self references
            code_lines = python_code.strip().split("\n")
            for code_line in code_lines:
                resolved = self._resolve_python_block_line(code_line, param_names, local_vars)
                lines.append(f"{prefix}{resolved}")
            return

        if "loop" in call:
            iterations = call["loop"]["iterations"]
            body = call["loop"]["body"]
            iter_expr = self._resolve_loop_expr(iterations, param_names, local_vars)
            lines.append(f"{prefix}for i in range({iter_expr}):")
            for item in body:
                self._add_impl_lines(lines, item, indent, depth + 1, param_names, local_vars)
            return

        if "loop_reverse" in call:
            iterations = call["loop_reverse"]["iterations"]
            body = call["loop_reverse"]["body"]
            iter_expr = self._resolve_loop_expr(iterations, param_names, local_vars)
            lines.append(f"{prefix}for i in range({iter_expr} - 1, -1, -1):")
            for item in body:
                self._add_impl_lines(lines, item, indent, depth + 1, param_names, local_vars)
            return

        if "for_each" in call:
            for_each_def = call["for_each"]
            var_name = for_each_def["var"]
            items = for_each_def["items"]
            body = for_each_def["body"]

            items_expr = self._resolve_for_each_items_expr(items, param_names, local_vars)

            lines.append(f"{prefix}for {var_name} in {items_expr}:")

            # Create local vars for $var substitution
            new_local_vars = dict(local_vars or {})
            new_local_vars[var_name] = var_name  # Use variable directly (no $ prefix in generated code)

            for item in body:
                self._add_impl_lines(lines, item, indent, depth + 1, param_names, new_local_vars)
            return

        if "if" in call:
            if_def = call["if"]
            condition = self._resolve_expr(if_def["condition"], param_names, local_vars)
            body = if_def["body"]

            lines.append(f"{prefix}if {condition}:")
            for item in body:
                self._add_impl_lines(lines, item, indent, depth + 1, param_names, local_vars)

            # Handle elif
            if "elif" in if_def:
                for elif_def in if_def["elif"]:
                    elif_condition = self._resolve_expr(elif_def["condition"], param_names, local_vars)
                    elif_body = elif_def["body"]
                    lines.append(f"{prefix}elif {elif_condition}:")
                    for item in elif_body:
                        self._add_impl_lines(lines, item, indent, depth + 1, param_names, local_vars)

            # Handle else
            if "else" in if_def:
                else_body = if_def["else"]
                lines.append(f"{prefix}else:")
                for item in else_body:
                    self._add_impl_lines(lines, item, indent, depth + 1, param_names, local_vars)
            return

        # Regular operation
        op_name = call.get("op", "")
        args = []

        qregs_refs = call.get("qregs", [])
        if qregs_refs:
            qregs_str = ", ".join(f"self.{r}" for r in qregs_refs)
            args.append(f"reg_list=[{qregs_str}]")

        params_refs = call.get("params", [])
        if params_refs:
            resolved_params = []
            for p in params_refs:
                resolved_params.append(self._resolve_param_ref(p, param_names, local_vars))
            params_str = ", ".join(resolved_params)
            args.append(f"param_list=[{params_str}]")

        # Symbol lookup: if op_name is a declared 'type: operation' param, use self.{name}()
        # Otherwise, use OperationRegistry.get_class() for registered operations
        if self._declared_op_params and op_name in self._declared_op_params:
            base = f'self.{op_name}({", ".join(args)})'
        else:
            base = f'OperationRegistry.get_class("{op_name}")({", ".join(args)})'

        if call.get("dagger"):
            base += ".dagger()"

        controllers = call.get("controllers", {})
        if controllers:
            base += self._generate_controller_chain(controllers)

        lines.append(f"{prefix}self.program_list.append({base})")

    def _generate_impl_item(self, call: Dict[str, Any], local_vars: Dict[str, Any] = None) -> str:
        """Generate a single item in program_list.

        Args:
            call: The operation call dictionary
            local_vars: Local variables (like $iteration) for template substitution
        """
        # Handle comments (skip)
        if "comment" in call and "op" not in call:
            return "# " + call["comment"]

        # Handle loops
        if "loop" in call:
            return self._generate_loop(call["loop"], local_vars)
        if "loop_reverse" in call:
            return self._generate_loop(call["loop_reverse"], local_vars, reverse=True)

        # Handle for_each
        if "for_each" in call:
            return self._generate_for_each(call["for_each"], local_vars)

        # Handle conditionals
        if "if" in call:
            return self._generate_conditional(call["if"], local_vars)

        op_name = call.get("op", "")

        # Build: OperationRegistry.get_class("OpName")(args)
        args = []

        # reg_list
        qregs_refs = call.get("qregs", [])
        if qregs_refs:
            qregs_str = ", ".join(f"self.{self._substitute(r, local_vars)}" for r in qregs_refs)
            args.append(f"reg_list=[{qregs_str}]")

        # param_list
        params_refs = call.get("params", [])
        if params_refs:
            params_str = ", ".join(self._resolve_param_ref(p, local_vars=local_vars) for p in params_refs)
            args.append(f"param_list=[{params_str}]")

        # temp_out for operations with temporary output registers
        temp_out = call.get("temp_out")
        if temp_out:
            args.append(f"# temp_out: {temp_out}")

        # Symbol lookup: if op_name is a declared 'type: operation' param, use self.{name}()
        # Otherwise, use OperationRegistry.get_class() for registered operations
        if self._declared_op_params and op_name in self._declared_op_params:
            base = f'self.{op_name}({", ".join(args)})'
        else:
            base = f'OperationRegistry.get_class("{op_name}")({", ".join(args)})'

        # dagger
        if call.get("dagger"):
            base += ".dagger()"

        # controllers
        controllers = call.get("controllers", {})
        if controllers:
            base += self._generate_controller_chain(controllers)

        return base

    def _substitute(self, value: str, local_vars: Dict[str, Any] = None) -> str:
        """Substitute template variables like $iteration."""
        if local_vars and isinstance(value, str):
            result = value
            for var_name, var_value in (local_vars or {}).items():
                result = result.replace(f"${var_name}", str(var_value))
            return result
        return value

    def _generate_loop(self, loop_def: Dict[str, Any], local_vars: Dict[str, Any] = None, reverse: bool = False) -> str:
        """Generate a for loop."""
        iterations = loop_def.get("iterations")
        body = loop_def.get("body", [])

        # Handle numeric iterations directly (no self. prefix for numbers)
        if isinstance(iterations, (int, float)):
            iter_expr = str(iterations)
        elif isinstance(iterations, str):
            iter_expr = f"self.{iterations}"
        else:
            iter_expr = str(iterations)

        lines = []
        iter_var = "i" if not reverse else "i_reverse"
        extra_vars = {"iteration": iter_var}
        lines.append(f"# Loop: {iterations} iterations")
        if reverse:
            lines.append(f"for {iter_var} in range({iter_expr} - 1, -1, -1):")
        else:
            lines.append(f"for {iter_var} in range({iter_expr}):")

        # Add body with iteration context
        indent = "    "
        for item in body:
            merged_vars = dict(local_vars or {})
            merged_vars.update(extra_vars)
            item_str = self._generate_impl_item(item, merged_vars)
            if item_str.startswith("#"):
                lines.append(f"{indent}{item_str}")
            else:
                lines.append(f"{indent}{item_str},")

        return "\n".join(lines)

    def _generate_conditional(self, cond_def: Dict[str, Any], local_vars: Dict[str, Any] = None) -> str:
        """Generate an if statement with optional else/elif."""
        condition = cond_def.get("condition", "")
        body = cond_def.get("body", [])

        lines = []
        lines.append(f"# Conditional: {condition}")
        lines.append(f"if {condition}:")
        indent = "    "
        for item in body:
            item_str = self._generate_impl_item(item, local_vars)
            if item_str.startswith("#"):
                lines.append(f"{indent}{item_str}")
            else:
                lines.append(f"{indent}{item_str},")

        # Handle elif
        if "elif" in cond_def:
            for elif_def in cond_def["elif"]:
                elif_condition = elif_def.get("condition", "")
                elif_body = elif_def.get("body", [])
                lines.append(f"elif {elif_condition}:")
                for item in elif_body:
                    item_str = self._generate_impl_item(item, local_vars)
                    if item_str.startswith("#"):
                        lines.append(f"{indent}{item_str}")
                    else:
                        lines.append(f"{indent}{item_str},")

        # Handle else
        if "else" in cond_def:
            else_body = cond_def["else"]
            lines.append("else:")
            for item in else_body:
                item_str = self._generate_impl_item(item, local_vars)
                if item_str.startswith("#"):
                    lines.append(f"{indent}{item_str}")
                else:
                    lines.append(f"{indent}{item_str},")

        return "\n".join(lines)

    def _generate_for_each(self, for_each_def: Dict[str, Any], local_vars: Dict[str, Any] = None) -> str:
        """Generate a for_each loop."""
        var_name = for_each_def.get("var", "item")
        items = for_each_def.get("items", [])
        body = for_each_def.get("body", [])

        items_expr = self._resolve_for_each_items_expr(items, local_vars=local_vars)

        lines = []
        lines.append(f"# For-each loop over {items_expr}")
        lines.append(f"for {var_name} in {items_expr}:")

        indent = "    "
        for item in body:
            # Add iteration variable to local vars for $var substitution
            merged_vars = dict(local_vars or {})
            merged_vars[var_name] = var_name
            item_str = self._generate_impl_item(item, merged_vars)
            if item_str.startswith("#"):
                lines.append(f"{indent}{item_str}")
            else:
                lines.append(f"{indent}{item_str},")

        return "\n".join(lines)

    def _resolve_param_ref(self, ref: Any, param_names: List[str] = None, local_vars: Dict[str, str] = None) -> str:
        """Resolve a parameter reference to Python code.

        Args:
            ref: Parameter value (could be string, number, list, or template)
            param_names: List of declared parameter names
            local_vars: Local variables for $var substitution (for_each iteration vars)
        """
        if isinstance(ref, str):
            # Handle $var references from for_each - use the variable directly
            if ref.startswith("$") and local_vars:
                var_name = ref[1:]  # Remove $ prefix
                if var_name in local_vars:
                    return var_name  # Use the iteration variable directly (e.g., "angle" not "self.angle")

            # Handle self. prefix - keep as-is
            if ref.startswith("self."):
                return ref

            # Template substitution for $name references
            result = ref
            if local_vars:
                for var_name, var_value in local_vars.items():
                    result = result.replace(f"${var_name}", str(var_value))

            # If it's still a $ reference that wasn't resolved, it might be a for_each var
            if result.startswith("$") and local_vars:
                var_name = result[1:]
                if var_name in local_vars:
                    return var_name

            # Check if it's a Python keyword
            if result in ("True", "False", "None"):
                return result

            # If it looks like a param reference, add self. prefix
            if param_names and result in param_names:
                return f"self.{result}"

            # Default: add self. prefix for backwards compatibility
            return f"self.{result}"
        elif isinstance(ref, (int, float)):
            return str(ref)
        elif isinstance(ref, list):
            items = ", ".join(self._resolve_param_ref(item, param_names, local_vars) for item in ref)
            return f"[{items}]"
        elif isinstance(ref, dict):
            # New complex param types
            ptype = ref.get("type")
            if ptype == "callable":
                # {"type": "callable", "name": "make_func"}
                # Returns the Python symbol name (imported separately by _generate_imports)
                return ref.get("name", "make_func")
            elif ptype == "op_instance":
                # {"type": "op_instance", "name": "GroverOracle", "args": [...]}
                op_name = ref.get("name", "")
                args = ref.get("args", [])
                if args:
                    args_str = ", ".join(
                        self._resolve_param_ref(a, param_names, local_vars)
                        for a in args
                    )
                    return f'OperationRegistry.get_class("{op_name}")({args_str})'
                return f'OperationRegistry.get_class("{op_name}")()'
            elif ptype == "qram":
                # {"type": "qram", "addr_size": int, "data_size": int, "memory": list}
                addr = ref.get("addr_size", 0)
                data = ref.get("data_size", 0)
                mem = ref.get("memory", [])
                mem_str = repr(mem)
                return f"ps.QRAMCircuit_qutrit({addr}, {data}, {mem_str})"
            elif ptype == "qram_ref":
                # {"type": "qram_ref", "name": "qram_param"}
                # Reference to a declared param that holds a QRAM circuit
                ref_name = ref.get("name", "")
                if param_names and ref_name in param_names:
                    return f"self.{ref_name}"
                return ref_name
            elif ptype == "literal":
                return repr(ref.get("value"))
            elif ptype == "expr":
                return self._resolve_expr(str(ref.get("value", "")), param_names, local_vars)
            else:
                return str(ref)
        else:
            return str(ref)

    def _resolve_loop_expr(self, expr: Any, param_names: List[str] = None,
                           local_vars: Dict[str, str] = None) -> str:
        """Resolve a loop iteration expression for range(...)."""
        if isinstance(expr, (int, float)):
            return str(expr)
        if isinstance(expr, dict) and expr.get("type") == "expr":
            return self._resolve_expr(str(expr.get("value", "")), param_names, local_vars)
        if isinstance(expr, str):
            if param_names and expr in param_names:
                return f"self.{expr}"
            return self._resolve_expr(expr, param_names, local_vars)
        return str(expr)

    def _resolve_for_each_items_expr(self, items: Any, param_names: List[str] = None,
                                     local_vars: Dict[str, str] = None) -> str:
        """Resolve a for_each items source expression."""
        if isinstance(items, list):
            return repr(items)
        if isinstance(items, dict):
            ptype = items.get("type")
            if ptype == "literal":
                return repr(items.get("value"))
            if ptype == "expr":
                return self._resolve_expr(str(items.get("value", "")), param_names, local_vars)
        if isinstance(items, str):
            ptype = self._param_type_map.get(items, "int")
            if ptype in ("array", "list"):
                return f"self.{items}"
            return f"range(self.{items})"
        return str(items)

    def _resolve_expr(self, expr: str, param_names: List[str] = None,
                      local_vars: Dict[str, str] = None) -> str:
        """Resolve a YAML expression into generated Python code."""
        import re as _re

        # If expression already starts with "self.", it's already fully qualified,
        # so avoid adding another "self." prefix (prevents self.self.x)
        if expr.lstrip().startswith("self."):
            return expr

        result = expr
        local_names = set(local_vars or {})
        if param_names:
            for pname in param_names:
                if pname in local_names:
                    continue
                pattern = r'\b' + _re.escape(pname) + r'\b'
                result = _re.sub(pattern, f"self.{pname}", result)
        return result

    def _generate_controller_chain(self, controllers: Dict[str, Any]) -> str:
        """Generate controller method chain."""
        chain = ""

        if "all_ones" in controllers:
            refs = controllers["all_ones"]
            refs_str = ", ".join(f"self.{r}" for r in refs)
            chain += f".control_by_all_ones([{refs_str}])"

        if "nonzero" in controllers:
            refs = controllers["nonzero"]
            refs_str = ", ".join(f"self.{r}" for r in refs)
            chain += f".control_by_nonzero([{refs_str}])"

        if "bit" in controllers:
            pairs = controllers["bit"]
            pairs_str = ", ".join(f"(self.{p[0]}, {p[1]})" for p in pairs)
            chain += f".control_by_bit([{pairs_str}])"

        if "value" in controllers:
            pairs = controllers["value"]
            pairs_str = ", ".join(f"(self.{p[0]}, {p[1]})" for p in pairs)
            chain += f".control_by_value([{pairs_str}])"

        return chain

    def _generate_control_override(self, override_type: str) -> List[str]:
        """Generate traverse_children override for special controller propagation patterns."""
        lines = []

        if override_type == "cnot_swap":
            # Swap operation's special control propagation
            # Only the middle CNOT receives controllers
            lines.append("    def traverse_children(self, visitor, dagger_ctx=False, controllers_ctx=None):")
            lines.append("        controllers_ctx = controllers_ctx or {}")
            lines.append("        controllers = merge_controllers(self.controllers, controllers_ctx)")
            lines.append("        self.program_list[0].traverse(visitor, False, {})")
            lines.append("        self.program_list[1].traverse(visitor, False, controllers)")
            lines.append("        self.program_list[2].traverse(visitor, False, {})")
        else:
            lines.append("    def traverse_children(self, visitor, dagger_ctx=False, controllers_ctx=None):")
            lines.append(f"        # Control override type: {override_type}")
            lines.append(f"        raise NotImplementedError(\"control override '{override_type}' not implemented\")")

        return lines

    def _resolve_python_block_line(self, code_line: str,
                                    param_names: List[str] = None,
                                    local_vars: Dict[str, str] = None) -> str:
        """Resolve $self.XXX references in a python block code line.

        Substitutes bare identifiers that match declared param names with self.XXX.
        Also handles $var references from for_each loops.
        """
        import re as _re
        result = code_line

        # Substitute $var references (for_each loop variables)
        if local_vars:
            for var_name, var_value in local_vars.items():
                result = result.replace(f"${var_name}", var_value)

        # Substitute bare param names with self.param_name (only in word boundaries)
        if param_names:
            for pname in param_names:
                # Match $pname as a word boundary token (not inside a string)
                # Simple approach: replace $pname with self.pname
                pattern = r'\$' + _re.escape(pname) + r'\b'
                result = _re.sub(pattern, f"self.{pname}", result)

        return result

    def generate_file_content(self, gen_class: GeneratedClass) -> str:
        """Generate complete file content for a generated class."""
        lines = []
        lines.append("# Generated from YAML definition")
        lines.append("")
        for imp in gen_class.imports:
            lines.append(imp)
        lines.append("")
        lines.append(gen_class.class_code)
        return "\n".join(lines)


def generate_class(definition: Dict[str, Any]) -> GeneratedClass:
    """Convenience function to generate a class from definition."""
    generator = CodeGenerator()
    return generator.generate(definition)
