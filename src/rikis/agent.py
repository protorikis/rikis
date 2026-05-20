import time
import httpx
import typer
from rikis import config
from rikis.runtimes import Runtime

JOB_POLL_INTERVAL = 15   # seconds
METRICS_PUSH_INTERVAL = 30  # seconds


def run(token: str, runtimes: dict[str, Runtime]) -> None:
    portal_url = config.load_portal_url()
    auth = {"Authorization": f"Bearer {token}"}

    typer.echo(f"Agent started with {len(runtimes)} runtime(s).")

    last_metrics = 0.0
    while True:
        now = time.time()

        if now - last_metrics >= METRICS_PUSH_INTERVAL:
            _push_metrics(portal_url, auth)
            last_metrics = now

        _pull_and_run_job(portal_url, auth, runtimes)

        time.sleep(JOB_POLL_INTERVAL)


def _pull_and_run_job(portal_url: str, auth: dict, runtimes: dict[str, Runtime]) -> None:
    try:
        res = httpx.get(f"{portal_url}/api/jobs", headers=auth, timeout=10)
        res.raise_for_status()
    except httpx.RequestError:
        typer.echo("Warning: could not reach portal.", err=True)
        return

    job = res.json()
    if not job:
        return

    runtime_url = job.get("runtime_url")
    model = job.get("model")

    if not model:
        typer.echo(f"Job {job['id']}: no model specified, skipping.", err=True)
        return

    if not runtime_url or runtime_url not in runtimes:
        typer.echo(f"Job {job['id']}: runtime '{runtime_url}' not available, skipping.", err=True)
        return

    runtime = runtimes[runtime_url]

    typer.echo(f"Running job {job['id']} ({len(job['sub_jobs'])} sub-jobs) [{model}]...")
    params = job.get("llm_params", {})

    for i, sub_job in enumerate(job["sub_jobs"], 1):
        label = sub_job.get("prompt_label") or sub_job["id"]
        sub_job_id = sub_job.get("sub_job_id")
        id_str = f" ({sub_job_id})" if sub_job_id is not None else ""
        typer.echo(f"  [{i}/{len(job['sub_jobs'])}]{id_str} {label}...")

        try:
            start_res = httpx.post(
                f"{portal_url}/api/jobs/{job['id']}/sub_jobs/{sub_job['id']}/start",
                headers=auth,
                timeout=10,
            )
            if start_res.json().get("cancelled"):
                typer.echo(f"  job {job['id']} cancelled, stopping.")
                break
        except httpx.RequestError:
            pass

        prompt = sub_job["prompt"]
        result: dict

        try:
            llm_result = runtime.run_prompt(
                prompt,
                model,
                temperature=params.get("temperature"),
                no_think=params.get("no_think", False),
            )
            result = {
                "status": "ok",
                "response": llm_result.response,
                "reasoning": llm_result.reasoning,
                "ttft_seconds": llm_result.ttft_seconds,
                "generation_seconds": llm_result.generation_seconds,
                "tokens_generated": llm_result.tokens_generated,
                "tokens_per_second": llm_result.tokens_per_second,
                "error": None,
            }
        except Exception as e:
            typer.echo(f"  sub-job {sub_job['id']} error: {e}", err=True)
            result = {"status": "error", "error": str(e)}

        try:
            httpx.post(
                f"{portal_url}/api/jobs/{job['id']}/sub_jobs/{sub_job['id']}/result",
                json=result,
                headers=auth,
                timeout=10,
            )
        except httpx.RequestError as e:
            typer.echo(f"Warning: could not submit result for sub-job {sub_job['id']}: {e}", err=True)

        if result["status"] == "ok":
            typer.echo(f"  sub-job {sub_job['id']}: ok | {result['tokens_generated']} tokens | {result['tokens_per_second']:.1f} tok/s | ttft={result['ttft_seconds']:.2f}s")
            typer.echo(f"    response: {result['response'][:200]}")
        else:
            typer.echo(f"  sub-job {sub_job['id']}: {result['status']}")


def _push_metrics(portal_url: str, auth: dict) -> None:
    # TODO: collect real system/model metrics
    try:
        httpx.post(f"{portal_url}/api/metrics", json={"placeholder": True}, headers=auth, timeout=10)
    except httpx.RequestError:
        typer.echo("Warning: could not push metrics.", err=True)
