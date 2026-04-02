"""Schema $ref resolution for CTMS canonicalization (Section 3.2, step 3).

Rules:
- Only fragment-only $ref (#/...) allowed. External refs are rejected.
- Cycles must be detected before resolution begins.
- After resolution, $defs and definitions are removed at all levels.
- Composition keywords (oneOf, anyOf, allOf, if/then/else) are preserved as-is.
"""

from __future__ import annotations

import copy
from typing import Any

from ctms.errors import DereferenceError


def dereference_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Resolve all $ref pointers in a JSON Schema, producing a self-contained schema.

    Returns a new dict with all $ref replaced by inlined content, $defs/$definitions
    removed, and composition keywords preserved.
    """
    schema = copy.deepcopy(schema)

    definitions = _collect_definitions(schema)
    _detect_cycles(schema, definitions)
    resolved = _walk_and_resolve(schema, definitions)
    result = _strip_defs(resolved)

    return result


def _collect_definitions(schema: dict[str, Any]) -> dict[str, Any]:
    """Extract the $defs or definitions mapping from the schema root."""
    defs = schema.get("$defs", {})
    if not defs:
        defs = schema.get("definitions", {})
    return defs


def _resolve_pointer(ref_string: str, definitions: dict[str, Any]) -> dict[str, Any]:
    """Resolve a single $ref string against the definitions dict.

    Only fragment-only refs (#/$defs/... or #/definitions/...) are permitted.
    """
    if not ref_string.startswith("#/"):
        raise DereferenceError(
            f"External $ref not allowed in signing surface: {ref_string}"
        )

    parts = ref_string.lstrip("#/").split("/")

    # Walk the path to find the target.
    # Expected paths: $defs/<name> or definitions/<name>
    if len(parts) != 2 or parts[0] not in ("$defs", "definitions"):
        raise DereferenceError(
            f"Unsupported $ref pointer format: {ref_string}"
        )

    def_name = parts[1]
    if def_name not in definitions:
        raise DereferenceError(
            f"$ref target not found: {ref_string}"
        )

    return copy.deepcopy(definitions[def_name])


def _detect_cycles(
    schema: dict[str, Any],
    definitions: dict[str, Any],
) -> None:
    """Walk all $ref targets and detect cycles before resolution begins."""
    if not definitions:
        return

    # Build a graph of which definitions reference which other definitions.
    def _collect_refs(node: Any) -> set[str]:
        """Collect all definition names referenced by $ref in a node."""
        refs: set[str] = set()
        if isinstance(node, dict):
            if "$ref" in node:
                ref = node["$ref"]
                if isinstance(ref, str) and ref.startswith("#/"):
                    parts = ref.lstrip("#/").split("/")
                    if len(parts) == 2 and parts[0] in ("$defs", "definitions"):
                        refs.add(parts[1])
            for value in node.values():
                refs |= _collect_refs(value)
        elif isinstance(node, list):
            for item in node:
                refs |= _collect_refs(item)
        return refs

    # Check each definition for cycles using DFS.
    def _has_cycle(name: str, visiting: set[str]) -> bool:
        if name in visiting:
            return True
        if name not in definitions:
            return False
        visiting.add(name)
        for referenced in _collect_refs(definitions[name]):
            if _has_cycle(referenced, visiting):
                return True
        visiting.remove(name)
        return False

    for def_name in definitions:
        if _has_cycle(def_name, set()):
            raise DereferenceError(
                f"Recursive $ref detected involving definition: {def_name}"
            )


def _walk_and_resolve(
    node: Any,
    definitions: dict[str, Any],
) -> Any:
    """Recursively walk JSON structure and replace $ref nodes with inlined content."""
    if isinstance(node, dict):
        if "$ref" in node:
            return _resolve_pointer(node["$ref"], definitions)
        return {
            key: _walk_and_resolve(value, definitions)
            for key, value in node.items()
        }
    elif isinstance(node, list):
        return [_walk_and_resolve(item, definitions) for item in node]
    else:
        return node


def _strip_defs(node: Any) -> Any:
    """Remove $defs and definitions keys at all nesting levels."""
    if isinstance(node, dict):
        return {
            key: _strip_defs(value)
            for key, value in node.items()
            if key not in ("$defs", "definitions")
        }
    elif isinstance(node, list):
        return [_strip_defs(item) for item in node]
    else:
        return node
