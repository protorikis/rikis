import typer
from rikis import commands

app = typer.Typer()
app.add_typer(commands.app)


def main() -> None:
    app()
