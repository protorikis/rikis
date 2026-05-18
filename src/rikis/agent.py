import time
import httpx
import typer
from rikis import config
from rikis.llm import LLMClient

JOB_POLL_INTERVAL = 15   # seconds
METRICS_PUSH_INTERVAL = 30  # seconds


def run(token: str) -> None:
    llm_url, model = config.load_llm()
    if not model:
        typer.echo("LLM model not configured.", err=True)
        return

    client = LLMClient(base_url=llm_url, model=model)
    portal_url = config.load_portal_url()
    auth = {"Authorization": f"Bearer {token}"}

    typer.echo(f"Agent started. LLM: {model} @ {llm_url}")

    last_metrics = 0.0
    while True:
        now = time.time()

        if now - last_metrics >= METRICS_PUSH_INTERVAL:
            _push_metrics(portal_url, auth)
            last_metrics = now

        _pull_and_run_job(portal_url, auth, client)

        time.sleep(JOB_POLL_INTERVAL)


def _pull_and_run_job(portal_url: str, auth: dict, client: LLMClient) -> None:
    try:
        res = httpx.get(f"{portal_url}/api/jobs", headers=auth, timeout=10)
        res.raise_for_status()
    except httpx.RequestError:
        typer.echo("Warning: could not reach portal.", err=True)
        return

    job = res.json()
    if not job:
        return

    typer.echo(f"Running job {job['id']} ({len(job['sub_jobs'])} sub-jobs)...")
    params = job.get("llm_params", {})

    for i, sub_job in enumerate(job["sub_jobs"], 1):
        label = sub_job.get("prompt_label") or sub_job["id"]
        sub_job_id = sub_job.get("sub_job_id")
        id_str = f" ({sub_job_id})" if sub_job_id is not None else ""
        typer.echo(f"  [{i}/{len(job['sub_jobs'])}]{id_str} {label}...")
        prompt = sub_job["prompt"]
        result: dict

        try:
            llm_result = client.run_prompt(
                prompt,
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
            typer.echo(f"  sub-job {sub_job['id']}: {result['status']} | {result['tokens_generated']} tokens | {result['tokens_per_second']:.1f} tok/s | ttft={result['ttft_seconds']:.2f}s")
            typer.echo(f"    response: {result['response'][:200]}")
        else:
            typer.echo(f"  sub-job {sub_job['id']}: {result['status']}")


def _push_metrics(portal_url: str, auth: dict) -> None:
    # TODO: collect real system/model metrics
    try:
        httpx.post(f"{portal_url}/api/metrics", json={"placeholder": True}, headers=auth, timeout=10)
    except httpx.RequestError:
        typer.echo("Warning: could not push metrics.", err=True)
