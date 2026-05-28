import socket
import httpx
import typer
from rikis import config as cfg, agent
from rikis.runtimes import create_runtime, RUNTIME_TYPES

app = typer.Typer()


@app.command()
def login(
    token: str = typer.Option(..., help="Token generated from the Bench Portal"),
    name: str = typer.Option(None, "--name", help="Display name for this endpoint"),
):
    """Authenticate this machine with the Bench Portal."""
    server_url = cfg.load_server_url()
    hostname = socket.gethostname()
    payload: dict = {"token": token, "hostname": hostname}
    if name:
        payload["name"] = name
    try:
        res = httpx.post(
            f"{server_url}/api/endpoints/register",
            json=payload,
            timeout=60,
        )
        if res.status_code != 200:
            typer.echo("Invalid token. Please generate a new one from the Bench Portal.", err=True)
            raise typer.Exit(1)
    except httpx.RequestError:
        typer.echo(f"Could not reach server at {server_url}. Is the backend accessible?", err=True)
        raise typer.Exit(1)

    cfg.save_token(token)
    typer.echo(f"Logged in successfully as {hostname}.")


@app.command()
def config(
    add_runtime: str = typer.Option(None, "--add-runtime", help=f"Add a runtime. Type: {', '.join(RUNTIME_TYPES)}"),
    remove_runtime: str = typer.Option(None, "--remove-runtime", help="Remove a runtime by URL"),
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
        cfg.add_runtime(add_runtime, url)
        typer.echo(f"Runtime added: {add_runtime} @ {url}")
        return
    if remove_runtime is not None:
        if not cfg.remove_runtime(remove_runtime):
            typer.echo(f"No runtime found with URL '{remove_runtime}'.", err=True)
            raise typer.Exit(1)
        typer.echo(f"Runtime removed: {remove_runtime}")
        return
    typer.echo("Nothing to configure. Use --add-runtime or --remove-runtime.", err=True)
    raise typer.Exit(1)


@app.command()
def start():
    """Start the rikis agent (pulls jobs from server and runs them)."""
    token = cfg.load_token()
    if not token:
        typer.echo("Not logged in. Run: rikis login --token <token>", err=True)
        raise typer.Exit(1)

    runtime_configs = cfg.load_runtimes()
    if not runtime_configs:
        typer.echo("No runtimes configured. Run: rikis config --add-runtime <type> --url <url>", err=True)
        raise typer.Exit(1)

    runtimes: dict = {rc["url"]: create_runtime(rc["type"], rc["url"]) for rc in runtime_configs}

    profiles = []
    typer.echo("Checking runtimes...")
    for rc in runtime_configs:
        try:
            models = runtimes[rc["url"]].list_models()
            profiles.append({"type": rc["type"], "url": rc["url"], "models": models})
            typer.echo(f"  {rc['type']} @ {rc['url']}: {len(models)} model(s)")
        except Exception as e:
            profiles.append({"type": rc["type"], "url": rc["url"], "models": []})
            typer.echo(f"  {rc['type']} @ {rc['url']}: unreachable ({e})")

    auth = {"Authorization": f"Bearer {token}"}
    server_url = cfg.load_server_url()
    try:
        httpx.post(f"{server_url}/api/endpoints/runtimes", json={"runtimes": profiles}, headers=auth, timeout=10)
    except httpx.RequestError:
        typer.echo("Warning: could not push runtime profiles to server.", err=True)

    agent.run(token, runtimes)


@app.command()
def status():
    """Show current agent configuration."""
    token = cfg.load_token()
    runtimes = cfg.load_runtimes()
    typer.echo("Logged in." if token else "Not logged in.")
    if runtimes:
        typer.echo(f"{len(runtimes)} runtime(s) configured:")
        for r in runtimes:
            typer.echo(f"  {r['type']} @ {r['url']}")
    else:
        typer.echo("No runtimes configured.")
