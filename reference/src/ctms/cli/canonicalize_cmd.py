"""ctms canonicalize command."""

import json
import sys

import click

from ctms.canonicalize import canonicalize, canonical_digest


@click.command()
@click.argument("tool_file", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), default=None, help="Output file path.")
@click.option("--digest", is_flag=True, help="Also print SHA-256 digest.")
def canonicalize_cmd(tool_file, output, digest):
    """Produce the canonical form of an MCP Tool object."""
    with open(tool_file, "r") as f:
        tool_object = json.load(f)

    try:
        canonical_form = canonicalize(tool_object)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    if output:
        with open(output, "wb") as f:
            f.write(canonical_form)
    else:
        sys.stdout.buffer.write(canonical_form)
        sys.stdout.buffer.write(b"\n")

    if digest:
        click.echo(f"sha256:{canonical_digest(canonical_form)}", err=True)
