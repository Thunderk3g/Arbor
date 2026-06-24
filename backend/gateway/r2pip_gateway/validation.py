"""Minimal JSON-Schema-subset argument validation (gateway pipeline step 1).

Supports: required keys, per-property "type" for string/integer/number/boolean/
object/array, and "enum" membership. No external jsonschema dependency.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping

_TYPE_CHECKS = {
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
}


def validate_args(args: Dict[str, Any], input_schema: Mapping[str, Any]) -> List[str]:
    """Return a list of violation strings; empty list means the args conform."""
    violations: List[str] = []

    for key in input_schema.get("required", []):
        if key not in args:
            violations.append(f"missing_required:{key}")

    properties: Mapping[str, Any] = input_schema.get("properties", {})
    for key, prop in properties.items():
        if key not in args:
            continue
        value = args[key]
        expected_type = prop.get("type")
        if expected_type in _TYPE_CHECKS and not _TYPE_CHECKS[expected_type](value):
            violations.append(f"type_mismatch:{key}:expected_{expected_type}")
            continue
        if "enum" in prop and value not in prop["enum"]:
            violations.append(f"enum_violation:{key}")

    return violations
