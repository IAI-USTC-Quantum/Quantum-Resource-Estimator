"""
Schema Validator for Quantum-Resource-Estimator DSL YAML definitions (composite-only).

Validates YAML composite operation definitions, checking for required fields,
type consistency, and reference validity.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any


class ValidationError:
    """A single validation error."""

    def __init__(self, path: str, message: str):
        self.path = path
        self.message = message

    def __str__(self):
        return f"[{self.path}] {self.message}"

    def __repr__(self):
        return f"ValidationError({self.path!r}, {self.message!r})"


class SchemaValidator:
    """
    Validates YAML composite operation definitions.

    Checks:
    - Required fields present (name, impl)
    - Type consistency (register types, parameter types)
    - $name references point to declared qregs/params
    - impl operations reference known operations (primitives or composites)
    - controllers format is valid
    """

    VALID_REGISTER_TYPES = {
        "General", "UnsignedInteger", "SignedInteger", "Boolean", "Rational"
    }
    VALID_PARAM_TYPES = {
        "int", "float", "symbol", "array", "object", "str", "bool",
        "callable",   # Python function reference: {"type": "callable", "name": "make_func"}
        "op_instance",  # Operation instance: {"type": "op_instance", "name": "GroverOracle"}
        "qram",         # QRAM circuit object: {"type": "qram", "addr_size": int, "data_size": int, "memory": list}
        "qram_ref",     # Reference to a declared QRAM param: {"type": "qram_ref", "name": "qram"}
        "operation",     # Operation instance passed as constructor argument: {"type": "operation"}
    }

    def __init__(self):
        self.errors: List[ValidationError] = []

    def validate(self, definitions: List[Dict[str, Any]],
                 known_operations: Optional[Set[str]] = None) -> List[ValidationError]:
        """
        Validate a list of YAML composite definitions.

        Args:
            definitions: List of YAML operation definitions
            known_operations: Set of known operation names (primitives + previously defined composites)
        """
        self.errors = []
        all_names: Set[str] = set()
        defined_in_batch: Set[str] = set()

        # Collect all names defined in this batch
        for defn in definitions:
            name = defn.get("name", "")
            if name:
                defined_in_batch.add(name)

        for defn in definitions:
            prefix = defn.get("name", "<unnamed>")
            self._validate_definition(defn, prefix, all_names, known_operations, defined_in_batch)
            all_names.add(defn.get("name", ""))

        return self.errors

    def _validate_definition(self, defn: Dict[str, Any], prefix: str,
                             all_names: Set[str],
                             known_operations: Optional[Set[str]],
                             defined_in_batch: Set[str]):
        """Validate a single composite operation definition."""
        # Required: name
        if "name" not in defn:
            self.errors.append(ValidationError(prefix, "Missing required field 'name'"))
            return

        name = defn["name"]
        path = name

        if not isinstance(name, str) or not name:
            self.errors.append(ValidationError(path, "'name' must be a non-empty string"))
            return

        # PascalCase check
        if not name[0].isupper():
            self.errors.append(ValidationError(path, f"'name' should be PascalCase, got '{name}'"))

        # Optional: qregs
        if "qregs" in defn:
            self._validate_qregs(defn["qregs"], path)

        # Optional: params
        if "params" in defn:
            self._validate_params(defn["params"], path)

        # Optional: temp_regs
        if "temp_regs" in defn:
            self._validate_temp_regs(defn["temp_regs"], path)

        # Required: impl (for composites)
        if "impl" not in defn:
            self.errors.append(ValidationError(path, "Composite operation must have 'impl'"))
        elif not isinstance(defn["impl"], list) or len(defn["impl"]) == 0:
            self.errors.append(ValidationError(f"{path}.impl", "Must be a non-empty list"))
        else:
            self._validate_impl(defn["impl"], defn, path, known_operations, defined_in_batch)

        # Optional: computed_params
        if "computed_params" in defn:
            self._validate_computed_params(defn["computed_params"], path)

        # Optional: self_conjugate
        if "self_conjugate" in defn:
            if not isinstance(defn["self_conjugate"], bool):
                self.errors.append(ValidationError(path, "'self_conjugate' must be a boolean"))

        # Optional: control_override
        if "control_override" in defn:
            if not isinstance(defn["control_override"], str):
                self.errors.append(ValidationError(path, "'control_override' must be a string"))

    def _validate_qregs(self, qregs: Any, path: str):
        """Validate quantum register declarations."""
        if not isinstance(qregs, list):
            self.errors.append(ValidationError(f"{path}.qregs", "Must be a list"))
            return

        for i, reg in enumerate(qregs):
            reg_path = f"{path}.qregs[{i}]"
            if not isinstance(reg, dict):
                self.errors.append(ValidationError(reg_path, "Must be a dict"))
                continue
            if "name" not in reg:
                self.errors.append(ValidationError(reg_path, "Missing 'name'"))
            if "type" not in reg:
                self.errors.append(ValidationError(reg_path, "Missing 'type'"))
            elif reg["type"] not in self.VALID_REGISTER_TYPES:
                self.errors.append(ValidationError(
                    reg_path,
                    f"Invalid register type '{reg['type']}'"
                ))

    def _validate_params(self, params: Any, path: str):
        """Validate classical parameter declarations."""
        if not isinstance(params, list):
            self.errors.append(ValidationError(f"{path}.params", "Must be a list"))
            return

        for i, param in enumerate(params):
            param_path = f"{path}.params[{i}]"
            if not isinstance(param, dict):
                self.errors.append(ValidationError(param_path, "Must be a dict"))
                continue
            if "name" not in param:
                self.errors.append(ValidationError(param_path, "Missing 'name'"))
            if "type" not in param:
                self.errors.append(ValidationError(param_path, "Missing 'type'"))
            elif param["type"] not in self.VALID_PARAM_TYPES:
                self.errors.append(ValidationError(
                    param_path,
                    f"Invalid param type '{param['type']}'"
                ))
            else:
                # Type-specific validation
                ptype = param["type"]
                if ptype == "callable":
                    if "name" not in param or not isinstance(param.get("name"), str):
                        self.errors.append(ValidationError(
                            param_path,
                            "'callable' param requires {'type': 'callable', 'name': '<func_name>'}"
                        ))
                elif ptype == "op_instance":
                    if "name" not in param or not isinstance(param.get("name"), str):
                        self.errors.append(ValidationError(
                            param_path,
                            "'op_instance' param requires {'type': 'op_instance', 'name': '<op_name>'}"
                        ))
                elif ptype == "qram":
                    if "addr_size" not in param:
                        self.errors.append(ValidationError(
                            param_path,
                            "'qram' param requires 'addr_size'"
                        ))
                    if "data_size" not in param:
                        self.errors.append(ValidationError(
                            param_path,
                            "'qram' param requires 'data_size'"
                        ))
                elif ptype == "qram_ref":
                    if "name" not in param or not isinstance(param.get("name"), str):
                        self.errors.append(ValidationError(
                            param_path,
                            "'qram_ref' param requires {'type': 'qram_ref', 'name': '<param_name>'}"
                        ))

    def _validate_temp_regs(self, temp_regs: Any, path: str):
        """Validate temporary register declarations."""
        if not isinstance(temp_regs, list):
            self.errors.append(ValidationError(f"{path}.temp_regs", "Must be a list"))
            return

        for i, reg in enumerate(temp_regs):
            reg_path = f"{path}.temp_regs[{i}]"
            if not isinstance(reg, dict):
                self.errors.append(ValidationError(reg_path, "Must be a dict"))
                continue
            if "name" not in reg:
                self.errors.append(ValidationError(reg_path, "Missing 'name'"))
            if "size" not in reg:
                self.errors.append(ValidationError(reg_path, "Missing 'size'"))

    def _validate_impl(self, impl: List[Dict[str, Any]], parent_defn: Dict[str, Any],
                       path: str, known_operations: Optional[Set[str]],
                       defined_in_batch: Set[str]):
        """Validate an implementation (list of operation calls)."""
        declared_qregs = {r["name"] for r in parent_defn.get("qregs", [])}
        declared_params = {p["name"] for p in parent_defn.get("params", [])}
        declared_temp = {r["name"] for r in parent_defn.get("temp_regs", [])}
        computed = {p["name"] for p in parent_defn.get("computed_params", [])}
        all_names = declared_qregs | declared_params | declared_temp | computed

        for i, call in enumerate(impl):
            call_path = f"{path}.impl[{i}]"

            if not isinstance(call, dict):
                self.errors.append(ValidationError(call_path, "Must be a dict"))
                continue

            # Skip validation for special constructs (loops, conditionals, comments, python blocks)
            # These have different structures
            special_keys = {"loop", "loop_reverse", "if", "comment", "for_each", "python"}
            if any(k in call for k in special_keys):
                self._validate_special_construct(call, all_names, known_operations, defined_in_batch, call_path)
                continue

            if "op" not in call:
                self.errors.append(ValidationError(call_path, "Missing 'op'"))
                continue

            # Check if op is known (allow declared operation params)
            op_name = call["op"]
            declared_op_params = {
                p["name"] for p in parent_defn.get("params", [])
                if isinstance(p, dict) and p.get("type") == "operation"
            }
            if known_operations is not None:
                if (op_name not in known_operations
                        and op_name not in defined_in_batch
                        and op_name not in declared_op_params):
                    self.errors.append(ValidationError(
                        call_path,
                        f"References unknown operation '{op_name}'"
                    ))

            # Validate qregs references
            if "qregs" in call:
                for j, ref in enumerate(call["qregs"]):
                    if isinstance(ref, str) and ref not in all_names:
                        self.errors.append(ValidationError(
                            f"{call_path}.qregs[{j}]",
                            f"Reference '{ref}' not found in declared names"
                        ))

            # Validate params references
            if "params" in call:
                for j, ref in enumerate(call["params"]):
                    # Dict refs are special types (callable/op_instance/qram) - validate by type
                    if isinstance(ref, dict):
                        ptype = ref.get("type")
                        if ptype in ("callable", "op_instance", "qram"):
                            # name-based refs reference declared params (must be in all_names)
                            ref_name = ref.get("name")
                            if isinstance(ref_name, str) and ref_name not in all_names:
                                self.errors.append(ValidationError(
                                    f"{call_path}.params[{j}]",
                                    f"Reference '{ref_name}' not found in declared names"
                                ))
                        else:
                            # Generic dict - treat as potentially invalid
                            pass
                    elif isinstance(ref, str) and ref not in all_names:
                        self.errors.append(ValidationError(
                            f"{call_path}.params[{j}]",
                            f"Reference '{ref}' not found in declared names"
                        ))

            # Validate controllers
            if "controllers" in call:
                self._validate_controllers(call["controllers"], all_names, call_path)

    def _validate_special_construct(self, call: Dict[str, Any], all_names: Set[str],
                                     known_operations: Optional[Set[str]],
                                     defined_in_batch: Set[str], path: str):
        """Validate special constructs like loops, conditionals, comments."""
        # Handle loops
        if "loop" in call:
            loop_def = call["loop"]
            if "body" in loop_def:
                for j, item in enumerate(loop_def["body"]):
                    self._validate_special_construct(item, all_names, known_operations, defined_in_batch, f"{path}.loop.body[{j}]")

        # Handle reverse loops
        if "loop_reverse" in call:
            loop_def = call["loop_reverse"]
            if "body" in loop_def:
                for j, item in enumerate(loop_def["body"]):
                    self._validate_special_construct(item, all_names, known_operations, defined_in_batch, f"{path}.loop_reverse.body[{j}]")

        # Handle conditionals (with optional else/elif)
        if "if" in call:
            cond_def = call["if"]
            cond_path = f"{path}.if"

            if "condition" not in cond_def:
                self.errors.append(ValidationError(cond_path, "Missing 'condition' in if"))

            if "body" in cond_def:
                for j, item in enumerate(cond_def["body"]):
                    self._validate_special_construct(item, all_names, known_operations, defined_in_batch, f"{cond_path}.body[{j}]")

            # Validate else clause
            if "else" in cond_def:
                for j, item in enumerate(cond_def["else"]):
                    self._validate_special_construct(item, all_names, known_operations, defined_in_batch, f"{cond_path}.else[{j}]")

            # Validate elif clauses
            if "elif" in cond_def:
                for ei, elif_def in enumerate(cond_def["elif"]):
                    elif_path = f"{cond_path}.elif[{ei}]"
                    if "condition" not in elif_def:
                        self.errors.append(ValidationError(elif_path, "Missing 'condition' in elif"))
                    if "body" in elif_def:
                        for j, item in enumerate(elif_def["body"]):
                            self._validate_special_construct(item, all_names, known_operations, defined_in_batch, f"{elif_path}.body[{j}]")

        # Handle for_each loops
        if "for_each" in call:
            for_each_def = call["for_each"]
            for_each_path = f"{path}.for_each"

            # Validate required fields
            if "var" not in for_each_def:
                self.errors.append(ValidationError(for_each_path, "Missing 'var' in for_each"))
            if "items" not in for_each_def:
                self.errors.append(ValidationError(for_each_path, "Missing 'items' in for_each"))
            if "body" not in for_each_def:
                self.errors.append(ValidationError(for_each_path, "Missing 'body' in for_each"))

            # Validate body
            if "body" in for_each_def:
                for j, item in enumerate(for_each_def["body"]):
                    self._validate_special_construct(item, all_names, known_operations, defined_in_batch, f"{for_each_path}.body[{j}]")

        # Handle python blocks - no validation needed (user is responsible for code correctness)
        if "python" in call and "op" not in call:
            return

        # Handle comments - no validation needed
        if "comment" in call and "op" not in call:
            return

    def _validate_controllers(self, controllers: Dict[str, Any], all_names: Set[str], path: str):
        """Validate controller definitions."""
        valid_types = {"all_ones", "nonzero", "bit", "value"}

        for ctrl_type, ctrl_list in controllers.items():
            ctrl_path = f"{path}.controllers.{ctrl_type}"

            if ctrl_type not in valid_types:
                self.errors.append(ValidationError(
                    ctrl_path,
                    f"Invalid controller type '{ctrl_type}'"
                ))
                continue

            if not isinstance(ctrl_list, list):
                self.errors.append(ValidationError(ctrl_path, "Must be a list"))
                continue

            if ctrl_type in ("all_ones", "nonzero"):
                for j, ref in enumerate(ctrl_list):
                    if isinstance(ref, str) and ref not in all_names:
                        self.errors.append(ValidationError(
                            f"{ctrl_path}[{j}]",
                            f"Reference '{ref}' not found in declared names"
                        ))

            elif ctrl_type in ("bit", "value"):
                for j, pair in enumerate(ctrl_list):
                    if not isinstance(pair, list) or len(pair) != 2:
                        self.errors.append(ValidationError(
                            f"{ctrl_path}[{j}]",
                            "Must be [register_name, value] pair"
                        ))
                    elif isinstance(pair[0], str) and pair[0] not in all_names:
                        self.errors.append(ValidationError(
                            f"{ctrl_path}[{j}]",
                            f"Reference '{pair[0]}' not found in declared names"
                        ))

    def _validate_computed_params(self, computed_params: Any, path: str):
        """Validate computed parameter declarations."""
        if not isinstance(computed_params, list):
            self.errors.append(ValidationError(f"{path}.computed_params", "Must be a list"))
            return

        for i, param in enumerate(computed_params):
            param_path = f"{path}.computed_params[{i}]"
            if not isinstance(param, dict):
                self.errors.append(ValidationError(param_path, "Must be a dict"))
                continue
            if "name" not in param:
                self.errors.append(ValidationError(param_path, "Missing 'name'"))
            if "formula" not in param:
                self.errors.append(ValidationError(param_path, "Missing 'formula'"))


def validate_yaml_definitions(definitions: List[Dict[str, Any]],
                               known_operations: Optional[Set[str]] = None) -> List[ValidationError]:
    """Convenience function to validate YAML definitions."""
    validator = SchemaValidator()
    return validator.validate(definitions, known_operations)


class PrimitiveSchemaValidator:
    """
    Validates primitive set definitions.

    A primitive set defines which operations are considered atomic
    (not lowered further).
    """

    def __init__(self):
        self.errors: List[ValidationError] = []

    def validate(self, definition: Dict[str, Any]) -> List[ValidationError]:
        """
        Validate a primitive set definition.

        Args:
            definition: YAML primitive set definition

        Returns:
            List of validation errors
        """
        self.errors = []
        self._validate_definition(definition, "")
        return self.errors

    def _validate_definition(self, defn: Dict[str, Any], path: str):
        """Validate a single primitive set definition."""
        # Required: name
        if "name" not in defn:
            self.errors.append(ValidationError(path, "Missing required field 'name'"))
            return

        name = defn["name"]
        path = name

        if not isinstance(name, str) or not name:
            self.errors.append(ValidationError(path, "'name' must be a non-empty string"))
            return

        # Required: primitives
        if "primitives" not in defn:
            self.errors.append(ValidationError(path, "Missing required field 'primitives'"))
            return

        primitives = defn["primitives"]
        if not isinstance(primitives, list):
            self.errors.append(ValidationError(path, "'primitives' must be a list"))
            return

        if len(primitives) == 0:
            self.errors.append(ValidationError(path, "'primitives' cannot be empty"))
            return

        # Validate each primitive name
        for i, prim in enumerate(primitives):
            prim_path = f"{path}.primitives[{i}]"
            if not isinstance(prim, str):
                self.errors.append(ValidationError(prim_path, "Primitive name must be a string"))
            elif not prim:
                self.errors.append(ValidationError(prim_path, "Primitive name cannot be empty"))


def validate_primitive_definition(definition: Dict[str, Any]) -> List[ValidationError]:
    """Convenience function to validate a primitive set definition."""
    validator = PrimitiveSchemaValidator()
    return validator.validate(definition)
