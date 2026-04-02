"""Signing surface extraction and JCS canonicalization (Section 3.2)."""

from __future__ import annotations

import hashlib
from typing import Any

import rfc8785

from ctms._types import SIGNING_SURFACE_FIELDS
from ctms.dereference import dereference_schema
from ctms.errors import CanonicalizationError


def extract_signing_surface(tool_object: dict[str, Any]) -> dict[str, Any]:
    """Extract signing surface fields from an MCP Tool object (Section 3.2, steps 1-2).

    Only fields present in the tool object are included.
    Absent fields are omitted, never set to null or defaults.
    """
    surface = {}
    for field in SIGNING_SURFACE_FIELDS:
        if field in tool_object:
            surface[field] = tool_object[field]
    return surface


def canonicalize(tool_object: dict[str, Any]) -> bytes:
    """Full canonicalization pipeline (Section 3.2, steps 1-5).

    Extract signing surface, dereference $refs in schemas, apply JCS.
    Returns the canonical form as bytes.
    """
    surface = extract_signing_surface(tool_object)

    # Step 3: dereference $ref in inputSchema and outputSchema.
    for schema_field in ("inputSchema", "outputSchema"):
        if schema_field in surface and _has_refs(surface[schema_field]):
            try:
                surface[schema_field] = dereference_schema(surface[schema_field])
            except Exception as e:
                raise CanonicalizationError(
                    f"Failed to dereference {schema_field}: {e}"
                ) from e

    # Step 4: apply JCS.
    try:
        canonical_bytes = rfc8785.dumps(surface)
    except Exception as e:
        raise CanonicalizationError(f"JCS canonicalization failed: {e}") from e

    return canonical_bytes


def canonical_digest(canonical_form: bytes) -> str:
    """Compute SHA-256 hex digest of a canonical form."""
    return hashlib.sha256(canonical_form).hexdigest()


def _has_refs(node: Any) -> bool:
    """Check if a JSON structure contains any $ref keywords."""
    if isinstance(node, dict):
        if "$ref" in node:
            return True
        return any(_has_refs(v) for v in node.values())
    elif isinstance(node, list):
        return any(_has_refs(item) for item in node)
    return False
