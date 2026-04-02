# CTMS Governance

This document describes how the Canonical Tool Manifest Specification (CTMS)
is maintained, how changes are proposed and accepted, and how the project
may transition to a broader governance model in the future.

## Current governance model

CTMS is currently maintained under a single-editor model. The editor has
final authority on all specification changes, roadmap decisions, and release
timing.

**Editor:** George Kanellopoulos

Community input is welcomed through the processes described in
[CONTRIBUTING.md](../CONTRIBUTING.md). All contributions are reviewed by the
editor. The editor may accept, reject, or request changes to any proposal.

## Specification changes

### Non-breaking changes

Changes that do not alter normative requirements (clarifications, examples,
editorial fixes, new test vectors) may be accepted by the editor at any time.
These do not require a new specification version.

### Minor specification versions

Changes that add new normative requirements without breaking existing
conformant implementations (e.g., new optional fields, new conformance
profile options) require a minor version increment (e.g., 1.0 to 1.1).

### Breaking specification versions

Changes that would break existing conformant implementations (e.g., adding
required fields to the signing surface, changing the canonicalization
procedure, modifying the verification steps) require a major version
increment (e.g., 1.x to 2.0). Breaking changes require:

1. A public issue describing the change and its rationale
2. A review period of at least 30 days
3. Consideration of migration impact on existing implementations
4. Editor approval

### Predicate type URI

The predicate type URI (`https://ctms.dev/v1/tool-manifest`) is versioned by
the major specification version. A new major version introduces a new
predicate type URI (e.g., `https://ctms.dev/v2/tool-manifest`). The editor
is responsible for maintaining the predicate type URI and ensuring that each
URI resolves to the corresponding specification version.

## Conformance and test suite

The conformance test suite is maintained alongside the specification. Changes
to the test suite follow the same review process as non-breaking specification
changes. New test vectors may be contributed by the community through the
process described in [CONTRIBUTING.md](../CONTRIBUTING.md).

An implementation claims conformance to a specific specification version and
conformance profile. The test suite provides the reference vectors for
validating that claim. The project does not certify implementations.

## Transition to community governance

If CTMS is adopted by a standards body or foundation (e.g., OpenSSF, Linux
Foundation AI), governance will transition to the model required by that
organization. This may include:

- Replacing the single-editor model with a technical steering committee
- Adopting a formal consensus or voting process for specification changes
- Transferring ownership of the predicate type URI
- Establishing a formal certification or conformance program

Until such a transition occurs, the single-editor model remains in effect.
The editor commits to documenting any governance transition publicly in this
repository.

## License

All specification text and project content is licensed under
[Apache 2.0](../LICENSE).
