"""Sigstore signing pipeline (Section 4.1).

Signs MCP tool metadata using the Sigstore keyless signing model:
OIDC auth -> Fulcio certificate -> ES256 signature -> Rekor log entry -> STM.
"""

from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from typing import Any

from ctms._types import ManifestVersion
from ctms.canonicalize import canonicalize
from ctms.stm import build_stm


def sign_tool(
    tool_object: dict[str, Any],
    subject_name: str,
    manifest_version: ManifestVersion,
    server_version: str,
    staging: bool = False,
) -> dict[str, Any]:
    """Full signing pipeline (Section 4.1, steps 1-4).

    1. Canonicalize the tool object
    2. Authenticate via OIDC (opens browser or uses ambient credentials)
    3. Obtain Fulcio certificate and sign with ES256
    4. Record in Rekor and assemble STM

    Returns a complete STM dict including the Sigstore bundle.
    """
    # Step 1: canonicalize.
    canonical_form = canonicalize(tool_object)

    # Steps 2-4: authenticate, sign, record.
    # Lazy imports to avoid import-time overhead and allow offline use.
    from sigstore.models import ClientTrustConfig
    from sigstore.oidc import Issuer, IdentityToken, detect_credential
    from sigstore.sign import SigningContext

    if staging:
        trust_config = ClientTrustConfig.staging()
    else:
        trust_config = ClientTrustConfig.production()

    context = SigningContext.from_trust_config(trust_config)

    # Try ambient credentials (e.g. GitHub Actions OIDC) first,
    # fall back to browser-based OIDC auth.
    raw_token = detect_credential()
    if raw_token:
        identity_token = IdentityToken(raw_token)
    else:
        oidc_url = trust_config.signing_config.get_oidc_url()
        issuer = Issuer(oidc_url)
        identity_token = issuer.identity_token()

    with context.signer(identity_token, cache=True) as signer:
        bundle = signer.sign_artifact(canonical_form)

    # Extract raw signature for the in-toto envelope.
    sig_b64 = base64.b64encode(bundle.signature).decode("ascii")

    # Serialize the full Sigstore bundle for verification later.
    sigstore_bundle = json.loads(bundle.to_json())

    signing_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return build_stm(
        subject_name=subject_name,
        canonical_form=canonical_form,
        manifest_version=manifest_version,
        server_version=server_version,
        signing_timestamp=signing_timestamp,
        signature=sig_b64,
        sigstore_bundle=sigstore_bundle,
    )
