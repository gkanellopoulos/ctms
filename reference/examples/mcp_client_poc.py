"""MCP client integration proof-of-concept.

Demonstrates how an MCP client uses CTMS to verify tool metadata
at runtime before allowing an LLM to invoke a tool.

This script simulates the client-side flow:
1. Client connects to an MCP server and receives tool definitions
2. Client looks up the corresponding STM for each tool
3. Client verifies the tool metadata against the STM
4. Client makes a trust decision based on verification result

Usage:
    python examples/mcp_client_poc.py TOOL_FILE STM_FILE [--trusted-publisher EMAIL]

Example with test vectors:
    python examples/mcp_client_poc.py ../vectors/weather-tool-object.json test-weather.stm.json

Example with publisher trust:
    python examples/mcp_client_poc.py ../vectors/weather-tool-object.json test-weather.stm.json \
        --trusted-publisher user@example.com
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def simulate_mcp_client(
    tool_file: str,
    stm_file: str,
    trusted_publishers: list[str] | None = None,
    staging: bool = False,
) -> None:
    """Simulate an MCP client verifying a tool at runtime."""

    from ctms.errors import CTMSVerificationError
    from ctms.verify import verify_canonical_form, verify_tool

    # --- Step 1: Client receives tool definition from MCP server ---
    print("[1] Receiving tool definition from MCP server...")
    with open(tool_file) as f:
        tool_object = json.load(f)
    print(f"    Tool name: {tool_object.get('name')}")
    print(f"    Description: {tool_object.get('description', '')[:60]}...")
    print()

    # --- Step 2: Client looks up the STM ---
    # In a real client, this would come from:
    #   - Convention-based discovery (server provides STM endpoint)
    #   - A registry lookup
    #   - A local cache from a previous verification
    print("[2] Looking up Sealed Tool Manifest (STM)...")
    with open(stm_file) as f:
        stm_dict = json.load(f)

    subject = stm_dict["payload"]["subject"][0]["name"]
    print(f"    Subject: {subject}")
    print()

    # --- Step 3: Verify (offline or full) ---
    has_bundle = "sigstoreBundle" in stm_dict

    if has_bundle:
        print("[3] Running full verification (Sigstore + canonical form)...")
        try:
            result = verify_tool(
                tool_object=tool_object,
                stm_dict=stm_dict,
                trusted_publishers=trusted_publishers,
                staging=staging,
            )
            print(f"    Status:    VERIFIED")
            print(f"    Publisher: {result.publisher_identity}")
            print(f"    Version:   {result.manifest_version}")
            print(f"    Digest:    sha256:{result.canonical_digest[:16]}...")
        except CTMSVerificationError as e:
            print(f"    Status:    FAILED [{e.failure_type}]")
            print(f"    Reason:    {e}")
            _trust_decision_failed(e.failure_type)
            return
    else:
        print("[3] Running offline verification (canonical form only, no Sigstore)...")
        try:
            verify_canonical_form(tool_object, stm_dict)
            print(f"    Status:    VERIFIED (offline)")
        except CTMSVerificationError as e:
            print(f"    Status:    FAILED [{e.failure_type}]")
            print(f"    Reason:    {e}")
            _trust_decision_failed(e.failure_type)
            return
    print()

    # --- Step 4: Trust decision ---
    print("[4] Trust decision...")
    if has_bundle and trusted_publishers:
        print("    Policy:  Tool is signed and publisher is trusted.")
        print("    Action:  ALLOW tool invocation.")
    elif has_bundle:
        print("    Policy:  Tool is signed but no publisher trust list configured.")
        print("    Action:  ALLOW with warning (signature valid, publisher unchecked).")
    else:
        print("    Policy:  Tool verified offline only (no Sigstore bundle).")
        print("    Action:  ALLOW with reduced confidence.")
    print()

    # --- Step 5: Pass to LLM ---
    print("[5] Tool is safe to expose to the LLM.")
    print(f"    The LLM can now see and invoke '{tool_object.get('name')}'")
    print(f"    with the verified description and input schema.")


def _trust_decision_failed(failure_type: str) -> None:
    """Show what an MCP client should do on verification failure."""
    print()
    print("[4] Trust decision...")
    if failure_type == "manifest_drift":
        print("    Policy:  Tool metadata does not match signed manifest.")
        print("    Action:  BLOCK. Do not expose this tool to the LLM.")
        print("             The tool description may have been tampered with.")
    elif failure_type == "signature_failure":
        print("    Policy:  Cryptographic signature is invalid.")
        print("    Action:  BLOCK. The STM may have been forged.")
    elif failure_type == "publisher_trust_failure":
        print("    Policy:  Publisher is not in the trusted list.")
        print("    Action:  BLOCK or WARN depending on client policy.")
    else:
        print(f"    Policy:  Verification failed ({failure_type}).")
        print("    Action:  BLOCK.")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="MCP client CTMS integration PoC")
    parser.add_argument("tool_file", help="Path to MCP tool object JSON")
    parser.add_argument("stm_file", help="Path to Sealed Tool Manifest JSON")
    parser.add_argument(
        "--trusted-publisher", action="append", default=None,
        help="Trusted publisher identity (can be repeated)",
    )
    parser.add_argument("--staging", action="store_true", help="Use Sigstore staging")
    args = parser.parse_args()

    simulate_mcp_client(
        tool_file=args.tool_file,
        stm_file=args.stm_file,
        trusted_publishers=args.trusted_publisher,
        staging=args.staging,
    )


if __name__ == "__main__":
    main()
