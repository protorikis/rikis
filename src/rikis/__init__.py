# Copyright 2026 Protorikis
# SPDX-License-Identifier: Apache-2.0

from importlib.metadata import version
import typer
from rikis import commands

app = typer.Typer()
app.add_typer(commands.app)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(version("rikis"))
        raise typer.Exit()


@app.callback()
def callback(
    _: bool = typer.Option(None, "--version", callback=_version_callback, is_eager=True, help="Show version and exit."),
) -> None:
    pass


def main() -> None:
    app()
