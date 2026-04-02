# Contributing to CTMS

Thank you for your interest in CTMS. This document explains how to contribute.

## Ways to Contribute

- **Spec feedback.** Open an issue if you find ambiguities, gaps, or conflicts in the specification. Reference the section number.
- **Test vectors.** Submit new conformance test vectors as JSON files under `vectors/`. Include the expected canonical form and a description of what the vector tests.
- **Implementation work.** Contributions to the reference implementation are welcome. Open an issue first to discuss the approach.
- **Security issues.** If you find a security vulnerability in the specification or reference implementation, do not open a public issue. Email gkanellopoulos@protonmail.com instead.

## Process

1. Open an issue describing what you want to change and why.
2. Fork the repository and create a branch.
3. Make your changes. Keep commits focused and messages clear.
4. Open a pull request referencing the issue.
5. All contributions require sign-off under the [Developer Certificate of Origin (DCO)](https://developercertificate.org/). Add `Signed-off-by: Your Name <your@email.com>` to your commit messages, or use `git commit -s`.

## Style

- Specification text follows [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119) for normative language (MUST, SHOULD, MAY).
- All other text (README, comments, commit messages, documentation) uses plain, direct language.

## License

By contributing, you agree that your contributions will be licensed under [Apache 2.0](LICENSE).
