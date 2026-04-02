"""ctms sign command."""

import json
import sys

import click

from ctms._types import ManifestVersion


@click.command()
@click.argument("tool_file", type=click.Path(exists=True))
@click.option("--subject-name", required=True, help="Qualified tool identifier.")
@click.option("--server-version", required=True, help="MCP server version string.")
@click.option("--version-major", type=int, default=1, help="Manifest major version.")
@click.option("--version-minor", type=int, default=0, help="Manifest minor version.")
@click.option("--output", "-o", type=click.Path(), default=None, help="Output STM file.")
@click.option("--staging", is_flag=True, help="Use Sigstore staging infrastructure.")
def sign_cmd(tool_file, subject_name, server_version, version_major, version_minor, output, staging):
    """Sign an MCP Tool object and produce an STM."""
    with open(tool_file, "r") as f:
        tool_object = json.load(f)

    manifest_version = ManifestVersion(major=version_major, minor=version_minor)

    try:
        from ctms.sign import sign_tool
        stm_dict = sign_tool(
            tool_object=tool_object,
            subject_name=subject_name,
            manifest_version=manifest_version,
            server_version=server_version,
            staging=staging,
        )
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    stm_json = json.dumps(stm_dict, indent=2)

    if output:
        with open(output, "w") as f:
            f.write(stm_json)
            f.write("\n")
        click.echo(f"STM written to {output}", err=True)
    else:
        click.echo(stm_json)
