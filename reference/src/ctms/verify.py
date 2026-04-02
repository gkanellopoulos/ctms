"""11-step verification procedure (Section 6.1).

Steps 1 (Receive) and 2 (Detect server version) are caller responsibilities.
This module implements steps 3-11.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from ctms._types import ManifestVersion
from ctms.canonicalize import canonicalize, canonical_digest
from ctms.errors import (
    ManifestDriftError,
    PublisherTrustFailureError,
    SignatureFailureError,
)
from ctms.stm import parse_stm


@dataclass
class VerificationResult:
    """Returned on successful verification."""
    tool_name: str
    subject_name: str
    publisher_identity: str | None
    manifest_version: ManifestVersion
    server_version: str
    signing_timestamp: str
    canonical_digest: str


def verify_canonical_form(
    tool_object: dict[str, Any],
    stm_dict: dict[str, Any],
) -> None:
    """Steps 4-6 only: extract, canonicalize, compare.

    Useful for offline/cached verification without Sigstore.
    Raises ManifestDriftError if canonical forms differ.
    """
    stm = parse_stm(stm_dict)

    # Step 4-5: extract and canonicalize runtime tool metadata.
    runtime_canonical = canonicalize(tool_object)
    runtime_digest = canonical_digest(runtime_canonical)

    # Step 6: compare.
    expected_digest = stm.subject.digest_sha256
    if runtime_digest != expected_digest:
        raise ManifestDriftError(
            f"Manifest drift detected: expected {expected_digest}, got {runtime_digest}",
            expected_digest=expected_digest,
            actual_digest=runtime_digest,
            subject_name=stm.subject.name,
        )


def verify_tool(
    tool_object: dict[str, Any],
    stm_dict: dict[str, Any],
    expected_subject_name: str | None = None,
    trusted_publishers: list[str] | None = None,
    staging: bool = False,
) -> VerificationResult:
    """Execute verification procedure steps 3-11 (Section 6.1).

    Steps 1-2 are caller responsibilities.
    The STM must already be retrieved (step 3 retrieval is the caller's job).

    Raises typed exceptions from ctms.errors on any failure.
    """
    stm = parse_stm(stm_dict)

    # Step 3 (partial): verify subject name if expected name is provided.
    if expected_subject_name is not None:
        if stm.subject.name != expected_subject_name:
            raise ManifestDriftError(
                f"Subject name mismatch: expected {expected_subject_name}, "
                f"got {stm.subject.name}",
                subject_name=stm.subject.name,
            )

    # Steps 4-5: extract and canonicalize runtime tool metadata.
    runtime_canonical = canonicalize(tool_object)
    runtime_digest = canonical_digest(runtime_canonical)

    # Step 6: compare canonical forms.
    expected_digest = stm.subject.digest_sha256
    if runtime_digest != expected_digest:
        raise ManifestDriftError(
            f"Manifest drift detected: expected {expected_digest}, got {runtime_digest}",
            expected_digest=expected_digest,
            actual_digest=runtime_digest,
            subject_name=stm.subject.name,
        )

    # Steps 7-9: verify signature, certificate, and log entry.
    publisher_identity = _verify_sigstore(
        runtime_canonical, stm_dict, staging=staging
    )

    # Step 10: verify publisher trust.
    if trusted_publishers is not None:
        _verify_publisher(publisher_identity, trusted_publishers, stm.subject.name)

    # Step 11: accept.
    return VerificationResult(
        tool_name=stm.predicate.canonical_form.get("name", ""),
        subject_name=stm.subject.name,
        publisher_identity=publisher_identity,
        manifest_version=stm.predicate.manifest_version,
        server_version=stm.predicate.server_version,
        signing_timestamp=stm.predicate.signing_timestamp,
        canonical_digest=runtime_digest,
    )


def _verify_sigstore(
    canonical_form: bytes,
    stm_dict: dict[str, Any],
    staging: bool = False,
) -> str | None:
    """Steps 7-9: verify signature, certificate, and log entry via Sigstore.

    Returns publisher identity string on success.
    Returns None if no Sigstore bundle is present (offline-only STM).
    Raises SignatureFailureError on any Sigstore verification failure.
    """
    bundle_data = stm_dict.get("sigstoreBundle")
    if bundle_data is None:
        # No Sigstore bundle; publisher identity cannot be determined.
        # Offline verification (steps 4-6) still works without this.
        return None

    # Lazy imports to allow offline use without sigstore installed.
    from sigstore.errors import VerificationError
    from sigstore.models import Bundle
    from sigstore.verify import Verifier
    from sigstore.verify.policy import UnsafeNoOp

    try:
        bundle = Bundle.from_json(json.dumps(bundle_data))
    except Exception as e:
        raise SignatureFailureError(f"Invalid Sigstore bundle: {e}")

    if staging:
        verifier = Verifier.staging()
    else:
        verifier = Verifier.production()

    # Verify signature, certificate chain, and log entry.
    # Identity policy is not checked here; publisher trust is handled
    # separately in step 10 by _verify_publisher.
    try:
        verifier.verify_artifact(canonical_form, bundle, UnsafeNoOp())
    except VerificationError as e:
        raise SignatureFailureError(
            f"Sigstore verification failed: {e}",
            subject_name=stm_dict.get("payload", {}).get("subject", [{}])[0].get("name"),
        )

    # Extract publisher identity from the signing certificate's SANs.
    return _extract_publisher_identity(bundle)


def _verify_publisher(
    publisher_identity: str | None,
    trusted_publishers: list[str],
    subject_name: str,
) -> None:
    """Step 10: check publisher against trust list."""
    if publisher_identity is None:
        raise PublisherTrustFailureError(
            "Publisher identity could not be determined",
            subject_name=subject_name,
        )
    if publisher_identity not in trusted_publishers:
        raise PublisherTrustFailureError(
            f"Publisher {publisher_identity} is not in the trusted publishers list",
            subject_name=subject_name,
            publisher_identity=publisher_identity,
        )


def _extract_publisher_identity(bundle: Any) -> str | None:
    """Extract the publisher identity (email or URI) from a Sigstore bundle's certificate."""
    from cryptography.x509 import SubjectAlternativeName, RFC822Name, UniformResourceIdentifier

    try:
        cert = bundle.signing_certificate
        san_ext = cert.extensions.get_extension_for_class(SubjectAlternativeName).value
        identities: list[str] = []
        identities.extend(san_ext.get_values_for_type(RFC822Name))
        identities.extend(san_ext.get_values_for_type(UniformResourceIdentifier))
        return identities[0] if identities else None
    except Exception:
        return None
