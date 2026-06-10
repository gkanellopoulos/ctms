# CTMS: Canonical Tool Manifest Specification

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20504985.svg)](https://doi.org/10.5281/zenodo.20504985)

CTMS is a specification for signing and verifying MCP tool metadata.

## The Problem

When an MCP client discovers a tool, it uses the tool's description to decide what the tool does and how to call it. No standard mechanism verifies that the description hasn't been tampered with, silently changed after deployment, or crafted to manipulate the model's behavior.

Tool description poisoning attacks against MCP have been [demonstrated in practice](https://arxiv.org/abs/2504.03767), including malicious code execution, remote access, and credential theft. The attacks work because there is nothing between a tool's description and the language model's trust in it.

But malice isn't always required. Tool metadata drifts on its own. A developer updates a description and forgets to re-sign. A deployment script overwrites a schema field. Parameters fall out of sync with what the tool actually accepts. The AI makes calls based on metadata that no longer reflects reality. None of this requires an attacker, just the normal entropy of software development.

In regulated environments, the stakes are higher. Auditors may require proof that the tool description in use at a specific time matched the approved version. Without a verifiable historical record, that proof does not exist.

## What CTMS Does

CTMS defines a canonical, signable representation of a tool's declared capabilities: its name, description, input/output schema, and behavioral annotations. Publishers sign this representation. Clients verify it at runtime. If anything has changed since signing, the tool is blocked.

Specifically:

- **Signing surface.** CTMS defines which fields from the MCP Tool object constitute the tool's semantic claim about its capabilities.
- **Canonicalization.** The signing surface is canonicalized via JCS ([RFC 8785](https://www.rfc-editor.org/rfc/rfc8785)), producing a deterministic byte sequence regardless of how the server serializes the metadata.
- **Keyless signing.** Publisher identity is established through OpenID Connect. Signing uses short-lived certificates issued by a Sigstore-compatible certificate authority. No long-lived keys to manage, rotate, or leak.
- **Transparency log.** Every signing event is recorded in an append-only, cryptographically verifiable log. The log provides an immutable audit trail of what was signed, by whom, and when.
- **Verification.** Clients compare runtime tool metadata against the signed manifest. If the metadata has drifted (whether through tampering, developer error, or unauthorized update) verification fails and the tool is rejected.
- **Versioning.** Every change to the signing surface requires a new signature. Breaking changes (schema, execution) require a major version increment. Semantic changes (description, annotations) require a minor version increment.

The result is a **Sealed Tool Manifest (STM)**: an immutable, auditable attestation of what a tool claimed at signing time.

## What CTMS Does Not Do

CTMS verifies that a tool's claims haven't changed. It does not verify that those claims are true. It is a seal, not a code review.

CTMS does not:

- Verify that a tool's implementation matches its description
- Scan tool descriptions for malicious content or prompt injection
- Enforce runtime policies on which tools a model may invoke
- Provide transport-level authentication between clients and servers
- Define a tool registry

## Built On

CTMS builds on established supply chain security infrastructure:

- [**in-toto**](https://in-toto.io/) attestation format for the envelope
- [**Sigstore**](https://sigstore.dev/) (Fulcio + Rekor) for keyless signing and transparency logging
- [**JCS**](https://www.rfc-editor.org/rfc/rfc8785) (RFC 8785) for deterministic JSON canonicalization

No new cryptographic primitives. No custom infrastructure.

## Conformance Profiles

CTMS defines three conformance profiles for different deployment contexts:

| Profile | Intended for | Key characteristics |
|---|---|---|
| **Community** | Open-source and public MCP servers | Public Sigstore, any OIDC provider, 72-hour cache, 2-year log retention |
| **Enterprise** | Regulated industries and organizational deployments | Organization-managed OIDC, private infrastructure permitted, 24-hour cache, 5+ year retention |
| **Sovereign** | Government, military, and national security | Government-operated infrastructure, real-time verification, no caching, 20+ year retention |

All profiles share the same canonical form, envelope format, and verification procedure. They differ in operational and cryptographic constraints.

## Relationship to MCP

CTMS is complementary to the [Model Context Protocol](https://modelcontextprotocol.io/). It does not modify, extend, or replace any part of MCP. The MCP specification explicitly acknowledges the absence of a mechanism to verify tool description integrity and defers this concern to the broader ecosystem. CTMS is a response to that deferral.

Existing MCP servers require no changes. The server continues to respond to `tools/list` as it normally would, with no awareness of CTMS. Verification happens on the client side, before tool metadata reaches the language model.

## Who This Is For

**MCP server publishers.** Attest to what your tools claim. Protect your users from tampering and metadata drift.

**MCP client developers.** Verify tool metadata before your model sees it. Block poisoned descriptions.

**Security and compliance teams.** Immutable audit trail of what every tool claimed, signed by whom, and when. Aligned with SLSA and existing supply chain security frameworks.

## Key Documents

- [**Specification**](spec/CTMS-specification.md) - the full CTMS v1.0 specification
- [**Threat Model**](THREAT_MODEL.md) - attack scenarios, mitigations, residual risks, and CSA TTP mapping
- [**Reference Implementation**](reference/README.md) - Python library and CLI (install, usage, API, tests)
- [**Test Vectors**](vectors/README.md) - machine-consumable conformance vectors
- [**Governance**](governance/GOVERNANCE.md) - governance model and change process
- [**Article**](https://gkanellopoulos.github.io/ctms/) - "Tool Metadata Poisoning: An Unresolved Attack Surface in MCP"

## Repository Structure

```
spec/              Specification document
governance/        Governance model
vectors/           Machine-consumable test vectors
reference/         Python reference implementation
  examples/        Attack demo, MCP client PoC, example signed STM
  tests/           67 offline tests against test vectors
docs/              GitHub Pages article on tool metadata poisoning
THREAT_MODEL.md    Threat model with attack scenarios
```

## Quick Start

Install the reference implementation and run the attack demo:

```bash
cd reference
pip install -e .
python examples/attack_demo.py
```

Or try signing and verifying a tool yourself:

```bash
ctms canonicalize ../vectors/weather-tool-object.json --digest
ctms sign ../vectors/weather-tool-object.json \
    --subject-name io.github.weathertools/weather-server/get_weather \
    --server-version 1.0.0 --staging -o weather.stm.json
ctms verify ../vectors/weather-tool-object.json weather.stm.json --staging
```

See [reference/README.md](reference/README.md) for full CLI and library documentation.

## Status

CTMS is at version 1.0 (2026-03-25). The Python reference implementation is included. Feedback is welcome.

## Citation

If you cite CTMS in a paper, report, or other work:

> Kanellopoulos, G. (2026). CTMS: Canonical Tool Manifest Specification (Version 1.0). Zenodo. https://doi.org/10.5281/zenodo.20504985

BibTeX:

```bibtex
@misc{kanellopoulos_2026_ctms,
  author       = {Kanellopoulos, George},
  title        = {{CTMS: Canonical Tool Manifest Specification}},
  month        = jun,
  year         = 2026,
  publisher    = {Zenodo},
  version      = {1.0},
  doi          = {10.5281/zenodo.20504985},
  url          = {https://doi.org/10.5281/zenodo.20504985}
}
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

[Apache 2.0](LICENSE)
