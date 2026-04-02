# CTMS Test Vectors

Machine-readable test vectors extracted from the CTMS specification Appendix A. Use these to validate your implementation's canonicalization, dereferencing, and verification logic.

## Weather tool (Appendix A.1-A.4)

A simple tool with a flat `inputSchema` and no `$ref` or composition keywords.

| File | Description | Spec section |
|---|---|---|
| `weather-tool-object.json` | MCP Tool object as returned by `tools/list` | A.1 |
| `weather-signing-surface.json` | Signing surface fields extracted from the Tool object | A.2 |
| `weather-canonical-form.txt` | JCS canonical form (raw bytes, no trailing newline expected) | A.3 |
| `weather-stm.json` | Complete STM as an in-toto envelope (placeholder signature and digest) | A.4 |

### How to use

1. Parse `weather-tool-object.json`
2. Extract signing surface fields. Compare against `weather-signing-surface.json`
3. Apply JCS canonicalization. Compare output bytes against `weather-canonical-form.txt`
4. Compute SHA-256 of the canonical form. This becomes the subject digest in the STM

## Query geo tool (Appendix A.7)

A tool with `$ref`, `oneOf`, and `allOf` in `inputSchema`. Tests the dereferencing step (Section 3.2, step 3).

| File | Description | Spec section |
|---|---|---|
| `query-geo-tool-object.json` | MCP Tool object with `$ref` and composition keywords | A.7 |
| `query-geo-dereferenced.json` | Signing surface after `$ref` resolution and `$defs` removal | A.7 |
| `query-geo-canonical-form.txt` | JCS canonical form of the dereferenced signing surface | A.7 |

### How to use

1. Parse `query-geo-tool-object.json`
2. Extract signing surface fields
3. Dereference: resolve the `$ref`, remove `$defs`, preserve `oneOf` and `allOf` as-is. Compare against `query-geo-dereferenced.json`
4. Apply JCS canonicalization. Compare output bytes against `query-geo-canonical-form.txt`

### What to check

- The `$ref` to `#/$defs/coordinates` is resolved (inlined) and `$defs` is removed
- The `allOf` branches are NOT merged into a single object
- The `oneOf` alternatives remain as separate array elements
- If your canonical form differs from `query-geo-canonical-form.txt`, your implementation is not compatible

## Notes

- The `.txt` files contain the exact byte sequence that should be the input to the signing operation. No trailing newline.
- The `weather-stm.json` file contains placeholder values for the signature and digest fields. These are structural examples, not cryptographically valid. The reference implementation will provide end-to-end test vectors with real signatures.
