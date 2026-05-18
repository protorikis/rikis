import socket
import httpx
import typer
from rikis import config, agent

app = typer.Typer()


@app.command()
def login(token: str = typer.Option(..., help="Token generated from the Bench Portal")):
    """Authenticate this machine with the Bench Portal."""
    portal_url = config.load_portal_url()
    hostname = socket.gethostname()
    try:
        res = httpx.post(
            f"{portal_url}/api/endpoints/register",
            json={"token": token, "hostname": hostname},
        )
        if res.status_code != 200:
            typer.echo("Invalid token. Please generate a new one from the Bench Portal.", err=True)
            raise typer.Exit(1)
    except httpx.RequestError:
        typer.echo(f"Could not reach portal at {portal_url}. Is the backend accessible?", err=True)
        raise typer.Exit(1)

    config.save_token(token)
    typer.echo(f"Logged in successfully as {hostname}.")


@app.command()
def configure(
    llm_url: str = typer.Option(None, help="Local LLM API base URL (OpenAI-compatible)"),
    model: str = typer.Option(None, help="Local LLM model name"),
):
    """Configure the local LLM endpoint."""
    if llm_url is None and model is None:
        typer.echo("Nothing to configure. Pass --llm-url and/or --model.", err=True)
        raise typer.Exit(1)
    config.save_llm(url=llm_url, model=model)
    typer.echo("Configuration saved.")


@app.command()
def start():
    """Start the rikis agent (pulls jobs, pushes metrics)."""
    token = config.load_token()
    if not token:
        typer.echo("Not logged in. Run: rikis login --token <token>", err=True)
        raise typer.Exit(1)
    _, model = config.load_llm()
    if not model:
        typer.echo("LLM not configured. Run: rikis configure --llm-url <url> --model <name>", err=True)
        raise typer.Exit(1)
    agent.run(token)


@app.command()
def status():
    """Show current agent status."""
    token = config.load_token()
    llm_url, model = config.load_llm()
    if not token:
        typer.echo("Not logged in.")
    else:
        typer.echo("Logged in.")
    typer.echo(f"LLM URL: {llm_url}")
    typer.echo(f"LLM model: {model or '(not set)'}")
