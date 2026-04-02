"""ctms inspect command."""

import json
import sys

import click

from ctms.stm import parse_stm


@click.command()
@click.argument("stm_file", type=click.Path(exists=True))
@click.option(
    "--output-format", type=click.Choice(["text", "json"]), default="text",
    help="Output format.",
)
def inspect_cmd(stm_file, output_format):
    """Display the contents of an STM file."""
    with open(stm_file, "r") as f:
        stm_dict = json.load(f)

    try:
        stm = parse_stm(stm_dict)
    except (ValueError, KeyError) as e:
        click.echo(f"Error parsing STM: {e}", err=True)
        sys.exit(1)

    if output_format == "json":
        info = {
            "subjectName": stm.subject.name,
            "subjectDigest": stm.subject.digest_sha256,
            "ctmsVersion": stm.predicate.ctms_version,
            "manifestVersion": str(stm.predicate.manifest_version),
            "serverVersion": stm.predicate.server_version,
            "signingTimestamp": stm.predicate.signing_timestamp,
        }
        click.echo(json.dumps(info, indent=2))
    else:
        click.echo(f"Subject:           {stm.subject.name}")
        click.echo(f"Subject digest:    sha256:{stm.subject.digest_sha256}")
        click.echo(f"CTMS version:      {stm.predicate.ctms_version}")
        click.echo(f"Manifest version:  {stm.predicate.manifest_version}")
        click.echo(f"Server version:    {stm.predicate.server_version}")
        click.echo(f"Signing timestamp: {stm.predicate.signing_timestamp}")
