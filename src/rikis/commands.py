import socket
import httpx
import typer
from rikis import config, agent
from rikis.runtimes import create_runtime, RUNTIME_TYPES

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
    add_runtime: str = typer.Option(None, "--add-runtime", help=f"Add a runtime. Type: {', '.join(RUNTIME_TYPES)}"),
    url: str = typer.Option(None, "--url", help="Runtime base URL (e.g. http://localhost:11434)"),
):
    """Configure rikis."""
    if add_runtime is not None:
        if not url:
            typer.echo("--url is required with --add-runtime.", err=True)
            raise typer.Exit(1)
        if add_runtime not in RUNTIME_TYPES:
            typer.echo(f"Unknown runtime type '{add_runtime}'. Available: {', '.join(RUNTIME_TYPES)}", err=True)
            raise typer.Exit(1)
        config.add_runtime(add_runtime, url)
        typer.echo(f"Runtime added: {add_runtime} @ {url}")
        return
    typer.echo("Nothing to configure. Use --add-runtime.", err=True)
    raise typer.Exit(1)


@app.command()
def start():
    """Start the rikis agent (pulls jobs from portal and runs them)."""
    token = config.load_token()
    if not token:
        typer.echo("Not logged in. Run: rikis login --token <token>", err=True)
        raise typer.Exit(1)

    runtime_configs = config.load_runtimes()
    if not runtime_configs:
        typer.echo("No runtimes configured. Run: rikis configure --add-runtime <type> --url <url>", err=True)
        raise typer.Exit(1)

    runtimes: dict = {}
    profiles = []
    for rc in runtime_configs:
        try:
            rt = create_runtime(rc["type"], rc["url"])
            models = rt.list_models()
            runtimes[rc["url"]] = rt
            profiles.append({"type": rc["type"], "url": rc["url"], "models": models})
            typer.echo(f"  {rc['type']} @ {rc['url']}: {len(models)} model(s)")
        except Exception as e:
            typer.echo(f"Warning: could not connect to {rc['type']} @ {rc['url']}: {e}", err=True)

    if not runtimes:
        typer.echo("No runtimes reachable. Check your configuration.", err=True)
        raise typer.Exit(1)

    auth = {"Authorization": f"Bearer {token}"}
    portal_url = config.load_portal_url()
    try:
        httpx.post(f"{portal_url}/api/endpoints/runtimes", json={"runtimes": profiles}, headers=auth, timeout=10)
    except httpx.RequestError:
        typer.echo("Warning: could not push runtime profiles to portal.", err=True)

    agent.run(token, runtimes)


@app.command()
def status():
    """Show current agent configuration."""
    token = config.load_token()
    runtimes = config.load_runtimes()
    typer.echo("Logged in." if token else "Not logged in.")
    if runtimes:
        typer.echo(f"{len(runtimes)} runtime(s) configured:")
        for r in runtimes:
            typer.echo(f"  {r['type']} @ {r['url']}")
    else:
        typer.echo("No runtimes configured.")
