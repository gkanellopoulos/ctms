"""ctms verify command."""

import json
import sys

import click

from ctms.errors import CTMSVerificationError
from ctms.verify import verify_canonical_form, verify_tool


@click.command()
@click.argument("tool_file", type=click.Path(exists=True))
@click.argument("stm_file", type=click.Path(exists=True))
@click.option("--subject-name", default=None, help="Expected qualified tool name.")
@click.option(
    "--trusted-publisher", multiple=True,
    help="Allowed publisher identity (can be repeated).",
)
@click.option("--staging", is_flag=True, help="Use Sigstore staging infrastructure.")
@click.option("--offline", is_flag=True, help="Steps 4-6 only (no Sigstore verification).")
@click.option(
    "--output-format", type=click.Choice(["text", "json"]), default="text",
    help="Output format.",
)
def verify_cmd(tool_file, stm_file, subject_name, trusted_publisher, staging, offline, output_format):
    """Verify an MCP Tool object against an STM."""
    with open(tool_file, "r") as f:
        tool_object = json.load(f)
    with open(stm_file, "r") as f:
        stm_dict = json.load(f)

    try:
        if offline:
            verify_canonical_form(tool_object, stm_dict)
            click.echo("Verification passed (offline, steps 4-6 only).")
        else:
            publishers = list(trusted_publisher) if trusted_publisher else None
            result = verify_tool(
                tool_object=tool_object,
                stm_dict=stm_dict,
                expected_subject_name=subject_name,
                trusted_publishers=publishers,
                staging=staging,
            )
            if output_format == "json":
                info = {
                    "status": "verified",
                    "toolName": result.tool_name,
                    "subjectName": result.subject_name,
                    "publisherIdentity": result.publisher_identity,
                    "manifestVersion": str(result.manifest_version),
                    "serverVersion": result.server_version,
                    "canonicalDigest": result.canonical_digest,
                }
                click.echo(json.dumps(info, indent=2))
            else:
                click.echo(f"Verification passed.")
                click.echo(f"  Tool:      {result.tool_name}")
                click.echo(f"  Subject:   {result.subject_name}")
                click.echo(f"  Publisher: {result.publisher_identity or 'unknown'}")
                click.echo(f"  Version:   {result.manifest_version}")
    except CTMSVerificationError as e:
        if output_format == "json":
            info = {
                "status": "failed",
                "failureType": e.failure_type,
                "message": str(e),
                "subjectName": e.subject_name,
                "publisherIdentity": e.publisher_identity,
            }
            click.echo(json.dumps(info, indent=2), err=True)
        else:
            click.echo(f"Verification FAILED [{e.failure_type}]: {e}", err=True)
        sys.exit(1)
