"""Tests for signing surface extraction and JCS canonicalization.

Validates against weather (A.1-A.3) and query-geo (A.7) test vectors.
"""

from ctms.canonicalize import (
    canonicalize,
    canonical_digest,
    extract_signing_surface,
)


class TestExtractSigningSurface:

    def test_weather_signing_surface(self, weather_tool_object, weather_signing_surface):
        """A.2: extracted surface matches weather-signing-surface.json."""
        surface = extract_signing_surface(weather_tool_object)
        assert surface == weather_signing_surface

    def test_only_present_fields(self):
        """Absent signing surface fields are omitted, not set to null."""
        tool = {"name": "minimal", "description": "A tool."}
        surface = extract_signing_surface(tool)
        assert surface == {"name": "minimal", "description": "A tool."}
        assert "inputSchema" not in surface
        assert "title" not in surface

    def test_non_signing_fields_excluded(self):
        """Fields outside the signing surface are dropped."""
        tool = {
            "name": "test",
            "description": "Desc.",
            "customField": "should be dropped",
            "_meta": {"internal": True},
        }
        surface = extract_signing_surface(tool)
        assert "customField" not in surface
        assert "_meta" not in surface


class TestCanonicalize:

    def test_weather_canonical_form(self, weather_tool_object, weather_canonical_form):
        """A.3: full pipeline output matches weather-canonical-form.txt."""
        result = canonicalize(weather_tool_object)
        assert result == weather_canonical_form

    def test_query_geo_canonical_form(self, query_geo_tool_object, query_geo_canonical_form):
        """A.7: query-geo with $ref produces expected canonical form."""
        result = canonicalize(query_geo_tool_object)
        assert result == query_geo_canonical_form

    def test_returns_bytes(self, weather_tool_object):
        """Canonical form is bytes, not str."""
        result = canonicalize(weather_tool_object)
        assert isinstance(result, bytes)

    def test_deterministic(self, weather_tool_object):
        """Same input always produces identical output."""
        a = canonicalize(weather_tool_object)
        b = canonicalize(weather_tool_object)
        assert a == b


class TestCanonicalDigest:

    def test_weather_digest(self, weather_canonical_form):
        """Digest is a hex string of expected length."""
        digest = canonical_digest(weather_canonical_form)
        assert isinstance(digest, str)
        assert len(digest) == 64  # SHA-256 hex = 64 chars

    def test_different_inputs_different_digests(self):
        """Different canonical forms produce different digests."""
        a = canonical_digest(b'{"name":"a"}')
        b = canonical_digest(b'{"name":"b"}')
        assert a != b
