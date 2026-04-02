"""Shared fixtures loading test vectors from ctms-repo/vectors/."""

import json
from pathlib import Path

import pytest


VECTORS_DIR = Path(__file__).resolve().parent.parent.parent / "vectors"


@pytest.fixture
def vectors_dir():
    return VECTORS_DIR


@pytest.fixture
def weather_tool_object():
    return json.loads((VECTORS_DIR / "weather-tool-object.json").read_bytes())


@pytest.fixture
def weather_signing_surface():
    return json.loads((VECTORS_DIR / "weather-signing-surface.json").read_bytes())


@pytest.fixture
def weather_canonical_form():
    # Strip trailing newline that text editors may add.
    return (VECTORS_DIR / "weather-canonical-form.txt").read_bytes().rstrip(b"\r\n")


@pytest.fixture
def weather_stm():
    return json.loads((VECTORS_DIR / "weather-stm.json").read_bytes())


@pytest.fixture
def query_geo_tool_object():
    return json.loads((VECTORS_DIR / "query-geo-tool-object.json").read_bytes())


@pytest.fixture
def query_geo_dereferenced():
    return json.loads((VECTORS_DIR / "query-geo-dereferenced.json").read_bytes())


@pytest.fixture
def query_geo_canonical_form():
    return (VECTORS_DIR / "query-geo-canonical-form.txt").read_bytes().rstrip(b"\r\n")
