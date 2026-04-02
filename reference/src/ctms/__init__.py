"""CTMS reference implementation: signing and verification for MCP tool metadata."""

__version__ = "0.1.0"

from ctms.canonicalize import canonicalize, extract_signing_surface, canonical_digest
from ctms.dereference import dereference_schema
from ctms.stm import build_stm, parse_stm
from ctms.version import classify_change, next_version
