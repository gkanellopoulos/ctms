"""Tests for change taxonomy and version logic (Section 5)."""

import pytest

from ctms._types import ManifestVersion
from ctms.errors import VersionRegressionError
from ctms.version import classify_change, next_version, validate_version_progression


class TestClassifyChange:

    def test_no_change(self):
        old = {"name": "tool", "description": "Desc."}
        new = {"name": "tool", "description": "Desc."}
        assert classify_change(old, new) == "none"

    def test_breaking_name_change(self):
        old = {"name": "tool_v1", "description": "Desc."}
        new = {"name": "tool_v2", "description": "Desc."}
        assert classify_change(old, new) == "breaking"

    def test_breaking_input_schema_change(self):
        old = {"name": "t", "inputSchema": {"type": "object"}}
        new = {"name": "t", "inputSchema": {"type": "object", "required": ["x"]}}
        assert classify_change(old, new) == "breaking"

    def test_breaking_output_schema_change(self):
        old = {"name": "t", "outputSchema": {"type": "string"}}
        new = {"name": "t", "outputSchema": {"type": "number"}}
        assert classify_change(old, new) == "breaking"

    def test_breaking_execution_change(self):
        old = {"name": "t", "execution": {"sandbox": True}}
        new = {"name": "t", "execution": {"sandbox": False}}
        assert classify_change(old, new) == "breaking"

    def test_semantic_description_change(self):
        old = {"name": "t", "description": "Old desc."}
        new = {"name": "t", "description": "New desc."}
        assert classify_change(old, new) == "semantic"

    def test_semantic_title_change(self):
        old = {"name": "t", "title": "Old Title"}
        new = {"name": "t", "title": "New Title"}
        assert classify_change(old, new) == "semantic"

    def test_semantic_annotations_change(self):
        old = {"name": "t", "annotations": {"readOnlyHint": True}}
        new = {"name": "t", "annotations": {"readOnlyHint": False}}
        assert classify_change(old, new) == "semantic"

    def test_breaking_takes_priority(self):
        """If both breaking and semantic fields changed, result is breaking."""
        old = {"name": "t", "description": "Old", "inputSchema": {"type": "object"}}
        new = {"name": "t", "description": "New", "inputSchema": {"type": "array"}}
        assert classify_change(old, new) == "breaking"

    def test_field_added(self):
        """Adding a new signing surface field is a change."""
        old = {"name": "t"}
        new = {"name": "t", "description": "Added."}
        assert classify_change(old, new) == "semantic"

    def test_field_removed(self):
        """Removing a signing surface field is a change."""
        old = {"name": "t", "inputSchema": {"type": "object"}}
        new = {"name": "t"}
        assert classify_change(old, new) == "breaking"


class TestNextVersion:

    def test_breaking_increments_major(self):
        v = next_version(ManifestVersion(1, 3), "breaking")
        assert v == ManifestVersion(2, 0)

    def test_semantic_increments_minor(self):
        v = next_version(ManifestVersion(1, 3), "semantic")
        assert v == ManifestVersion(1, 4)

    def test_none_raises(self):
        with pytest.raises(ValueError, match="No version increment"):
            next_version(ManifestVersion(1, 0), "none")


class TestValidateVersionProgression:

    def test_valid_major_bump(self):
        validate_version_progression(ManifestVersion(1, 0), ManifestVersion(2, 0))

    def test_valid_minor_bump(self):
        validate_version_progression(ManifestVersion(1, 0), ManifestVersion(1, 1))

    def test_equal_versions_rejected(self):
        with pytest.raises(VersionRegressionError):
            validate_version_progression(ManifestVersion(1, 0), ManifestVersion(1, 0))

    def test_regression_rejected(self):
        with pytest.raises(VersionRegressionError):
            validate_version_progression(ManifestVersion(2, 0), ManifestVersion(1, 5))

    def test_minor_regression_rejected(self):
        with pytest.raises(VersionRegressionError):
            validate_version_progression(ManifestVersion(1, 3), ManifestVersion(1, 2))
