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

        ran = _pull_and_run_job(portal_url, auth, runtimes)

        if not ran:
            time.sleep(JOB_POLL_INTERVAL)


def _pull_and_run_job(portal_url: str, auth: dict, runtimes: dict[str, Runtime]) -> bool:
    try:
        res = httpx.post(f"{portal_url}/api/jobs/next", headers=auth, timeout=10)
        res.raise_for_status()
    except httpx.RequestError:
        typer.echo("Warning: could not reach portal.", err=True)
        return False

    job = res.json()
    if not job:
        return False

    runtime_url = job.get("runtime_url")
    model = job.get("model")

    if not model:
        typer.echo(f"Job {job['id']}: no model specified, skipping.", err=True)
        return False

    if not runtime_url or runtime_url not in runtimes:
        typer.echo(f"Job {job['id']}: runtime '{runtime_url}' not available, skipping.", err=True)
        return False

    runtime = runtimes[runtime_url]

    typer.echo(f"Running job {job['id']} ({len(job['sub_jobs'])} sub-jobs) [{model}]...")
    params = job.get("llm_params", {})
    multi_turn = params.get("multi_turn", False) or params.get("preserve_thinking", False)
    history: list = []

    for i, sub_job in enumerate(job["sub_jobs"], 1):
        if sub_job.get("status") != "pending":
            continue
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
            if not start_res.is_success:
                typer.echo(f"  Error: {start_res.status_code}", err=True)
            else:
                match start_res.json().get("status"):
                    case "job_cancelled":
                        typer.echo(f"  job {job['id']} cancelled, stopping")
                        break
                    case "skipped":
                        typer.echo(f"  sub-job {sub_job['id']}: skipped")
                        continue
        except httpx.RequestError:
            pass

        prompt = sub_job["prompt"]
        result: dict

        try:
            llm_result = runtime.run_prompt(
                prompt,
                model,
                temperature=params.get("temperature"),
                thinking=params.get("thinking", True),
                preserve_thinking=params.get("preserve_thinking"),
                history=history if multi_turn else None,
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

        if multi_turn:
            reasoning = result.get("reasoning") or ""
            response = result.get("response") or ""
            assistant_content = f"<think>\n{reasoning}\n</think>\n\n{response}" if params.get("preserve_thinking") and reasoning else response
            history.append({"role": "user", "content": prompt})
            history.append({"role": "assistant", "content": assistant_content})

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
        else:
            typer.echo(f"  sub-job {sub_job['id']}: {result['status']}")

    return True


def _push_metrics(portal_url: str, auth: dict) -> None:
    # TODO: collect real system/model metrics
    try:
        httpx.post(f"{portal_url}/api/metrics", json={"placeholder": True}, headers=auth, timeout=10)
    except httpx.RequestError:
        typer.echo("Warning: could not push metrics.", err=True)
