"""CTMS CLI entry point."""

import click

from ctms.cli.canonicalize_cmd import canonicalize_cmd
from ctms.cli.inspect_cmd import inspect_cmd
from ctms.cli.sign_cmd import sign_cmd
from ctms.cli.verify_cmd import verify_cmd


@click.group()
@click.version_option(package_name="ctms")
def cli():
    """CTMS: signing and verification for MCP tool metadata."""


cli.add_command(canonicalize_cmd, "canonicalize")
cli.add_command(inspect_cmd, "inspect")
cli.add_command(sign_cmd, "sign")
cli.add_command(verify_cmd, "verify")
