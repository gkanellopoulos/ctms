"""Shared data structures and constants for CTMS."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# The 7 signing surface fields (Section 3.1).
SIGNING_SURFACE_FIELDS: tuple[str, ...] = (
    "name", "title", "description",
    "inputSchema", "outputSchema",
    "annotations", "execution",
)

# Fields that trigger breaking changes (Section 5.1).
BREAKING_FIELDS: frozenset[str] = frozenset({
    "name", "inputSchema", "outputSchema", "execution",
})

# Fields that trigger semantic changes (Section 5.1).
SEMANTIC_FIELDS: frozenset[str] = frozenset({
    "description", "title", "annotations",
})

# Fixed values for STM structure (Section 3.3).
INTOTO_STATEMENT_TYPE = "https://in-toto.io/Statement/v1"
INTOTO_PAYLOAD_TYPE = "application/vnd.in-toto+json"
CTMS_PREDICATE_TYPE = "https://ctms.dev/v1/tool-manifest"
CTMS_VERSION = "1.0"


@dataclass(frozen=True)
class ManifestVersion:
    """STM version identifier (Section 5.2)."""
    major: int
    minor: int

    def __gt__(self, other: ManifestVersion) -> bool:
        return (self.major, self.minor) > (other.major, other.minor)

    def __ge__(self, other: ManifestVersion) -> bool:
        return (self.major, self.minor) >= (other.major, other.minor)

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}"


@dataclass(frozen=True)
class STMSubject:
    """In-toto subject entry (Section 3.3)."""
    name: str
    digest_sha256: str


@dataclass(frozen=True)
class STMPredicate:
    """STM predicate contents (Section 3.3)."""
    ctms_version: str
    manifest_version: ManifestVersion
    server_version: str
    signing_timestamp: str
    canonical_form: dict[str, Any]


@dataclass(frozen=True)
class STM:
    """Parsed Sealed Tool Manifest (Section 3.3)."""
    subject: STMSubject
    predicate: STMPredicate
    signature: str  # base64-encoded
    keyid: str
    signing_certificate: bytes | None = None
