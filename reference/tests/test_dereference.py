"""Tests for $ref resolution (Section 3.2, step 3).

Validates against query-geo test vectors (A.7).
"""

import pytest

from ctms.dereference import dereference_schema
from ctms.errors import DereferenceError


class TestDereferenceSchema:

    def test_query_geo_dereferencing(self, query_geo_tool_object, query_geo_dereferenced):
        """A.7: query-geo inputSchema $refs resolved and $defs removed."""
        result = dereference_schema(query_geo_tool_object["inputSchema"])
        expected = query_geo_dereferenced["inputSchema"]
        assert result == expected

    def test_no_refs_passthrough(self):
        """Schema without $ref is returned unchanged (minus $defs)."""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
        }
        result = dereference_schema(schema)
        assert result == schema

    def test_defs_removed(self):
        """$defs are removed even if no $ref references them."""
        schema = {
            "type": "object",
            "$defs": {
                "unused": {"type": "string"},
            },
            "properties": {
                "name": {"type": "string"},
            },
        }
        result = dereference_schema(schema)
        assert "$defs" not in result
        assert result["properties"]["name"] == {"type": "string"}

    def test_definitions_removed(self):
        """Older 'definitions' keyword is also removed."""
        schema = {
            "type": "object",
            "definitions": {
                "addr": {"type": "string"},
            },
            "properties": {
                "address": {"$ref": "#/definitions/addr"},
            },
        }
        result = dereference_schema(schema)
        assert "definitions" not in result
        assert result["properties"]["address"] == {"type": "string"}

    def test_composition_keywords_preserved(self):
        """oneOf, anyOf, allOf are preserved, not merged."""
        schema = {
            "type": "object",
            "properties": {
                "value": {
                    "oneOf": [
                        {"type": "string"},
                        {"type": "number"},
                    ]
                }
            },
        }
        result = dereference_schema(schema)
        assert "oneOf" in result["properties"]["value"]
        assert len(result["properties"]["value"]["oneOf"]) == 2


class TestDereferenceErrors:

    def test_external_ref_rejected(self):
        """External $ref (not fragment-only) raises DereferenceError."""
        schema = {
            "type": "object",
            "properties": {
                "item": {"$ref": "https://example.com/schema.json"},
            },
        }
        with pytest.raises(DereferenceError, match="External .ref not allowed"):
            dereference_schema(schema)

    def test_missing_target_rejected(self):
        """$ref pointing to nonexistent definition raises DereferenceError."""
        schema = {
            "type": "object",
            "$defs": {},
            "properties": {
                "item": {"$ref": "#/$defs/missing"},
            },
        }
        with pytest.raises(DereferenceError, match="not found"):
            dereference_schema(schema)

    def test_cycle_detected(self):
        """Recursive $ref cycle raises DereferenceError."""
        schema = {
            "type": "object",
            "$defs": {
                "a": {"$ref": "#/$defs/b"},
                "b": {"$ref": "#/$defs/a"},
            },
            "properties": {
                "item": {"$ref": "#/$defs/a"},
            },
        }
        with pytest.raises(DereferenceError, match="Recursive"):
            dereference_schema(schema)

    def test_self_referencing_cycle(self):
        """Self-referencing definition raises DereferenceError."""
        schema = {
            "type": "object",
            "$defs": {
                "loop": {"$ref": "#/$defs/loop"},
            },
            "properties": {
                "item": {"$ref": "#/$defs/loop"},
            },
        }
        with pytest.raises(DereferenceError, match="Recursive"):
            dereference_schema(schema)

    def test_input_not_mutated(self):
        """Original schema dict is not modified."""
        schema = {
            "type": "object",
            "$defs": {
                "coords": {"type": "object", "properties": {"x": {"type": "number"}}},
            },
            "properties": {
                "point": {"$ref": "#/$defs/coords"},
            },
        }
        import copy
        original = copy.deepcopy(schema)
        dereference_schema(schema)
        assert schema == original
