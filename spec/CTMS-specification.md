# Canonical Tool Manifest Specification (CTMS)

**Version:** 1.0
**Date:** 2026-03-25
**Status:** Published
**Author:** George Kanellopoulos

## Abstract

CTMS defines a signing and verification scheme for MCP (Model Context Protocol) tool metadata. MCP servers declare tool capabilities through descriptions, schemas, and annotations that language models use to discover and invoke tools. Nothing in the MCP protocol verifies that these declarations are accurate or unchanged. CTMS addresses this gap by defining a canonical form for tool metadata, a keyless signing scheme using Sigstore, a versioning model that distinguishes breaking from semantic changes, and a verification procedure that MCP clients perform before passing tool metadata to the language model. The signed artifact is a Sealed Tool Manifest (STM), structured as an in-toto attestation and recorded in a transparency log.

---

## 1. Introduction

### 1.1 Problem statement

#### What is the Model Context Protocol (MCP)?

MCP (Model Context Protocol) is an open-source standard that allows AI applications to connect to external systems such as data sources, tools, and workflows. It acts like a USB-C port for AI, providing a standardized way for language models to access information and perform tasks through external integrations. ([source](https://modelcontextprotocol.io/docs/getting-started/intro)).

During the MCP lifecycle and specifically in the **[Initialization](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle#initialization)** phase the server must respond with its own capabilities and information. Subsequently according to the MCP specification, the language model, by examining those capabilities and information can **discover and invoke tools automatically based on its contextual understanding.** However, the specification also explicitly states that tool descriptions should be considered untrusted ([source](https://modelcontextprotocol.io/specification/2025-11-25/index#key-principles)) and MCP itself cannot enforce tool security principles at the protocol level ([source](https://modelcontextprotocol.io/specification/2025-11-25/index#implementation-guidelines)). Additionally the newly established [MCP Registry](https://modelcontextprotocol.io/registry/about) *focuses on namespace authentication and metadata hosting, while relying on the broader ecosystem for security scanning of actual server code* ([source](https://modelcontextprotocol.io/registry/about#security-scanning)).

#### The Gap

Radosevich and Halloran (2025) demonstrated tool poisoning attacks against MCP, including malicious code execution, remote access, and credential theft. The attacks work because there is nothing between a tool’s description and the language model’s trust in it.

The consequences fall along a spectrum. At the malicious end: a tool description includes hidden instructions that manipulate the AI into exfiltrating data (description poisoning), a description is silently rewritten after deployment so the AI follows new instructions without the user’s knowledge (rug pull), or a malicious description in one server influences how the model uses tools from a different, trusted server (cross-tool shadowing).

But malice is not always required. Tool metadata drifts on its own. A developer updates a description but forgets to update the manifest. A deployment script overwrites an `inputSchema` field. Parameters, types, or optional fields fall out of sync with what the manifest expects. The AI makes tool calls based on metadata that no longer reflects reality. None of this requires an attacker. It just requires the normal entropy of software development.

In regulated settings, the stakes are higher. Tool descriptions may overpromise capabilities that an organization is not licensed to use, leading the AI to perform actions outside validated processes such as GxP, GMP, or CFR21 environments. Auditors may require proof that the tool description in use at a specific time matched the approved version. Without a verifiable historical record, that proof does not exist.

#### Addressing the gap

This specification defines a **canonical, signable representation of a tool’s declared capabilities** (the "signing surface"). Publishers create and sign this representation. Clients verify it at runtime. If the tool’s description, schema, or annotations have changed since signing, verification fails and the tool is blocked. The result is a stable, auditable reference for what the tool claims to do, independent of where or how it is deployed.


### 1.2 Scope and non-goals

CTMS builds on established standards to define a verifiable trust layer for MCP tool metadata. The specification addresses the following concerns:

1. Signing surface. CTMS defines a signing surface consisting of the following fields from the MCP Tool object: `name`, `title`, `description`, `inputSchema`, `outputSchema`, `annotations`, `execution`. These fields constitute the semantic claim that a tool makes about its capabilities. Fields added to the MCP Tool object in future protocol revisions that are consumed by the language model or influence tool selection SHOULD be included in the signing surface in subsequent CTMS versions.
2. Canonicalization. The canonical form is a JSON object containing the signing surface fields, extracted directly from the MCP Tool object. This object is canonicalized per RFC 8785 (JCS). The canonical form is the only input to the signing operation.
3. Signing. CTMS adopts a keyless signing model where publisher identity is established through OpenID Connect and signing is performed using short-lived certificates issued by a Sigstore-compatible certificate authority. No long-lived keys are required.
4. Versioning. Every change to any field in the signing surface requires a new signature. Changes to `name`, `inputSchema`, `outputSchema`, or `execution` constitute breaking changes and require a major version increment. Changes to `description`, `title`, or `annotations` constitute semantic changes and require a minor version increment.
5. Verification. CTMS defines a verification procedure for MCP clients. A compliant client performs manifest verification whenever it receives tool metadata from an MCP server, regardless of the protocol method that triggered the exchange. This includes, but is not limited to, `tools/list` responses and re-fetches following `notifications/tools/list_changed`. If verification fails, the client rejects the tool and does not pass its metadata to the language model. The client reports the verification failure, including the nature of the mismatch, to the user or operator. CTMS does not define client behavior for tools that have no associated manifest. Whether to accept unsigned tools is a client policy decision outside the scope of this specification.
6. Transparency log. All signing events are recorded in a Sigstore-compatible transparency log. The log provides an immutable, auditable record of Sealed Tool Manifest (STM) signing history. Clients cache verified STMs locally and verify against the transparency log at first use and periodically afterwards. Real-time log access is not required for every tool discovery operation. Implementations may operate a private Sigstore-compatible transparency log for STMs that cannot be published to a public log.


The following are explicitly outside the scope of this specification:

- Runtime policy enforcement. CTMS does not define or enforce policies governing which tools an AI model is permitted to invoke, under what conditions, or with what constraints. 
- Transport-level authentication, authorization, and runtime communication safeguards. CTMS does not address request authentication, rate limiting, traffic inspection, or other runtime communication safeguards between MCP clients and servers. Who is allowed to talk to whom, and how the communication is protected, are not this specification's concern.
- Server or tool registry. CTMS does not define a registry. The MCP Registry and downstream aggregators serve this function. CTMS manifests may be stored in or referenced by registries, but CTMS does not define registry behavior.
- Implementation correctness verification. CTMS verifies that a tool's declared capabilities have not changed from the signed version. It does not and cannot verify that the tool actually does what it claims. A tool that is correctly signed but incorrectly implemented will pass verification. We return to this limitation in Section 9.3.
- Threat detection and vulnerability scanning. CTMS does not scan tool descriptions for known attack patterns, malicious prompts, or vulnerabilities. CTMS ensures claim integrity, it does not evaluate claim safety.

Governance of this specification (including the process for proposing changes, managing breaking revisions, maintaining the `https://ctms.dev/v1/tool-manifest` predicate type URI, and testing conformance) is defined in a separate governance document. The technical specification does not prescribe a governance model.


### 1.3 Relationship to MCP

CTMS is a complementary specification to the Model Context Protocol. It does not modify, extend, or replace any part of the MCP protocol. The MCP specification explicitly acknowledges the absence of a mechanism to verify tool description integrity and defers this concern to the broader ecosystem (see Section 1.1). CTMS is a response to that deferral.

Within the MCP architecture of Host, Client, and Server, CTMS introduces responsibilities at two points. On the publisher side, the entity responsible for an MCP server creates and signs a Sealed Tool Manifest (STM) before deployment. The MCP server itself is unmodified. It continues to respond to `tools/list` as it normally would, with no awareness of CTMS. On the client side, a CTMS-compliant client compares the runtime tool metadata received from the server against the signed STM. This verification occurs **before** tool metadata is passed to the language model.

CTMS does not introduce new MCP protocol methods, message types, or schema modifications. Existing servers and clients continue to function as they do today. CTMS is opt-in and backwards-compatible.

Future revisions of the MCP specification could facilitate CTMS adoption, for example by defining a protocol method for retrieving STMs directly from a server. CTMS does not depend on any such changes and is designed to operate with the MCP protocol as currently specified.


### 1.4 Relationship to existing standards and prior art

CTMS integrates with the existing software supply chain security ecosystem rather than introducing parallel mechanisms.

in-toto. CTMS adopts the in-toto attestation format (v1) as the envelope for Sealed Tool Manifests (STMs). An STM is structured as an in-toto statement. The subject identifies the tool (server name and tool name). The predicate contains the canonical signing surface. STMs can be consumed by existing in-toto verification tooling without modification. The predicate type is specific to CTMS and is defined in Section 3.

SLSA. The Supply-chain Levels for Software Artifacts (SLSA) framework defines graduated levels of supply chain integrity. CTMS does not implement SLSA directly, but its guarantees can be mapped to the SLSA level vocabulary. An STM signed via Sigstore with a transparency log entry provides guarantees comparable to SLSA Build L2. Provenance is generated by an independent platform (Sigstore) rather than self-attested by the publisher alone, and the signing event is recorded in a tamper-evident log. Organizations that require stronger guarantees, such as third-party audit signatures or hardened signing environments, may extend STMs to achieve SLSA Build L3-equivalent assurance. This is outside the scope of version 1.0.

Sigstore. CTMS uses Sigstore as its signing and transparency infrastructure. Sigstore's certificate authority (Fulcio) issues short-lived signing certificates bound to publisher identity via OpenID Connect. Sigstore's transparency log (Rekor) records all signing events in an append-only, cryptographically verifiable ledger. These services are free, publicly operated under the Linux Foundation's OpenSSF, and adopted by major package ecosystems including npm and PyPI. CTMS does not depend on a specific Sigstore deployment. Implementations may operate private Sigstore-compatible infrastructure where required. We chose Sigstore over building a custom signing infrastructure for the same reason we chose in-toto over a custom envelope: the ecosystem already exists, and reimplementing it would have cost adoption without adding capability.

Prior art. Beyond the Radosevich and Halloran attack demonstrations cited in Section 1.1, several works have proposed defensive mechanisms. Li et al. (2025) demonstrated a dual-signature verification framework, and the ETDI framework (Bhatt et al., 2025) introduced OAuth-enhanced tool definitions with JWS signing. These works address authentication and access control aspects of MCP tool security. CTMS addresses a complementary concern: establishing a canonical, verifiable record of what a tool claims to do, with a versioning taxonomy and verification procedure designed for independent interoperability. Hou et al. (2025) surveyed the MCP ecosystem and identified tool validation and supply chain auditability as open research gaps.



## 2. Terminology

RFC 2119 Keywords. The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in RFC 2119.

MCP terms. The following terms are used as defined in the Model Context Protocol Specification (2025-11-25):

- MCP Host: the application that hosts the language model and one or more MCP clients.
- MCP Client: the component within the host that communicates with an MCP server.
- MCP Server: the external process that exposes tools, resources, and prompts to MCP clients.
- Tool object: the JSON object returned by an MCP server in response to a `tools/list` request, describing a single tool's name, description, schema, annotations, and execution properties.

CTMS terms. The following terms are defined by this specification:

- Signing surface: the set of fields from the MCP Tool object that constitute the tool's semantic claim about its capabilities. The signing surface for CTMS v1.0 consists of: `name`, `title`, `description`, `inputSchema`, `outputSchema`, `annotations`, `execution`.
- Canonical form: the deterministic byte representation of the signing surface, produced by applying JSON Canonicalization Scheme (JCS) per RFC 8785. Semantically identical tool metadata always produces identical bytes regardless of the serialization used by the MCP server.
- Sealed Tool Manifest (STM): the signed, immutable attestation of a tool's declared capabilities. An STM consists of the canonical form wrapped in an in-toto attestation envelope and signed via a Sigstore-compatible signing mechanism. The STM is the primary artifact defined by this specification.
- Publisher: the entity that creates and signs an STM. The publisher is identified by an OpenID Connect identity bound to the signing certificate. The publisher is not necessarily the developer of the MCP server. It is the party that attests to the tool's declared capabilities.
- Manifest verification: the process by which an MCP client compares the tool metadata received at runtime from an MCP server against a corresponding STM to determine whether the metadata matches the signed claim.
- Breaking change: a change to any of the following signing surface fields: `name`, `inputSchema`, `outputSchema`, `execution`. Breaking changes alter the tool's programmatic contract and require a major version increment of the STM.
- Semantic change: a change to any of the following signing surface fields: `description`, `title`, `annotations`. Semantic changes alter what the language model reads about the tool without changing its programmatic contract, and require a minor version increment of the STM.
- Manifest drift: the condition in which the tool metadata returned by an MCP server at runtime diverges from the corresponding STM. Manifest drift may result from malicious tampering, developer error, or unauthorized updates. CTMS-compliant clients detect manifest drift through manifest verification.
- Transparency log: an append-only, cryptographically verifiable ledger in which all STM signing events are recorded. The transparency log provides an immutable audit trail of what was signed, by whom, and when. CTMS requires a Sigstore-compatible transparency log (e.g., Rekor).



## 3. Sealed Tool Manifest

Each tool exposed by an MCP server gets its own STM. A server that exposes n number of tools will have n number of independent STMs, each signed and versioned separately. This per-tool granularity is intentional: tools within the same server can change at different rates, be maintained by different teams, and have different trust requirements. Section 4.1 addresses the operational cost of signing multiple STMs per server, and Section 6.2 addresses the verification cost on the client side.

### 3.1 Signing surface definition

The signing surface is the set of fields from the MCP Tool object whose values constitute the semantic claim that a tool makes about its capabilities. Any change to a signing surface field alters the claim and requires a new STM.

The signing surface for CTMS v1.0 consists of the following fields:

| Field | MCP status | Description |
|---|---|---|
| `name` | Required | Unique identifier for the tool |
| `title` | Optional | Human-readable display name |
| `description` | Optional | Human-readable description of functionality |
| `inputSchema` | Required | JSON Schema defining expected input parameters |
| `outputSchema` | Optional | JSON Schema defining expected output structure |
| `annotations` | Optional | Properties describing tool behavior (ToolAnnotations) |
| `execution` | Optional | Execution-related properties including task support. The internal structure of this field is defined by the MCP specification version in effect at the time of signing. CTMS signs the field's contents as-is. |

The MCP Tool object also contains `icons` and `_meta` fields. These are excluded from the signing surface. `icons` is a presentation concern that does not affect the tool's semantic claim. `_meta` is reserved protocol metadata managed by the MCP framework, not by the tool publisher.

The MCP specification describes `annotations` as advisory hints that are "not guaranteed to provide a faithful description of tool behavior." CTMS includes annotations in the signing surface precisely because they are untrusted by default. Signing them establishes a verifiable record of what the publisher declared, which is the precondition for any trust policy a client may apply.

When constructing the signing surface, only fields that are present in the Tool object as returned by the MCP server are included. Fields that are absent from the server's response MUST be omitted from the signing surface. They MUST NOT be included as null or with default values. The verifier MUST apply the same rule: if the runtime Tool object does not contain a field, that field MUST be omitted from the verification input. The canonical form is determined by the fields present at signing time. Verifiers MUST compare against the canonical form as signed, not against what the current MCP specification version would define for those fields. If a newer MCP version adds sub-fields to `execution` or another signing surface field, those sub-fields are not part of the canonical form unless the STM was signed with them present.

In practice, the most frequently changed signing surface field will be `description`, as publishers refine how they explain their tools to language models. Changes to `inputSchema` are less common but more consequential; see Section 5.1 for how the change taxonomy handles this.

Fields added to the MCP Tool object in future protocol revisions that are consumed by the language model or influence tool selection MUST be included in the signing surface in subsequent CTMS versions.

### 3.2 Canonicalization procedure

The canonical form is produced by applying the following procedure:

1. Extract. From the Tool object returned by the MCP server, extract only the fields defined in the signing surface (Section 3.1). Discard all other fields.
2. Construct. Create a JSON object containing only the extracted fields. The object MUST NOT contain any fields outside the signing surface.
3. Dereference. If `inputSchema` or `outputSchema` contains JSON Schema `$ref` references, the implementer MUST resolve all `$ref` pointers by inlining the referenced schema, producing a self-contained schema with no remaining `$ref` keywords.

   **Reference scope.** All `$ref` pointers MUST be fragment-only references to definitions within the same schema document (i.e., beginning with `#/`). External URI references (e.g., `https://example.com/schemas/foo.json`) MUST NOT appear in the signing surface. Publishers whose Tool object schemas use external references MUST resolve and inline them before the Tool object is served by the MCP server.

   **Cycle detection.** Implementations MUST detect reference cycles before beginning resolution. Recursive `$ref` structures, where resolution would create a cycle (e.g., a definition that references itself directly or indirectly), MUST be rejected as non-canonicalizable. Publishers whose schemas contain recursive references MUST restructure the schema to eliminate the recursion before signing.

   **Post-resolution cleanup.** After resolution, `$defs` and `definitions` keywords MUST be removed at all nesting levels. Composition keywords (`oneOf`, `anyOf`, `allOf`, `if`/`then`/`else`) MUST be preserved as structural elements and MUST NOT be merged or flattened. In particular, `allOf` branches MUST NOT be merged into a single schema object. Merging semantics vary across JSON Schema libraries and would produce different canonical forms from different implementations.

   **Determinism.** The same input schema MUST always produce the same dereferenced output. Implementers SHOULD validate their output against the test vector in Appendix A.7.
4. Canonicalize. Apply JSON Canonicalization Scheme (JCS) per RFC 8785 to the constructed object. This produces a deterministic byte sequence in which:
  - Object keys are sorted lexicographically by Unicode code point at all nesting levels
  - Insignificant whitespace is removed
  - Numbers and strings are normalized per RFC 8785

The canonicalization applies recursively to all nested structures, including the contents of `inputSchema`, `outputSchema`, and `annotations`.
5. Output. The resulting byte sequence is the canonical form. This byte sequence is the sole input to the signing operation defined in Section 4.

Implementers MUST use a JCS implementation that fully conforms to RFC 8785. Partial or non-conformant implementations will produce different byte sequences and cause verification failures. **This is not a theoretical risk, it is the most likely source of interoperability problems in practice.** A JCS library that sorts keys by byte value rather than Unicode code point will produce correct output for ASCII keys and silently wrong output for everything else. Test with non-ASCII tool names before shipping.

### 3.3 Schema

An STM is structured as an in-toto attestation statement (v1) with a CTMS-specific predicate type. The complete STM has the following structure:

```json
{
  "payloadType": "application/vnd.in-toto+json",
  "payload": {
    "_type": "https://in-toto.io/Statement/v1",
    "subject": [
      {
        "name": "io.github.user/weather-server/get_weather",
        "digest": {
          "sha256": "<hex-encoded SHA-256 digest of the canonical form>"
        }
      }
    ],
    "predicateType": "https://ctms.dev/v1/tool-manifest",
    "predicate": {
      "ctmsVersion": "1.0",
      "manifestVersion": {
        "major": 1,
        "minor": 0
      },
      "serverVersion": "2.1.0",
      "signingTimestamp": "2026-03-22T14:30:00Z",
      "canonicalForm": {
        "name": "get_weather",
        "description": "Get current weather information for a location",
        "inputSchema": {
          "type": "object",
          "properties": {
            "location": {
              "type": "string",
              "description": "City name or zip code"
            }
          },
          "required": ["location"]
        }
      }
    }
  },
  "signatures": [
    {
      "keyid": "",
      "sig": "<base64-encoded signature>"
    }
  ]
}
```

Subject. The subject name MUST be a qualified identifier in the format {namespace}/{toolName}. The namespace MUST be one of:
- The server's registered name from an MCP-compatible registry using reverse DNS notation (e.g., io.github.user/weather-server/get_weather), or
- The publisher's OIDC identity followed by the server name (e.g., github.com/user123/weather-server/get_weather)

The namespace format used MUST be consistent across all STMs produced by the same publisher for the same server. The subject digest MUST be the SHA-256 hash of the canonical form as defined in Section 3.2.

Predicate. The predicate contains:
- `ctmsVersion`: the version of the CTMS specification this STM conforms to.
- `manifestVersion`: the version of this STM, consisting of major and minor integers as defined in Section 5.
- `serverVersion`: the version of the MCP server (`serverInfo.version`) at the time the STM was signed. Clients use this field to detect server version changes that may indicate updated tool metadata (see Section 6.1, step 2).
- `signingTimestamp`: the time at which the STM was signed, in RFC 3339 format. This timestamp is informational since the authoritative signing time is recorded in the transparency log. In the keyless signing model, the signing certificate's validity window (typically 10 minutes) naturally constrains the possible divergence between `signingTimestamp` and the log timestamp. The signing must occur within the certificate's validity period, and the log entry must be recorded while the certificate is still valid. A divergence exceeding the certificate validity window would cause the certificate verification in Section 6.1, step 8 to fail.
- `canonicalForm`: the signing surface fields extracted from the MCP Tool object. When serialized within the predicate, these fields are in their canonical (JCS) representation.

Signatures. The signatures array is inherited from the in-toto envelope format. CTMS v1.0 STMs MUST contain exactly one signature, produced as defined in Section 4. The signature is computed over the canonical form, not over the full in-toto statement. Future versions of CTMS MAY define semantics for additional signatures (e.g., co-signing, counter-signatures, audit attestations). v1.0 verifiers MUST reject an STM with zero signatures and SHOULD ignore additional entries beyond the first. See Section B.12 for the rationale.


## 4. Signing

### 4.1 Signing procedure

The signing input is the canonical form produced by the procedure defined in Section 3.2. The signing operation produces a Sealed Tool Manifest (STM) structured as an in-toto attestation envelope as defined in Section 3.3.

The signing procedure is as follows:

1. Authenticate. The publisher authenticates with an OpenID Connect (OIDC) identity provider. The OIDC identity (e.g., github.com/user123 or corp.example.com/build-service) becomes the publisher identity bound to the signing certificate.
2. Obtain certificate. A Sigstore-compatible certificate authority (e.g., Fulcio) issues a short-lived X.509 signing certificate. The certificate binds the publisher's OIDC identity to an ephemeral key pair and is valid for a limited window (typically 10 minutes). The publisher's private key exists only for the duration of the signing operation.
3. Sign. The publisher computes a digital signature over the canonical form using the ephemeral private key. The algorithm MUST be ES256 for the Community and Enterprise profiles; the Sovereign profile permits alternatives per Section 8.
4. Record and assemble. The signing event is recorded in a Sigstore-compatible transparency log. The recorded event includes the signature, the signing certificate, and the artifact digest. The log entry provides the authoritative timestamp for the signing event. Once recorded, the STM is assembled as an in-toto attestation envelope containing the payload, signature, and signing certificate. The ephemeral private key is discarded.

The signing procedure MUST be performed in its entirety. An STM that lacks a transparency log entry is not valid, regardless of whether the signature itself is cryptographically correct.

When a server exposes multiple tools, the publisher authenticates once (step 1), obtains one certificate (step 2), and signs all tool canonical forms with the same certificate in a single session. Steps 3 and 4 are repeated per tool but are independent and may be performed concurrently. The certificate validity window (typically 10 minutes) is sufficient for signing a large number of tools in one batch.

Publishers SHOULD review tool descriptions for accuracy, safety, and absence of injected instructions before signing. The signing operation attests to the content as provided. It does not evaluate whether the content is safe, accurate, or free of embedded prompt injection. Once signed, a malicious description carries the publisher's institutional credibility (see Section 9.3).

Publishers SHOULD sign the new STM and confirm the transparency log entry before deploying updated tool metadata to the MCP server. If the server begins returning updated metadata before the corresponding STM is available, clients will detect manifest drift and reject the tool until the new STM propagates. This sign-then-deploy ordering avoids an operational window during which legitimate updates are indistinguishable from tampering.

### 4.2 Key representation and certificate lifecycle

CTMS uses keyless signing. No long-lived key pairs are generated, distributed, or managed by publishers. The trust anchor is the publisher's OIDC identity, not a persistent key.

The signing certificate issued during step 2 of the signing procedure is an X.509 certificate containing:
- The publisher's OIDC identity (issuer and subject claims)
- The ephemeral public key
- A validity window corresponding to the signing operation

The certificate is embedded in the STM envelope. Verifiers do not need to fetch the certificate separately. Because the certificate is short-lived, verification of an STM does not depend on the certificate's validity window. Instead, verification confirms that:
- The certificate was valid at the time recorded in the transparency log entry
- The transparency log entry exists and is consistent with the STM

No keys need to be rotated, revoked, or protected at rest. See Section 9.1 for what happens when these trust assumptions are violated.

### 4.3 Publisher identity

The publisher is the entity that attests to a tool's declared capabilities by signing an STM. Publisher identity is established through OIDC authentication at signing time and permanently recorded in the transparency log.

A publisher identity may represent:
- An individual developer (e.g., github.com/user123)
- An organizational build system (e.g., corp.example.com/ci-pipeline)
- A government entity (e.g., agency.gov/signing-authority)

The OIDC provider used for publisher authentication is determined by the conformance profile in effect (Section 8). The Community profile permits any OIDC provider. The Enterprise profile requires an organization-managed provider. The Sovereign profile requires a government-operated or nationally accredited provider.

Verifiers SHOULD present the publisher identity to users as part of the verification result. This allows users to make trust decisions based on who signed the STM, not only whether the signature is valid.

### 4.4 Conformance profiles

CTMS defines three conformance profiles that specify the permitted signing infrastructure, algorithms, identity providers, and transparency log requirements. All profiles share the same canonical form, envelope format, and verification procedure. They differ only in the operational and cryptographic constraints applied to signing and logging.

The three profiles are:
- Community: for open-source and publicly distributed MCP servers
- Enterprise: for regulated industries and organizational deployments
- Sovereign: for government, military, and national security use cases

The full specification of each profile, including its requirements across signing, verification, and transparency logging, is defined in Section 8. Sections 5 through 7 of this specification note where requirements vary by profile and reference Section 8 for the applicable constraints.

Organizations MAY define custom conformance profiles that extend or restrict the requirements of an existing profile, provided that the custom profile satisfies all baseline requirements defined in this specification. Custom profiles MUST be documented and made available to verifiers.


## 5. Versioning

### 5.1 Change taxonomy

Every change to any field in the signing surface requires a new STM with a new version. The change taxonomy classifies each change as either breaking or semantic based on which field was modified. Section B.6 explains why even "non-breaking" changes require re-signing.

Breaking changes are changes to fields that define the tool's programmatic contract: the interface that callers use to invoke the tool and interpret its results. A change is classified as breaking if it modifies any of the following fields:

- `name`: the tool's identifier changes, making existing references invalid
- `inputSchema`: the parameters the tool accepts change in any way, including adding optional parameters, removing parameters, changing types, or modifying constraints
- `outputSchema`: the structure of the tool's return value changes
- `execution`: execution-related properties including task support. A change to `taskSupport` (e.g., from `"optional"` to `"required"`) alters whether existing clients can invoke the tool.

Breaking changes require a major version increment. Classifying all `execution` changes as breaking is a conservative default. The `execution` field is a container whose internal structure is defined by the MCP specification, and future MCP versions may add sub-fields with purely advisory semantics. Future CTMS versions MAY reclassify specific `execution` sub-fields as semantic changes once their semantics are established and the impact on client behavior is understood.

Semantic changes are changes to fields that alter what the language model or user reads about the tool without modifying its programmatic contract. A change is classified as semantic if it modifies any of the following fields:

- `description`: the human-readable explanation of the tool's functionality
- `title`: the human-readable display name
- `annotations`: the behavioral hints (`readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`)

Semantic changes require a minor version increment. The distinction matters to downstream clients: a major version bump signals that integrations may break, while a minor bump signals that the tool works the same way but explains itself differently.

Any change that modifies fields in both categories simultaneously (e.g., changing both `description` and `inputSchema`) is treated as a breaking change and requires a major version increment.

### 5.2 Version identifiers

STM versions follow a major.minor format represented as two integers in the STM predicate (see Section 3.3).

The initial version of an STM is 1.0. There is no pre-stable or zero-major versioning. When a publisher creates the first STM for a tool, it is version 1.0.

Version increments follow these rules:

- A breaking change increments the major version by one and resets the minor version to zero (e.g., 1.3 becomes 2.0).
- A semantic change increments the minor version by one (e.g., 1.3 becomes 1.4).
- Each new version requires a new STM with a new signature and a new transparency log entry.

STM versioning is independent of the MCP server's own version. A server at version 3.0.0 may have tools with STMs at version 1.0, 1.5, or 4.0. The STM version tracks changes to the tool's declared capabilities, not changes to the server's implementation. Version numbers are not required to be contiguous. A publisher may increment from 1.0 to 1.5 if intermediate versions were signed internally but never published, or simply as a publisher decision. The only requirement is that each published version is strictly greater than the previous one in the same lineage (Section 5.3).

### 5.3 Lineage

An STM lineage is the sequence of STM versions for a given tool published by a given publisher. The lineage is identified by the combination of the subject name (Section 3.3) and the publisher identity (Section 4.3).

If a different publisher signs an STM for the same tool, this constitutes a new lineage. The new lineage begins at version 1.0 regardless of the version reached by the previous publisher's lineage. A tool may have multiple concurrent lineages from different publishers. The verifier determines which lineage to trust based on publisher identity.

A lineage MUST be monotonically increasing. A publisher MUST NOT issue an STM with a version lower than or equal to any previously published STM in the same lineage. Verifiers operating under the Enterprise or Sovereign profile MUST reject an STM whose version is not greater than the most recent STM in the same lineage recorded in the transparency log. Verifiers operating under the Community profile SHOULD reject such STMs. Without MUST-level enforcement, the version rollback mitigation described in Section 9.2 is advisory rather than guaranteed.


## 6. Verification

### 6.1 Client verification procedure

A CTMS-compliant client MUST perform the following verification procedure whenever it receives tool metadata from an MCP server. This includes, but is not limited to, `tools/list` responses and re-fetches following `notifications/tools/list_changed`.

The verification procedure is as follows:

1. **Receive.** The client receives tool metadata from the MCP server via any protocol method that returns tool information.

2. **Detect server version.** The client compares the server version reported during initialization (`serverInfo.version`) against the `serverVersion` field in any cached STM. If the server version has changed, the client MUST re-fetch the STM from the transparency log (proceeding to step 3), as the tool metadata may have changed. Note that `serverVersion` is a performance optimization hint, not a security control. It tells the client when to re-fetch, reducing unnecessary log lookups. The actual security guarantee comes from steps 4 through 6 (extract, canonicalize, compare), which detect tampering regardless of what `serverVersion` reports. Because a server may never increment its version string (whether through negligence or intent), clients SHOULD periodically re-verify against the transparency log even when no version change is detected. A re-verification interval of no more than half the profile's maximum cache duration is RECOMMENDED.

3. **Retrieve STM.** The client retrieves the STM for the tool by looking up the qualified subject name (Section 3.3) in the transparency log. If a valid cached STM exists and no server version change has been detected, the client MAY use the cached STM subject to the caching rules defined in Section 6.2. If no STM is found for the tool, the tool is unsigned. The handling of unsigned tools is outside the scope of this specification. The client MUST verify that the subject name in the retrieved STM corresponds to the expected qualified name for the tool being verified. If the subject name does not match, the STM MUST be rejected. This check is necessary because the cryptographic signature covers the canonical form (which contains the tool `name`) but not the full subject name (which includes the namespace). See Section B.13 for the rationale.

4. **Extract.** From the runtime Tool object, extract the signing surface fields as defined in Section 3.1. Absent fields are omitted.

5. **Canonicalize.** Apply the canonicalization procedure defined in Section 3.2 to produce the canonical form of the runtime tool metadata.

6. **Compare.** Compare the canonical form produced in step 5 against the `canonicalForm` in the STM predicate. If they do not match byte-for-byte, verification fails with a manifest drift failure. Note: a step 6 failure may also result from a canonicalization bug rather than actual drift. If the tool metadata appears unchanged but the canonical forms diverge, implementers should investigate whether their JCS implementation conforms to RFC 8785 before attributing the failure to tampering.

7. **Verify signature.** Verify the cryptographic signature in the STM against the canonical form using the public key in the embedded signing certificate. If the signature is invalid, verification fails with a signature failure.

8. **Verify certificate.** Confirm that the signing certificate was issued by a Sigstore-compatible certificate authority and that the certificate was valid at the time recorded in the transparency log entry. If the certificate cannot be validated, verification fails with a certificate failure.

9. **Verify log entry.** Confirm that a corresponding entry exists in the transparency log and that the entry is consistent with the STM (matching digest, signature, and certificate). If the log entry is missing or inconsistent, verification fails with a log integrity failure.

Implementations MAY reorder steps 7 through 9 provided all three are performed. For example, verifying the log entry before the signature avoids revealing to an attacker whether the client holds a cached STM. This is a minor consideration for Community deployments but may be relevant for Sovereign operational security.

10. **Verify publisher.** Extract the publisher identity from the signing certificate and evaluate whether the publisher is trusted for this tool. The mechanism for establishing publisher trust is a client policy decision. Clients operating under the Enterprise or Sovereign profile SHOULD maintain an explicit publisher trust list mapping expected publisher identities to specific tools or tool namespaces. A client that accepts any publisher identity technically satisfies this step but provides no protection against the competing lineage attack described in Section 9.3. If the publisher is untrusted, verification fails with a publisher trust failure.

11. **Accept.** If all preceding steps succeed, the tool metadata is verified. The client passes the tool metadata to the language model.

If verification fails at any step, the client MUST reject the tool and MUST NOT pass its metadata to the language model. No fallback. No "warn and continue." The client MUST report the failure to the user or operator, including the failure type as defined in Section 6.3.

A conformance test suite is included in the same repository as this specification. The reference implementation includes 67 offline tests covering canonicalization, schema dereferencing, STM construction and parsing, change taxonomy, and offline verification. These tests validate against the test vectors in Appendix A and the `vectors/` directory. Future additions to the test suite will cover:

- Each caching scenario per conformance profile
- Canonicalization of tool names containing non-ASCII characters (testing JCS Unicode code point sorting vs. byte value sorting)
- Numeric values exercising JCS number normalization (scientific notation, trailing zeros)
- Negative test vectors showing the output of common dereferencing mistakes (e.g., merged `allOf` branches)
- End-to-end verification including signature validation, certificate chain verification, log entry consistency checks, and revocation hint processing

### 6.2 STM retrieval and caching

The primary mechanism for STM retrieval is lookup by qualified subject name in the transparency log. Publishers SHOULD ensure that the tool's subject name (Section 3.3) is consistent across the MCP Registry, the transparency log, and the server's `serverInfo.name`.

To facilitate discovery, servers SHOULD include an STM reference in the `serverInfo` metadata returned during initialization. The reference SHOULD be a well-known field `ctms` defined as a JSON object with the following schema:

- `version` (string): optional. The CTMS specification version this hint conforms to. Defaults to `"1.0"` if absent. Clients that do not recognize the version SHOULD process the fields they understand and ignore the rest. Clients MAY warn the operator that a newer hint version is available.
- `logUrl` (string, URI): optional. The base URL of the transparency log where the server's STMs are recorded.
- `subjectPrefix` (string): optional. The qualified subject name prefix for this server's tools (e.g., `"io.github.weathertools/weather-server"`).

Servers that include the `ctms` field SHOULD include at least one of `logUrl` or `subjectPrefix`. Both MAY be present simultaneously. Clients MUST ignore a `ctms` field that contains neither `logUrl` nor `subjectPrefix`, and MUST ignore any additional keys in the `ctms` object that they do not recognize.

This reference is an unsigned discovery hint. It is not part of the signing surface and is not covered by the STM. A malicious server can set the field to anything, which is why the verification procedure (Section 6.1) does not depend on it. The reference reduces the number of log lookups a client must attempt, nothing more.

STM discovery is not fully specified in CTMS v1.0. A client encountering a tool for the first time needs the qualified subject name to query the transparency log, but the subject name is established by the publisher and may not be derivable from the information available to the client. The `ctms` hint in `serverInfo` addresses this but is unsigned and untrusted. Three discovery paths are available:

- **Convention-based construction.** The client constructs a candidate subject name from the server's `serverInfo.name` and the tool's `name` field using the naming conventions defined in Section 3.3. Clients SHOULD implement this as the baseline discovery mechanism, since it requires no external dependencies. It works when publishers follow the naming conventions and fails silently when they do not.

  For MCP servers accessible over HTTP (e.g., SSE transport), publishers SHOULD serve STMs at a well-known URI following the pattern `/.well-known/ctms/{toolName}.stm`, where `{toolName}` is the tool's `name` field. The served file MUST be the complete STM as defined in Section 3.3 (full in-toto envelope including payload and signatures), served with content type `application/json`. This gives clients a deterministic, zero-dependency lookup path for the common case.

  This convention does not apply to stdio-transport servers, which have no HTTP endpoint. Stdio-transport servers rely on convention-based name construction and registry lookup for STM discovery. Publishers of stdio-transport servers SHOULD register with an MCP-compatible registry to enable discovery.
- **Server hint.** The `ctms` field in `serverInfo` provides a subject name prefix or log URL. The client uses this to narrow the log search. The hint is untrusted, but a wrong hint only causes discovery failure. It cannot cause the client to accept a forged STM, because the verification procedure (Section 6.1) validates the STM independently of how it was discovered.
- **Registry lookup.** If the MCP Registry or a compatible registry maintains STM references for registered servers, the client can resolve the qualified subject name through the registry. Clients SHOULD prefer registry lookup over the other paths when a compatible registry is available. This is the most reliable path but depends on registry adoption.

If none of these paths produces a valid STM, the tool is treated as unsigned.

When a client receives multiple tools from a single `tools/list` response, each tool is verified independently. The log lookups for all tools in the response are independent and may be performed concurrently. Clients MAY batch log queries by subject name prefix to reduce the number of network round-trips. For servers exposing a large number of tools, initial verification involves latency proportional to the tool count. Clients SHOULD provide progress indication to users during first-time verification of such servers.

Clients SHOULD cache verified STMs locally to avoid requiring a transparency log lookup on every tool metadata exchange. The following caching rules apply:

- A cached STM is valid until the client detects a change in server version, receives a `notifications/tools/list_changed` notification, or the cache duration exceeds the maximum defined by the conformance profile (Section 8). Note that a `tools/list_changed` notification followed by a manifest drift failure may indicate a legitimate update where the server deployed new metadata before the publisher signed the corresponding STM (see Section 4.1). Clients SHOULD retry STM retrieval after a short delay before treating this as a permanent failure.
- When a cached STM is used, the client MUST still perform steps 4 through 6 of the verification procedure (extract, canonicalize, compare) against the runtime tool metadata. Caching skips the log lookup, not the comparison.
- If the transparency log is unreachable, the client's behavior is determined by the conformance profile in effect:
- **Community profile**: the client MAY proceed with a cached STM if one exists.
- **Enterprise profile**: the client MAY proceed with a cached STM only if the cache age does not exceed the maximum duration defined by the profile. If the cache has expired, the client MUST reject the tool.
- **Sovereign profile**: the client MUST NOT proceed without a confirmed transparency log verification. If the log is unreachable, the client MUST reject the tool.

### 6.3 Failure handling

When verification fails, the client MUST report a typed failure. The straightforward cases: an **unsigned tool** has no STM at all (handling is a client policy decision). **Manifest drift** means the runtime metadata does not match the signed canonical form; the tool has changed since signing, whether through tampering or developer error. **Signature failure** means the STM has been corrupted or forged.

The remaining failure types require more context:

| Failure type | Condition | Meaning |
|---|---|---|
| Certificate failure | The signing certificate cannot be validated against the certificate authority or was not valid at the recorded signing time | The signing infrastructure may be compromised or misconfigured. |
| Log integrity failure | The transparency log entry is missing, inconsistent, or cannot be verified | The signing event may not have been properly recorded, or the log may be compromised. |
| Publisher trust failure | The publisher identity in the signing certificate is not trusted by the client | The STM was signed by a publisher the client or operator has not approved. |
| Version regression | The STM version is lower than or equal to a previously verified STM in the same lineage | A possible rollback attack. An older STM is being presented as current. |
| Log unreachable | The transparency log cannot be contacted and profile rules prohibit cached verification | The client cannot complete verification due to infrastructure unavailability. |

The client MUST include the failure type, the tool's qualified subject name, and the publisher identity (if available) in the failure report. For manifest drift, the client SHOULD include the expected and actual canonical form digests. For certificate failure, the client SHOULD include the certificate details.

When a `tools/list` response contains multiple tools and verification fails for one or more but not all, the client faces a trust decision beyond individual tool verification. A server that returns tampered metadata for one tool has demonstrated that its tool metadata pipeline is compromised or misconfigured. The individually verified tools may still be trustworthy, or the server may have been selectively targeted. For the Community profile, whether to reject the entire tool set is a client policy decision. For the Enterprise and Sovereign profiles, the baseline is stricter: clients operating under these profiles SHOULD reject all tools from a server where any tool fails with manifest drift, signature failure, or log integrity failure, as these failure types are evidence of pipeline compromise. Publisher trust failure and unsigned tool handling remain policy decisions under all profiles.


## 7. Transparency Log

### 7.1 Log structure

The transparency log is an append-only, cryptographically verifiable data structure that records all STM signing events. The log provides tamper evidence, inclusion verifiability, and historical auditability for the CTMS ecosystem.

The log MUST be implemented as a Merkle tree consistent with the design principles of RFC 9162 (Certificate Transparency Version 2.0). Specifically, the log MUST provide:

- **Append-only semantics.** Once an entry is recorded, it MUST NOT be modified, replaced, or deleted. The log MUST reject any operation that would alter an existing entry.
- **Inclusion proofs.** For any entry, the log MUST be able to produce a cryptographic proof that the entry is contained in the log at a specific tree size.
- **Consistency proofs.** For any two tree sizes, the log MUST be able to produce a cryptographic proof that the smaller tree is a prefix of the larger tree. That is, no entries were modified or removed as the log grew.
- **Signed tree heads.** The log MUST periodically publish a signed tree head representing the current root hash and tree size. Verifiers and monitors use signed tree heads to detect log misbehavior.

CTMS requires a Sigstore-compatible transparency log (e.g., Rekor). Implementations MAY operate a private transparency log instance provided it satisfies all requirements defined in this section. Private log instances MUST implement the same data structures, proof mechanisms, and query interfaces as the public Sigstore Rekor service.

If a transparency log operator decommissions a log instance, the operator MUST publish a decommissioning notice with sufficient lead time for clients and monitors to migrate. All log entries MUST be transferable to a successor log. The successor log MUST preserve the original log timestamps, inclusion proofs, and signed tree heads from the decommissioned log. For the Sovereign profile, where retention periods may extend to 20 years or longer, log operators SHOULD plan for organizational succession and ensure that retention obligations survive the decommissioning of any individual log instance.

### 7.2 Entry format

Each transparency log entry records a single STM signing event. A log entry MUST contain:

| Field | Description |
|---|---|
| Subject name | The qualified tool identifier as defined in Section 3.3 |
| Artifact digest | The SHA-256 hash of the canonical form |
| Signature | The cryptographic signature over the canonical form |
| Signing certificate | The X.509 certificate issued by the certificate authority, containing the publisher's OIDC identity |
| Log timestamp | The time at which the log recorded the entry, assigned by the log server (not the publisher) |
| STM version | The `manifestVersion` (major.minor) of the STM |

The log timestamp is the authoritative record of when the signing event occurred. Publishers MUST NOT be able to influence the log timestamp. The `signingTimestamp` field in the STM predicate (Section 3.3) is informational only; the log timestamp takes precedence in any dispute.

Log entries MUST be searchable by at minimum:
- Subject name (exact match and prefix match)
- Publisher identity (the OIDC subject in the signing certificate)
- Time range (entries recorded between two timestamps)

These query capabilities enable both monitoring and auditing functions as defined in Section 7.3.

In addition to signing event entries, the transparency log MUST support a **revocation hint** entry type. A revocation hint is a signed log entry published by a publisher to signal that one or more previously signed STM versions in a lineage should no longer be considered current. A revocation hint entry MUST contain:

| Field | Description |
|---|---|
| Subject name | The qualified tool identifier of the revoked STM |
| Revoked versions | The specific `manifestVersion`(s) being revoked, or a range |
| Publisher identity | The OIDC identity of the publisher, which MUST match the publisher identity of the revoked STM's lineage |
| Reason | An optional human-readable reason for revocation |
| Log timestamp | Assigned by the log server, as with signing event entries |

The revocation hint MUST be signed by the same publisher identity that signed the original STM. A revocation hint from a different identity MUST be rejected by the log. This prevents an attacker from revoking a legitimate publisher's STMs.

CTMS v1.0 defines the revocation hint entry type and requires log support for recording and querying revocation hints. Since v1.0 defers client-side revocation enforcement, monitoring is the only active revocation path. Monitors operating under the Enterprise or Sovereign profile MUST alert on revocation hint entries for monitored tools. Monitors operating under the Community profile SHOULD alert on revocation hint entries. The integration of revocation hints into the client verification procedure and cache invalidation model is deferred to a future version of this specification. See Section 9.3 for the implications of this deferral.

### 7.3 Monitor and auditor roles

CTMS defines two log consumer roles. These are functions, not specific people or systems. An individual, an automated process, or a service can fill either role.

**Monitor.** A monitor watches the transparency log on an ongoing basis to detect events of interest. The most important signal is an unexpected publisher signing an STM for a monitored tool. Version regressions within a lineage (a possible rollback attack) are also worth alerting on. How often to poll and what else to watch for are implementation decisions. The log is not required to provide push notifications.

**Auditor.** An auditor queries the transparency log after the fact, typically for a compliance review, security investigation, or regulatory inquiry. Auditors need complete history, not real-time alerts. Typical queries include:
- All STM versions for a specific tool, from first signing to present
- The STM that was current for a specific tool at a specific point in time
- All STMs signed by a specific publisher within a time range
- Log consistency: confirming that no entries have been modified or removed since the last audit
- Comparing signing timestamps against deployment records to verify the correct STM was in effect during a specific operational window

The transparency log MUST retain entries for a minimum duration determined by the conformance profile in effect (Section 8). The Community profile defines a minimum retention period suitable for open-source ecosystems. The Enterprise and Sovereign profiles define extended retention periods aligned with regulatory and compliance requirements.


## 8. Compliance Mapping

### 8.1 Conformance profiles

CTMS defines three conformance profiles that specify operational and cryptographic constraints for different deployment contexts. All profiles share the same canonical form (Section 3), envelope format (Section 3.3), change taxonomy (Section 5), and verification procedure (Section 6.1). They differ in the requirements applied to signing infrastructure, identity providers, transparency logging, caching, and retention.

An implementation claims conformance to exactly one profile. All requirements of the claimed profile MUST be satisfied. A higher-tier profile satisfies all requirements of lower-tier profiles. An implementation conforming to the Sovereign profile also satisfies the Enterprise and Community profile requirements.

#### Cross-profile verification

Conformance profiles apply independently to publishers and clients. A publisher signs STMs according to its claimed profile's signing requirements (algorithm, OIDC provider, CA, transparency log). A client verifies STMs according to its own profile's verification requirements (cache duration, log-unreachable behavior). When a client operating under the Enterprise or Sovereign profile verifies an STM signed under the Community profile, the client applies its own profile's verification rules. All profiles require ES256 support, which ensures that any client can verify any STM regardless of the profile under which it was signed.

Whether a client accepts an STM from a publisher operating under a different profile is a publisher trust policy decision, enforced at step 10 of the verification procedure (Section 6.1). A Sovereign client may accept Community-signed STMs for non-sensitive tools, or it may require that all consumed STMs originate from government-accredited identities. CTMS provides the verification mechanism; it does not dictate trust policy.

Organizations that need to consume tools from a lower-tier profile under their own profile's constraints have a second option: sign their own STM for the tool. For example, a government agency that wants to consume an open-source weather tool under the Sovereign profile can review the tool, then sign an STM using its own sovereign infrastructure (government OIDC, government CA, government transparency log). Per Section 5.3, this creates a new lineage under the government's publisher identity, starting at version 1.0. The original publisher's Community-profile lineage continues to exist for other consumers. The same tool can have concurrent lineages from different publishers operating under different profiles.

#### Community profile

The Community profile is intended for open-source and publicly distributed MCP servers where the primary goal is to establish a baseline of verifiable trust with minimal operational burden.

| Requirement | Specification |
|---|---|
| Signing algorithm | ECDSA with P-256 (ES256). MUST be supported. |
| OIDC provider | Any OpenID Connect provider MAY be used. |
| Certificate authority | Public Sigstore Fulcio instance or compatible. |
| Transparency log | Public Sigstore Rekor instance or compatible. |
| Cache duration | Clients MAY cache verified STMs. Clients that cache MUST NOT retain a cached STM for longer than 72 hours. |
| Re-verification interval | Clients SHOULD re-verify against the transparency log at least every 36 hours, even if no server version change is detected. |
| Log-unreachable behavior | Clients MAY proceed with a cached STM if one exists. |
| Retention period | Log entries MUST be retained for a minimum of 2 years. |

Publishers operating under the Community profile SHOULD maintain their own signing records (certificates, log entry receipts, and STM copies) beyond the log's minimum retention period. Compliance investigations or security incidents may require evidence that extends past the 2-year window.

Because the Community profile permits any OIDC provider, the assurance level of a Community-profile STM varies with the security posture of the provider used. Clients operating under any profile SHOULD evaluate the OIDC issuer, not just the publisher identity subject, as part of the trust decision at step 10 of the verification procedure (Section 6.1). An STM signed via a hardened organizational provider and an STM signed via a low-assurance consumer provider carry different levels of confidence in the publisher's identity, even if both are valid Community-profile STMs.

#### Enterprise profile

The Enterprise profile is intended for regulated industries, organizational deployments, and environments subject to compliance requirements such as SOX, HIPAA, GxP, or equivalent frameworks. It increases assurance by requiring organization-managed identity and permitting private infrastructure.

| Requirement | Specification |
|---|---|
| Signing algorithm | ECDSA with P-256 (ES256). MUST be supported. Ed25519 MAY be supported as an additional option. |
| OIDC provider | MUST be an organization-managed identity provider (e.g., Azure AD, Okta). Public consumer identity providers (e.g., personal Gmail accounts) MUST NOT be used. |
| Certificate authority | Organization-operated Sigstore-compatible instance, or the public Sigstore Fulcio instance with organizational OIDC. |
| Transparency log | Organization-operated Sigstore-compatible instance RECOMMENDED. Public Rekor MAY be used if organizational policy permits. |
| Cache duration | Clients MAY cache verified STMs. Clients that cache MUST NOT retain a cached STM for longer than 24 hours. If the cache age exceeds 24 hours and the transparency log is unreachable, the client MUST reject the tool. |
| Re-verification interval | Clients SHOULD re-verify against the transparency log at least every 12 hours, even if no server version change is detected. |
| Log-unreachable behavior | Clients MAY proceed with a cached STM only if the cache age does not exceed 24 hours. Otherwise, the client MUST reject the tool. |
| Retention period | The retention period MUST be determined by the organization's applicable regulatory, legal, and compliance requirements. The organization MUST document the retention period in its conformance profile documentation. The retention period MUST NOT be less than 5 years. |

#### Sovereign profile

The Sovereign profile is intended for government, military, and national security use cases where the highest level of assurance is required and infrastructure must be under sovereign control.

| Requirement | Specification |
|---|---|
| Signing algorithm | Determined by applicable national cryptographic policy (e.g., CNSA 2.0 for US federal systems). ES256 MUST be supported as a fallback for interoperability. |
| OIDC provider | MUST be a government-operated or nationally accredited identity provider. |
| Certificate authority | MUST be government-operated or nationally accredited. Public Sigstore infrastructure MUST NOT be used as the primary certificate authority. |
| Transparency log | MUST be government-operated or nationally accredited. The log MAY be air-gapped from public networks. Public Sigstore infrastructure MUST NOT be used as the primary transparency log. |
| Cache duration | Caching is not permitted. Clients MUST verify every tool metadata exchange against the transparency log in real time. |
| Re-verification interval | Not applicable. Every tool metadata exchange requires real-time log verification. |
| Log-unreachable behavior | Clients MUST NOT proceed. If the transparency log is unreachable, the client MUST reject the tool. |
| Retention period | The retention period MUST be determined by the applicable national records retention policy. The retention period MUST NOT be less than 20 years. Where national policy requires permanent retention, the log MUST support indefinite retention. |

#### Custom profiles

Organizations MAY define custom conformance profiles that extend or restrict the requirements of an existing profile. A custom profile MUST:
- Identify which base profile it extends (Community, Enterprise, or Sovereign)
- Satisfy all requirements of the base profile
- Document all deviations from or additions to the base profile
- Be made available to all verifiers that will encounter STMs signed under the custom profile

All MUST-level requirements of the base profile are inherited unchanged by the custom profile. Only SHOULD-level and MAY-level requirements may be modified. For example, a custom profile based on Enterprise MUST NOT permit a different OIDC provider category, a weaker signing algorithm, or a retention period shorter than 5 years, because these are MUST-level requirements of the Enterprise profile. A custom profile MAY tighten requirements (e.g., reduce cache duration below 24 hours) or add new requirements not present in the base profile.

### 8.2 SLSA level alignment

CTMS conformance profiles correspond to the following Supply-chain Levels for Software Artifacts (SLSA) Build track levels:

| CTMS profile | SLSA equivalent | Rationale |
|---|---|---|
| Community | Build L2 | Provenance is generated by an independent platform (Sigstore) rather than self-attested. The signing event is recorded in a tamper-evident transparency log. The publisher identity is established via OIDC, not self-declared. |
| Enterprise | Build L2+ | Satisfies L2 and adds organizational identity controls and private infrastructure, but does not require the build-environment hardening defined in SLSA Build L3. Organizations MAY achieve L3-equivalent assurance by combining CTMS with hardened signing environments. |
| Sovereign | Build L3 (contextual) | The combination of sovereign-controlled infrastructure, real-time verification, no caching, and government-accredited identity providers provides assurances comparable to SLSA Build L3 within the sovereign context. Full SLSA L3 equivalence depends on the hardening measures applied to the signing environment, which are determined by national policy rather than this specification. |

CTMS does not claim formal SLSA certification for any profile. The mapping above is provided to assist organizations in positioning CTMS within their existing SLSA compliance frameworks. Organizations seeking formal SLSA assessment should evaluate their complete supply chain, of which CTMS is one component.


## 9. Security Considerations

This section documents the security assumptions, mitigated threats, and residual risks of CTMS. Residual risks (Section 9.3) deserve particular attention because they define what CTMS cannot do even when everything works correctly.

The [CSA MCP Security Project](https://modelcontextprotocol-security.io) maintains a TTP taxonomy covering 12 attack categories across the MCP ecosystem. CTMS directly addresses 7 TTPs (primarily in categories 2, 6, 8, and 11) and partially addresses 7 more. A detailed mapping of CTMS coverage against the CSA taxonomy is provided in the companion threat model document (`THREAT_MODEL.md`).

### 9.1 Trust assumptions

CTMS relies on the following assumptions. If any assumption is violated, the security guarantees of the specification are weakened or invalidated.

**Client implementation correctness.** This is the assumption we can least help with. The security guarantees of CTMS depend entirely on the client correctly implementing the verification procedure defined in Section 6.1. A client that skips steps, accepts bad signatures, or swallows errors provides no security at all. The best manifests in the world do not help if the verifier is broken. This specification defines what clients MUST do and it cannot ensure that implementations are correct. Every other assumption below is about infrastructure that can be monitored, audited, and replaced. A broken client is invisible until something goes wrong. The conformance test suite (Section 6.1) partially mitigates this risk by providing test vectors that implementations can validate against, but passing a test suite is not a proof of correctness.

**OIDC provider integrity.** CTMS relies on the OIDC identity provider to correctly authenticate publisher identity. If an OIDC provider is compromised, an attacker could obtain a valid signing certificate for an arbitrary identity and produce a validly signed STM with malicious content. The Enterprise and Sovereign profiles reduce exposure by requiring organization-managed or government-operated providers. The transparency log provides a forensic trail for post-incident investigation.

A related but distinct attack vector is OIDC token theft. An attacker who obtains a valid OIDC token from the publisher's environment (e.g., a leaked CI pipeline secret, an exposed environment variable, or a compromised build agent) can authenticate to the certificate authority and sign an STM under the publisher's identity without compromising the OIDC provider itself. This is the most likely real-world attack path against Community-profile publishers, whose CI pipelines may not have the same hardening as Enterprise or Sovereign environments. Mitigations include scoping CI tokens to specific actions, using short-lived credentials, and monitoring for unexpected signing events in the transparency log.

**Certificate authority integrity.** CTMS relies on the Sigstore-compatible certificate authority (e.g., Fulcio) to issue certificates only to authenticated identities. A compromised CA could issue certificates without proper authentication. The transparency log records all issued certificates, so monitors can detect unexpected issuances. The Sovereign profile requires government-operated certificate authorities under direct institutional control.

**Transparency log integrity.** CTMS relies on the transparency log to faithfully record all signing events and to present a consistent view to all clients. A compromised log operator could omit entries or present different log contents to different clients (a split-view attack). Merkle tree consistency proofs (Section 7.1) allow any client to detect log inconsistencies by comparing signed tree heads. Organizations operating private logs SHOULD implement independent witnesses or cross-log verification.

For private transparency logs under the Enterprise and Sovereign profiles, there is a transitive trust dependency that deserves explicit acknowledgment. The client trusts the log's signed tree heads, which means the client trusts the log operator's signing key. If the same organization operates both the private log and the private certificate authority, that organization can forge an entire STM lifecycle (signing certificate, STM signature, and log entry) with no external evidence of the forgery. Independent witnesses or cross-log verification partially mitigate this, but only if the witnesses are genuinely independent of the log operator. Organizations deploying private CTMS infrastructure SHOULD ensure that the log operator and the certificate authority are under separate administrative control, or that an independent external witness monitors the log.

### 9.2 Threats mitigated

**Tool description poisoning.** Tool descriptions are signed at publish time and verified at discovery time. Any modification to a tool description after signing results in a manifest drift failure during verification. This applies whether the modification is malicious injection, unauthorized editing, or man-in-the-middle alteration.

**Rug pull / post-deployment changes.** CTMS detects unauthorized changes to tool metadata after deployment. If a server returns tool metadata that differs from the signed STM, verification fails. The transparency log retains the original signed description for forensic comparison.

**Version rollback attacks.** The monotonically increasing version requirement (Section 5.3) prevents an attacker from presenting an older, potentially vulnerable STM as current. Verifiers reject any STM whose version is not greater than the most recently verified version in the same lineage.

**Manifest drift.** CTMS detects unintentional divergence between signed and runtime tool metadata. The cause is immaterial: developer error, deployment misconfiguration, and delayed updates are all detected.

**Audit trail absence.** The transparency log provides an immutable, timestamped record of all STM signing events, satisfying regulatory and compliance requirements for verifiable tool description history.

### 9.3 Residual risks

The following risks remain even when CTMS is correctly implemented. These are not edge cases. They are inherent limitations of what a signing-and-verification specification can achieve. Implementers and adopters should understand these clearly before depending on CTMS in production.

**Implementation correctness is not verified.** This is the most important limitation to understand. CTMS verifies that a tool's declared capabilities have not changed from the signed version. It says nothing about whether those capabilities are truthful. A tool whose description says "reads a file" but whose implementation deletes a file will pass CTMS verification without issue, because the description has not been tampered with. CTMS is a seal, not a code review. Implementation correctness verification is outside the scope of this specification (Section 1.2).

**Cross-tool shadowing is detectable but not preventable.** A correctly signed tool description may still contain instructions that influence how the language model uses other tools. CTMS cannot prevent the language model from following cross-tool instructions embedded in a validly signed description. That is a runtime model-behavior problem, not a signing problem.

What CTMS does contribute is auditability. Because the description is signed and recorded in the transparency log, the content that caused the cross-tool influence is preserved, attributable to a specific publisher, and inspectable after the fact. Monitors can flag descriptions that reference other tools by name or contain instruction-like patterns. Publishers can be held accountable for descriptions that manipulate model behavior beyond the tool's own scope.

The actual prevention of cross-tool influence requires client-side mechanisms: description isolation, tool-scoped context boundaries, or content policy enforcement. These are complementary to CTMS and outside its scope.

**Compromised publisher identity.** If an attacker gains control of a publisher's OIDC account, they can sign a validly structured STM with malicious content. The STM will pass verification because the identity, certificate, and signature are all technically valid. Mitigation: the transparency log records the signing event, and monitors can detect the compromise after the fact. Organizations SHOULD implement monitoring for unexpected STM publications under their namespaces. The Enterprise and Sovereign profiles reduce this risk through organizational identity providers with stronger authentication controls (e.g., multi-factor authentication, conditional access policies).

**Identity migration breaks revocation.** CTMS ties publisher identity to the OIDC subject recorded at signing time. If a publisher's OIDC subject changes (due to an organizational rename, email domain migration, or identity provider switch) the publisher can no longer sign revocation hints for STMs signed under the previous identity, because the revocation hint must be signed by the same publisher identity as the original STM (Section 7.2). The prior STMs remain valid and verifiable, but the publisher has lost the ability to revoke them. Organizations planning identity migrations SHOULD publish new STMs under the new identity and sign revocation hints for the old lineage before the migration takes effect.

**Competing lineage attack.** An attacker who controls a different OIDC identity can publish a new STM lineage for an existing tool. The STM will be validly signed under the attacker's identity. Clients that do not maintain publisher trust policies (specifically, that do not restrict which publisher identities are accepted for a given tool) may accept the attacker's STM. Mitigation: clients SHOULD maintain a mapping of expected publisher identities for tools they depend on. Monitors SHOULD alert on new publisher lineages appearing for monitored tools.

**Denial of availability.** If the transparency log is unavailable, the Sovereign profile prevents all tool usage (by design). The Enterprise profile prevents tool usage once cached STMs expire. An attacker who can disrupt connectivity to the transparency log can therefore prevent an organization from using CTMS-verified tools. Mitigation: organizations operating under the Enterprise or Sovereign profile SHOULD deploy redundant transparency log infrastructure. The private log option (Section 7.1) allows organizations to operate log infrastructure within their own network boundary.

**Pre-signing poisoning and trust inversion.** CTMS signs whatever description the publisher provides. The specification has no way to judge whether a description is malicious or benign at signing time. That is a content analysis problem, not a cryptographic one.

If the publisher's development environment is compromised and a malicious description is introduced before signing, the resulting STM will contain the poisoned description with a perfectly valid signature. The signature proves the description has not changed. It does not prove the description was safe to begin with. Pre-deployment security scanning complements CTMS by evaluating description content before it is signed. Organizations that care about this threat vector should treat scanning and signing as two stages of the same pipeline, not as independent steps.

A signed malicious description may be treated as more trustworthy than a legitimate unsigned one. A client configured to block unsigned tools but accept signed ones will give a poisoned STM more credibility than an honest tool that simply has not been signed yet. This trust inversion is inherent to any signing system: a valid signature on bad content is more dangerous than no signature at all. It reinforces why publishers SHOULD review tool descriptions before signing (Section 4.1).

**No client-side revocation enforcement.** CTMS v1.0 defines a revocation hint entry type in the transparency log (Section 7.2), which allows publishers to signal that a previously signed STM should no longer be considered current. Monitors can detect and alert on revocation hints.

However, v1.0 does not integrate revocation hints into the client verification procedure or cache invalidation model. A client using a cached STM will not learn of a revocation hint until the next transparency log check, which may not occur until cache expiry. Under the Community profile, the exposure window is up to 72 hours. Under the Enterprise profile, up to 24 hours.

Integration of revocation hints into client-side verification is a candidate for a future version of this specification. The fundamental tension is that caching exists to avoid frequent log lookups, and revocation only helps if clients check the log. Resolving this requires careful design of polling intervals and their interaction with the profile-dependent caching model.


## 10. IANA Considerations

This specification requires no IANA registrations. All algorithms, envelope formats, and infrastructure are pre-existing.


## References

### Normative references

- **RFC 2119.** Bradner, S., "Key words for use in RFCs to Indicate Requirement Levels," BCP 14, RFC 2119, March 1997.
- **RFC 7515.** Jones, M., Bradley, J., and N. Sakimura, "JSON Web Signature (JWS)," RFC 7515, May 2015.
- **RFC 7517.** Jones, M., "JSON Web Key (JWK)," RFC 7517, May 2015.
- **RFC 8785.** Rundgren, A., Jordan, B., and S. Erdtman, "JSON Canonicalization Scheme (JCS)," RFC 8785, June 2020.
- **RFC 9162.** Laurie, B., Messeri, E., and R. Stradling, "Certificate Transparency Version 2.0," RFC 9162, December 2021.
- **MCP Specification.** Model Context Protocol Specification, version 2025-11-25. https://modelcontextprotocol.io/specification/2025-11-25
- **in-toto Attestation Framework.** in-toto Attestation Framework, v1. https://github.com/in-toto/attestation
- **SLSA.** Supply-chain Levels for Software Artifacts, v1.0. https://slsa.dev/spec/v1.0

### Informative references

- **Radosevich, B. and Halloran, J.T.** (2025). "MCP Safety Audit: LLMs with the Model Context Protocol Allow Major Security Exploits." Demonstrated tool description poisoning attacks against MCP servers, including malicious code execution, remote access, and credential theft. https://arxiv.org/abs/2504.03767
- **Li, X. et al.** (2025). "A Dual-Signature Verification Framework for MCP Tool Security." Proposed a dual-signature scheme for verifying tool description integrity.
- **Bhatt, M. et al.** (2025). "ETDI: Enhanced Tool Definition Interface for MCP." Introduced OAuth-enhanced tool definitions with JWS signing for MCP tool authentication and access control.
- **Hou, X. et al.** (2025). "Model Context Protocol (MCP): Landscape, Security Threats, and Future Research Directions." Surveyed the MCP ecosystem and identified tool validation and supply chain auditability as open research gaps.


## Appendix A: Examples

This appendix provides a complete worked example of an STM lifecycle: signing surface extraction, canonicalization, STM construction, and verification. The example uses a weather tool because it is simple enough to follow without domain knowledge. A real-world tool with a larger `inputSchema` or nested output types would produce a longer canonical form but follow the same procedure exactly.

### A.1 MCP Tool object (runtime)

The following Tool object is returned by an MCP server in response to a `tools/list` request:

```json
{
  "name": "get_weather",
  "title": "Get Weather",
  "description": "Get current weather information for a location, including temperature, conditions, and humidity.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "location": {
        "type": "string",
        "description": "City name or zip code"
      },
      "units": {
        "type": "string",
        "enum": ["celsius", "fahrenheit"],
        "description": "Temperature unit"
      }
    },
    "required": ["location"]
  },
  "annotations": {
    "readOnlyHint": true,
    "openWorldHint": true
  }
}
```

The server does not include `outputSchema` or `execution` because this tool does not define them. Per Section 3.1, absent fields are omitted from the signing surface. Most tools in practice will look like this: `name`, `description`, `inputSchema`, and possibly `annotations`. The full seven-field signing surface is the maximum, not the common case.

### A.2 Signing surface extraction

The publisher extracts only the signing surface fields that are present in the Tool object:

```json
{
  "name": "get_weather",
  "title": "Get Weather",
  "description": "Get current weather information for a location, including temperature, conditions, and humidity.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "location": {
        "type": "string",
        "description": "City name or zip code"
      },
      "units": {
        "type": "string",
        "enum": ["celsius", "fahrenheit"],
        "description": "Temperature unit"
      }
    },
    "required": ["location"]
  },
  "annotations": {
    "readOnlyHint": true,
    "openWorldHint": true
  }
}
```

The fields `outputSchema` and `execution` are not present in the Tool object and are therefore not included.

### A.3 Canonical form (JCS output)

Applying JCS (RFC 8785) to the signing surface produces the following byte sequence. Object keys are sorted lexicographically at all nesting levels and insignificant whitespace is removed:

```
{"annotations":{"openWorldHint":true,"readOnlyHint":true},"description":"Get current weather information for a location, including temperature, conditions, and humidity.","inputSchema":{"properties":{"location":{"description":"City name or zip code","type":"string"},"units":{"description":"Temperature unit","enum":["celsius","fahrenheit"],"type":"string"}},"required":["location"],"type":"object"},"name":"get_weather","title":"Get Weather"}
```

The SHA-256 digest of this byte sequence is computed and used as the subject digest in the STM.

### A.4 Complete STM

The signed STM, structured as an in-toto attestation envelope:

```json
{
  "payloadType": "application/vnd.in-toto+json",
  "payload": {
    "_type": "https://in-toto.io/Statement/v1",
    "subject": [
      {
        "name": "io.github.weathertools/weather-server/get_weather",
        "digest": {
          "sha256": "a1b2c3d4e5f6..."
        }
      }
    ],
    "predicateType": "https://ctms.dev/v1/tool-manifest",
    "predicate": {
      "ctmsVersion": "1.0",
      "manifestVersion": {
        "major": 1,
        "minor": 0
      },
      "serverVersion": "2.1.0",
      "signingTimestamp": "2026-03-22T14:30:00Z",
      "canonicalForm": {
        "annotations": {
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "Get current weather information for a location, including temperature, conditions, and humidity.",
        "inputSchema": {
          "properties": {
            "location": {
              "description": "City name or zip code",
              "type": "string"
            },
            "units": {
              "description": "Temperature unit",
              "enum": ["celsius", "fahrenheit"],
              "type": "string"
            }
          },
          "required": ["location"],
          "type": "object"
        },
        "name": "get_weather",
        "title": "Get Weather"
      }
    }
  },
  "signatures": [
    {
      "keyid": "",
      "sig": "<base64-encoded ES256 signature>"
    }
  ]
}
```

Note that the `canonicalForm` within the predicate has its keys in JCS-sorted order (alphabetical), which differs from the order in the original Tool object.

### A.5 Verification walkthrough

When a client connects to the weather server and receives the Tool object from Section A.1, it performs the verification procedure from Section 6.1:

1. **Receive.** The client receives the Tool object above from the MCP server.
2. **Detect server version.** The client checks `serverInfo.version` against any cached STM. Assume this is a first connection, so no cache exists.
3. **Retrieve STM.** The client queries the transparency log for subject name `io.github.weathertools/weather-server/get_weather` and retrieves the STM from Section A.4.
4. **Extract.** The client extracts the signing surface fields from the runtime Tool object: `name`, `title`, `description`, `inputSchema`, `annotations`. The fields `outputSchema` and `execution` are absent and omitted.
5. **Canonicalize.** The client applies JCS to produce the canonical form shown in Section A.3.
6. **Compare.** The client compares the canonical form against the `canonicalForm` in the STM predicate. They match byte-for-byte. This is the step that catches tampering. If even a single character in the description had been changed, the canonical forms would diverge here.
7. **Verify signature.** The client verifies the ES256 signature against the canonical form using the public key from the embedded signing certificate. The signature is valid.
8. **Verify certificate.** The client confirms the signing certificate was issued by Fulcio and was valid at the time recorded in the log entry.
9. **Verify log entry.** The client confirms the transparency log contains an entry matching the STM's digest, signature, and certificate.
10. **Verify publisher.** The client extracts the publisher identity (`github.com/weathertools`) from the signing certificate. The client's publisher trust policy accepts this identity.
11. **Accept.** All checks pass. The client passes the tool metadata to the language model.

### A.6 Version bump example

Later, the publisher updates the tool description to add wind speed information:

```
"description": "Get current weather information for a location, including temperature, conditions, humidity, and wind speed."
```

This is a change to the `description` field, which is a semantic change (Section 5.1). The publisher:

1. Constructs a new signing surface with the updated description
2. Produces a new canonical form via JCS
3. Signs the new canonical form, producing a new STM at version **1.1** (minor increment from 1.0)
4. Records the signing event in the transparency log

If the publisher instead added a new required parameter to `inputSchema`, that would be a breaking change requiring version **2.0**.

The weather tool example uses a flat `inputSchema` with no references or composition. Section A.7 provides a test vector that exercises `$ref`, `oneOf`, and `allOf`, which are the constructs most likely to cause interoperability problems in practice.


### A.7 Schema dereferencing test vector

This section provides a test vector for the dereferencing step (Section 3.2, step 3). The tool uses an `inputSchema` with `$ref`, `oneOf`, and `allOf`, which are the constructs most likely to produce divergent results across JSON Schema implementations. If your implementation produces the canonical form shown at the end of this section, your dereferencing is compatible.

**Tool object as returned by the MCP server:**

```json
{
  "name": "query_geo",
  "description": "Query geographic features by place name or coordinates.",
  "inputSchema": {
    "type": "object",
    "$defs": {
      "coordinates": {
        "type": "object",
        "properties": {
          "lat": { "type": "number" },
          "lon": { "type": "number" }
        },
        "required": ["lat", "lon"]
      }
    },
    "properties": {
      "target": {
        "oneOf": [
          {
            "type": "object",
            "properties": {
              "placeName": { "type": "string" }
            },
            "required": ["placeName"]
          },
          { "$ref": "#/$defs/coordinates" }
        ]
      },
      "options": {
        "allOf": [
          {
            "type": "object",
            "properties": {
              "format": { "type": "string", "enum": ["json", "geojson"] }
            }
          },
          {
            "type": "object",
            "properties": {
              "verbose": { "type": "boolean" }
            }
          }
        ]
      }
    },
    "required": ["target"]
  }
}
```

**After dereferencing (step 3):**

The `$ref` in the second `oneOf` branch is replaced with the contents of `$defs/coordinates`. The `$defs` keyword is removed. The `allOf` and `oneOf` structures are preserved as-is. The `allOf` branches are NOT merged into a single object.

```json
{
  "name": "query_geo",
  "description": "Query geographic features by place name or coordinates.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "target": {
        "oneOf": [
          {
            "type": "object",
            "properties": {
              "placeName": { "type": "string" }
            },
            "required": ["placeName"]
          },
          {
            "type": "object",
            "properties": {
              "lat": { "type": "number" },
              "lon": { "type": "number" }
            },
            "required": ["lat", "lon"]
          }
        ]
      },
      "options": {
        "allOf": [
          {
            "type": "object",
            "properties": {
              "format": { "type": "string", "enum": ["json", "geojson"] }
            }
          },
          {
            "type": "object",
            "properties": {
              "verbose": { "type": "boolean" }
            }
          }
        ]
      }
    },
    "required": ["target"]
  }
}
```

**Canonical form (after JCS, step 4):**

```
{"description":"Query geographic features by place name or coordinates.","inputSchema":{"properties":{"options":{"allOf":[{"properties":{"format":{"enum":["json","geojson"],"type":"string"}},"type":"object"},{"properties":{"verbose":{"type":"boolean"}},"type":"object"}]},"target":{"oneOf":[{"properties":{"placeName":{"type":"string"}},"required":["placeName"],"type":"object"},{"properties":{"lat":{"type":"number"},"lon":{"type":"number"}},"required":["lat","lon"],"type":"object"}]}},"required":["target"],"type":"object"},"name":"query_geo"}
```

Three things to verify against:

1. The `$ref` is resolved and `$defs` is gone.
2. The `allOf` is intact. The two branch objects are not merged into `{"type": "object", "properties": {"format": ..., "verbose": ...}}`. If your implementation merges them, the canonical form will differ and verification will fail.
3. The `oneOf` is intact. The two alternatives remain as separate array elements with the resolved `coordinates` schema inlined in place of the `$ref`.


## Appendix B: Design Rationale

This appendix documents the reasoning behind key design decisions in CTMS. These rationales are informational and do not carry normative weight.

### B.1 Why a sealed manifest rather than transport-level protection?

Transport-level protections (TLS, mTLS, OAuth) answer "am I talking to the right server?" They do not answer "is this server telling me what the publisher intended?" A compromised or misconfigured server can return any tool metadata over a perfectly authenticated connection. CTMS operates at the content layer. It verifies the message, not the messenger.

### B.2 Why JCS (RFC 8785) for canonicalization?

Without canonicalization, signing JSON is meaningless. The same logical object can be serialized with different key ordering, whitespace, and number formatting, producing different bytes and different signatures. JCS is the only JSON canonicalization scheme with an RFC designation. There was no real alternative to evaluate.

### B.3 Why keyless signing via Sigstore?

Key management is consistently the weakest link in signing systems. Keys get leaked, lost, stolen, or never rotated. Traditional PKI requires publishers to generate, store, protect, rotate, and distribute long-lived signing keys, and the history of software supply chain compromises is largely a history of that process failing. Sigstore sidesteps the problem entirely. The publisher authenticates via an existing OIDC identity, obtains a short-lived certificate, signs, and the private key is discarded. The trust anchor becomes "is this identity authentic?" rather than "is this key secure?" Organizations already invest heavily in answering the first question through their identity infrastructure. Asking them to also manage signing keys would have been the single largest barrier to CTMS adoption.

### B.4 Why in-toto attestation format?

We considered designing a custom envelope. We rejected it because it would have required every consumer to write a new parser for no functional gain. in-toto is already the standard envelope for supply chain attestations. Existing verification tooling, policy engines, and attestation storage systems all understand it. By structuring STMs as in-toto statements, CTMS gets ecosystem integration for free.

### B.5 Why three conformance profiles?

A single set of requirements would either be too permissive for government use cases or too burdensome for open-source adoption. The profile model allows CTMS to serve three deployment contexts (open-source community, regulated enterprise, and sovereign/government) under a single specification. All profiles share the same canonical form, envelope format, and verification procedure. They differ only in the operational constraints: who can sign, where the log lives, and how long entries are retained. Government and military environments have requirements that cannot be met by a single-tier specification.

### B.6 Why are all signing surface changes re-signed (not just "breaking" ones)?

The primary attack vector CTMS addresses is tool description poisoning, which operates through the `description` field, not through `inputSchema` or `outputSchema`. If description changes were permitted without re-signing, an attacker who gained write access to the server's tool metadata could modify the description to inject malicious instructions while the signature remained valid. The breaking/semantic distinction in CTMS controls the version number increment (major vs. minor), not whether re-signing is required. Every change to any signing surface field requires a new signature.

We debated on whether `annotations` should be in the signing surface at all, since behavioral hints like `readOnlyHint` are advisory and the MCP spec does not require clients to respect them. We included them because a changed `destructiveHint` can alter model behavior as much as a changed description. If a tool flips from "this is read-only" to "this may modify data," the model should treat that as a meaningful change in the tool's contract, even if the hint is technically non-binding.

### B.7 Why does a different publisher start a new lineage at 1.0?

The alternative is far worse. If publisher B could issue version 2.4 of a tool previously signed by publisher A, every client would need logic to decide whether that handoff was legitimate. Who authorized it? Was it a transfer of ownership or a hostile takeover? Resetting to 1.0 avoids the question entirely. Two publishers, two lineages, two independent trust decisions.

### B.8 Why hard block on verification failure?

A soft failure mode (warn and continue) undermines the security guarantee. If a client can proceed with a tool whose signature is invalid or whose description has drifted from the signed version, CTMS provides auditing but not protection. The specification requires hard block because description poisoning operates in real time. A post-hoc audit finding does not undo the actions the model was manipulated into performing. The conformance profiles provide flexibility for infrastructure availability (caching, log-unreachable behavior) without weakening the fundamental rule: a failed verification means the tool is not used.

### B.9 Why serverVersion triggers re-fetch?

Without this, a client could keep using a cached STM from server version 2.0 while the server has quietly upgraded to 3.0 with different tool metadata. The `serverVersion` field closes that gap. When the server version changes, the client re-verifies against the transparency log. This is cheap and prevents a class of stale-cache problems that would otherwise be invisible.

To be clear about what `serverVersion` is and is not: it is an optimization hint that reduces unnecessary log lookups. It is not a security control. A server that lies about its version (or never changes it) does not bypass CTMS. Steps 4 through 6 of the verification procedure (extract, canonicalize, compare) catch any mismatch between runtime metadata and the signed STM, regardless of what `serverVersion` reports. The worst a dishonest `serverVersion` can do is delay re-fetch until the next cache expiry or `tools/list_changed` notification.

### B.10 Why profile-dependent behavior when the log is unreachable?

The availability-vs-security tradeoff differs across deployment contexts. An open-source developer whose public Rekor instance is temporarily unreachable should not be blocked from using tools they verified yesterday. A government system processing classified data cannot tolerate uncertainty about whether the tool metadata has been tampered with since the last verification. The profile-dependent approach encodes these risk tolerances into the specification rather than leaving them as implementation decisions that each client would resolve differently.

### B.11 Why no zero-major versioning?

Some versioning schemes use 0.x to signal pre-stable or experimental status. CTMS prohibits this because an STM is a trust attestation, not a software release. A tool at STM version 0.3 would signal "this claim might change without notice," which undermines the purpose of signing it in the first place. If a publisher is not confident enough in a tool's description to commit to version 1.0, the tool should not be signed yet. The version number is cheap. A publisher can iterate through 1.0, 2.0, 3.0 as the tool stabilizes. Each version is a fresh attestation with a full signing event. Pre-stable versioning is a useful convention for code libraries. It is a liability for trust claims.

### B.12 Why exactly one signature in v1.0?

The in-toto envelope format allows multiple entries in the `signatures` array. CTMS v1.0 constrains this to exactly one. The reason is that multi-signature semantics are not simple. Does a second signature mean both signers must be trusted (AND)? Or that either is sufficient (OR)? Is a counter-signature an endorsement, an audit attestation, or something else? Who is expected to verify which signature? Each answer implies different client verification logic, and leaving this ambiguous would mean every implementation resolves the question differently. Future versions may define multi-signature semantics for specific use cases (enterprise co-signing, sovereign counter-signatures, third-party audit attestations) but only after the verification semantics are fully specified. For v1.0, one publisher, one signature, one verification path.

### B.13 Why does the signature cover the canonical form, not the full in-toto statement?

Standard in-toto practice signs the entire statement. CTMS signs only the canonical form (the signing surface fields). The reason: the canonical form is the semantic claim. The in-toto statement structure (subject name, predicate type, metadata) is the envelope, not the content. Signing the canonical form means the signature answers one question: "has the tool's declared capabilities changed?" The subject name, which includes the publisher's namespace, is not covered by the signature. This means an attacker who obtains a legitimately signed STM could in theory present it under a different subject name without invalidating the signature. The verification procedure closes this gap at step 3: the client MUST verify that the STM's subject name corresponds to the expected qualified name for the tool. The subject digest (SHA-256 of the canonical form) in the in-toto subject provides an additional binding: it ties the subject to the content. But the explicit subject name check is the normative defense.

