"""Tests for STM construction and parsing (Section 3.3).

Validates against weather-stm.json structure.
"""

import json

import pytest

from ctms._types import ManifestVersion
from ctms.canonicalize import canonicalize, canonical_digest
from ctms.stm import build_stm, parse_stm, stm_to_json, stm_from_json


class TestParseSTM:

    def test_weather_stm_structure(self, weather_stm):
        """Parse weather-stm.json and verify structural fields."""
        stm = parse_stm(weather_stm)

        assert stm.subject.name == "io.github.weathertools/weather-server/get_weather"
        assert stm.predicate.ctms_version == "1.0"
        assert stm.predicate.manifest_version == ManifestVersion(major=1, minor=0)
        assert stm.predicate.server_version == "2.1.0"
        assert stm.predicate.signing_timestamp == "2026-03-22T14:30:00Z"

    def test_weather_stm_canonical_form_in_predicate(self, weather_stm, weather_signing_surface):
        """The canonicalForm in the predicate matches the signing surface."""
        stm = parse_stm(weather_stm)
        assert stm.predicate.canonical_form == weather_signing_surface

    def test_invalid_payload_type(self, weather_stm):
        """Wrong payloadType raises ValueError."""
        weather_stm["payloadType"] = "application/json"
        with pytest.raises(ValueError, match="payloadType"):
            parse_stm(weather_stm)

    def test_invalid_statement_type(self, weather_stm):
        """Wrong _type raises ValueError."""
        weather_stm["payload"]["_type"] = "https://wrong.io/Statement/v1"
        with pytest.raises(ValueError, match="_type"):
            parse_stm(weather_stm)

    def test_invalid_predicate_type(self, weather_stm):
        """Wrong predicateType raises ValueError."""
        weather_stm["payload"]["predicateType"] = "https://wrong.dev/v1/manifest"
        with pytest.raises(ValueError, match="predicateType"):
            parse_stm(weather_stm)

    def test_no_subjects(self, weather_stm):
        """Empty subject list raises ValueError."""
        weather_stm["payload"]["subject"] = []
        with pytest.raises(ValueError, match="subject"):
            parse_stm(weather_stm)

    def test_multiple_subjects(self, weather_stm):
        """Multiple subjects raises ValueError (exactly one required)."""
        weather_stm["payload"]["subject"].append(
            {"name": "extra", "digest": {"sha256": "abc"}}
        )
        with pytest.raises(ValueError, match="subject"):
            parse_stm(weather_stm)

    def test_no_signatures(self, weather_stm):
        """Empty signatures list raises ValueError."""
        weather_stm["signatures"] = []
        with pytest.raises(ValueError, match="signature"):
            parse_stm(weather_stm)


class TestBuildSTM:

    def test_roundtrip(self, weather_tool_object):
        """build_stm output can be parsed back by parse_stm."""
        canonical_form = canonicalize(weather_tool_object)

        stm_dict = build_stm(
            subject_name="io.github.test/server/get_weather",
            canonical_form=canonical_form,
            manifest_version=ManifestVersion(major=1, minor=0),
            server_version="1.0.0",
            signing_timestamp="2026-03-25T10:00:00Z",
            signature="dGVzdHNpZw==",
        )

        stm = parse_stm(stm_dict)
        assert stm.subject.name == "io.github.test/server/get_weather"
        assert stm.predicate.server_version == "1.0.0"
        assert stm.signature == "dGVzdHNpZw=="

    def test_digest_matches_canonical_form(self, weather_tool_object):
        """Subject digest in built STM matches actual canonical form digest."""
        canonical_form = canonicalize(weather_tool_object)
        expected_digest = canonical_digest(canonical_form)

        stm_dict = build_stm(
            subject_name="test/tool",
            canonical_form=canonical_form,
            manifest_version=ManifestVersion(major=1, minor=0),
            server_version="1.0.0",
            signing_timestamp="2026-03-25T10:00:00Z",
            signature="c2ln",
        )

        actual_digest = stm_dict["payload"]["subject"][0]["digest"]["sha256"]
        assert actual_digest == expected_digest


class TestSTMSerialization:

    def test_to_json_pretty(self, weather_stm):
        """stm_to_json with pretty=True produces indented JSON."""
        result = stm_to_json(weather_stm, pretty=True)
        assert "\n" in result
        assert "  " in result

    def test_to_json_compact(self, weather_stm):
        """stm_to_json with pretty=False produces compact JSON."""
        result = stm_to_json(weather_stm, pretty=False)
        assert "\n" not in result
        assert "  " not in result

    def test_roundtrip_json(self, weather_stm):
        """stm_to_json -> stm_from_json produces equal dict."""
        json_str = stm_to_json(weather_stm)
        restored = stm_from_json(json_str)
        assert restored == weather_stm
