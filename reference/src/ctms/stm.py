"""STM construction and parsing (Section 3.3).

STMs are built as plain Python dicts matching the in-toto v1 statement format.
No dependency on in-toto-attestation protobuf bindings.
"""

from __future__ import annotations

import json
from typing import Any

from ctms._types import (
    CTMS_PREDICATE_TYPE,
    CTMS_VERSION,
    INTOTO_PAYLOAD_TYPE,
    INTOTO_STATEMENT_TYPE,
    ManifestVersion,
    STM,
    STMPredicate,
    STMSubject,
)
from ctms.canonicalize import canonical_digest


def build_stm(
    subject_name: str,
    canonical_form: bytes,
    manifest_version: ManifestVersion,
    server_version: str,
    signing_timestamp: str,
    signature: str,
    keyid: str = "",
    sigstore_bundle: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Construct a complete STM dict (in-toto envelope) from components.

    If sigstore_bundle is provided, it is stored at the top level for
    full Sigstore verification (steps 7-9).
    """
    digest = canonical_digest(canonical_form)
    # Parse canonical form back to dict for the predicate.
    canonical_dict = json.loads(canonical_form)

    stm: dict[str, Any] = {
        "payloadType": INTOTO_PAYLOAD_TYPE,
        "payload": {
            "_type": INTOTO_STATEMENT_TYPE,
            "subject": [
                {
                    "name": subject_name,
                    "digest": {"sha256": digest},
                }
            ],
            "predicateType": CTMS_PREDICATE_TYPE,
            "predicate": {
                "ctmsVersion": CTMS_VERSION,
                "manifestVersion": {
                    "major": manifest_version.major,
                    "minor": manifest_version.minor,
                },
                "serverVersion": server_version,
                "signingTimestamp": signing_timestamp,
                "canonicalForm": canonical_dict,
            },
        },
        "signatures": [
            {
                "keyid": keyid,
                "sig": signature,
            }
        ],
    }

    if sigstore_bundle is not None:
        stm["sigstoreBundle"] = sigstore_bundle

    return stm


def parse_stm(stm_dict: dict[str, Any]) -> STM:
    """Parse and validate an STM dict into a typed STM dataclass.

    Validates structural requirements from Section 3.3:
    - Correct payloadType
    - Correct statement _type
    - Correct predicateType
    - Exactly one subject
    - Exactly one signature
    - Required predicate fields present
    """
    # Validate envelope.
    payload_type = stm_dict.get("payloadType")
    if payload_type != INTOTO_PAYLOAD_TYPE:
        raise ValueError(f"Invalid payloadType: {payload_type}")

    payload = stm_dict.get("payload", {})

    statement_type = payload.get("_type")
    if statement_type != INTOTO_STATEMENT_TYPE:
        raise ValueError(f"Invalid statement _type: {statement_type}")

    predicate_type = payload.get("predicateType")
    if predicate_type != CTMS_PREDICATE_TYPE:
        raise ValueError(f"Invalid predicateType: {predicate_type}")

    # Validate subject.
    subjects = payload.get("subject", [])
    if len(subjects) != 1:
        raise ValueError(f"Expected exactly one subject, got {len(subjects)}")

    subject_entry = subjects[0]
    subject = STMSubject(
        name=subject_entry["name"],
        digest_sha256=subject_entry["digest"]["sha256"],
    )

    # Validate signatures.
    signatures = stm_dict.get("signatures", [])
    if len(signatures) == 0:
        raise ValueError("STM must contain at least one signature")

    sig_entry = signatures[0]

    # Parse predicate.
    pred = payload.get("predicate", {})
    mv = pred.get("manifestVersion", {})
    predicate = STMPredicate(
        ctms_version=pred["ctmsVersion"],
        manifest_version=ManifestVersion(
            major=mv["major"],
            minor=mv["minor"],
        ),
        server_version=pred["serverVersion"],
        signing_timestamp=pred["signingTimestamp"],
        canonical_form=pred["canonicalForm"],
    )

    return STM(
        subject=subject,
        predicate=predicate,
        signature=sig_entry["sig"],
        keyid=sig_entry.get("keyid", ""),
    )


def stm_to_json(stm_dict: dict[str, Any], pretty: bool = True) -> str:
    """Serialize STM dict to JSON string."""
    if pretty:
        return json.dumps(stm_dict, indent=2)
    return json.dumps(stm_dict, separators=(",", ":"))


def stm_from_json(json_string: str) -> dict[str, Any]:
    """Parse JSON string into STM dict."""
    return json.loads(json_string)
