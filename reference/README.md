# CTMS Reference Implementation

Python library and CLI for signing and verifying MCP tool metadata using the CTMS specification.

## Install

Requires Python 3.10 or later.

```bash
pip install -e .
```

For development (includes pytest):

```bash
pip install -e ".[dev]"
```

## CLI

The `ctms` command provides four subcommands.

### canonicalize

Produce the canonical form of an MCP Tool object.

```bash
# Print canonical form to stdout
ctms canonicalize tool.json

# Write to file and print digest
ctms canonicalize tool.json -o canonical.txt --digest
```

### sign

Sign an MCP Tool object and produce a Sealed Tool Manifest (STM). Opens a browser for Sigstore OIDC authentication.

```bash
# Sign against Sigstore staging (for testing)
ctms sign tool.json \
    --subject-name io.github.org/server/tool_name \
    --server-version 1.0.0 \
    --staging \
    -o tool.stm.json

# Sign against Sigstore production
ctms sign tool.json \
    --subject-name io.github.org/server/tool_name \
    --server-version 1.0.0 \
    -o tool.stm.json
```

### verify

Verify an MCP Tool object against an STM.

```bash
# Full verification (Sigstore signature + canonical form)
ctms verify tool.json tool.stm.json --staging

# With publisher trust check
ctms verify tool.json tool.stm.json --staging \
    --trusted-publisher user@example.com

# Offline verification (canonical form comparison only, no Sigstore)
ctms verify tool.json tool.stm.json --offline

# JSON output
ctms verify tool.json tool.stm.json --offline --output-format json
```

### inspect

Display the contents of an STM file.

```bash
ctms inspect tool.stm.json
ctms inspect tool.stm.json --output-format json
```

## Library

The `ctms` package can be imported directly for integration into MCP clients or other tools.

### Canonicalize a tool

```python
from ctms import canonicalize, extract_signing_surface, canonical_digest

tool_object = {
    "name": "get_weather",
    "description": "Get current weather.",
    "inputSchema": {"type": "object", "properties": {"location": {"type": "string"}}}
}

surface = extract_signing_surface(tool_object)
canonical_form = canonicalize(tool_object)
digest = canonical_digest(canonical_form)
```

### Verify a tool against an STM (offline)

```python
import json
from ctms.verify import verify_canonical_form
from ctms.errors import ManifestDriftError

tool_object = json.load(open("tool.json"))
stm_dict = json.load(open("tool.stm.json"))

try:
    verify_canonical_form(tool_object, stm_dict)
    print("Tool metadata matches the signed manifest.")
except ManifestDriftError as e:
    print(f"Tampered: expected {e.expected_digest}, got {e.actual_digest}")
```

### Verify with Sigstore and publisher trust

```python
from ctms.verify import verify_tool
from ctms.errors import CTMSVerificationError

try:
    result = verify_tool(
        tool_object=tool_object,
        stm_dict=stm_dict,
        trusted_publishers=["publisher@example.com"],
        staging=True,  # False for production
    )
    print(f"Verified. Publisher: {result.publisher_identity}")
except CTMSVerificationError as e:
    print(f"Failed [{e.failure_type}]: {e}")
```

### Classify changes between tool versions

```python
from ctms import classify_change, next_version
from ctms._types import ManifestVersion

old_surface = {"name": "tool", "description": "Old description."}
new_surface = {"name": "tool", "description": "New description."}

change = classify_change(old_surface, new_surface)  # "semantic"
version = next_version(ManifestVersion(1, 0), change)  # ManifestVersion(1, 1)
```

## Examples

### Attack demonstration

Shows five attack scenarios (description poisoning, rug pull, schema injection, annotation tampering) and how CTMS blocks each one. No Sigstore authentication needed.

```bash
python examples/attack_demo.py
```

### MCP client proof-of-concept

Simulates an MCP client verifying a tool at runtime before exposing it to the LLM.

```bash
# With a Sigstore-signed STM
python examples/mcp_client_poc.py ../vectors/weather-tool-object.json examples/weather-signed.stm.json --staging

# With publisher trust
python examples/mcp_client_poc.py ../vectors/weather-tool-object.json examples/weather-signed.stm.json \
    --staging --trusted-publisher user@example.com
```

### Example signed STM

`examples/weather-signed.stm.json` is a real STM for the weather tool vector, signed against Sigstore staging. You can verify it:

```bash
ctms verify ../vectors/weather-tool-object.json examples/weather-signed.stm.json --staging
```

## Tests

```bash
# Run all offline tests
pytest tests/ -v

# Run tests for a specific module
pytest tests/test_canonicalize.py -v
```

67 tests covering canonicalization, dereferencing, STM construction/parsing, change taxonomy, offline verification, and CLI commands. All tests run offline against the [test vectors](../vectors/).

## Architecture

```
src/ctms/
    __init__.py          Public API re-exports
    _types.py            Constants, dataclasses (ManifestVersion, STM, etc.)
    errors.py            Typed exceptions for each verification failure
    canonicalize.py      Signing surface extraction + JCS (Section 3.2)
    dereference.py       $ref resolution for JSON Schema (Section 3.2, step 3)
    stm.py               STM construction and parsing (Section 3.3)
    version.py           Change taxonomy and version logic (Section 5)
    sign.py              Sigstore signing pipeline (Section 4.1)
    verify.py            11-step verification procedure (Section 6.1)
    cli/
        main.py          Click CLI entry point
        canonicalize_cmd.py
        sign_cmd.py
        verify_cmd.py
        inspect_cmd.py
```
