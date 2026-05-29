# Copyright 2026 Protorikis
# SPDX-License-Identifier: Apache-2.0

import typer
from rikis import commands

app = typer.Typer()
app.add_typer(commands.app)


def main() -> None:
    app()
