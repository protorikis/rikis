# Copyright 2026 Protorikis
# SPDX-License-Identifier: Apache-2.0

import time
import httpx
import typer
from rikis import config
from rikis.runtimes import Runtime

JOB_POLL_INTERVAL = 15   # seconds

def run(token: str, runtimes: dict[str, Runtime]) -> None:
    server_url = config.load_server_url()
    auth = {"Authorization": f"Bearer {token}"}

    waiting = False
    while True:
        ran = _pull_and_run_job(server_url, auth, runtimes)
        if not ran:
            if not waiting:
                typer.echo("Waiting for jobs...")
                waiting = True
            time.sleep(JOB_POLL_INTERVAL)
        else:
            waiting = False


def _pull_and_run_job(server_url: str, auth: dict, runtimes: dict[str, Runtime]) -> bool:
    try:
        res = httpx.post(f"{server_url}/api/jobs/next", headers=auth, timeout=10)
    except httpx.RequestError as e:
        typer.echo(f"Error: could not reach server: {e}. Retrying in {JOB_POLL_INTERVAL}s...", err=True)
        return False
    if res.status_code == 401:
        typer.echo("Error: authentication failed. Re-run: rikis login --token <token>", err=True)
        raise typer.Exit(1)
    if not res.is_success:
        typer.echo(f"Error: server returned {res.status_code}. Retrying in {JOB_POLL_INTERVAL}s...", err=True)
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

    typer.echo(f"Running job {job['id']} ({len(job['sub_jobs'])} sub-jobs) [{model}]")
    params = job.get("llm_params", {})
    multi_turn = params.get("multi_turn", False) or params.get("preserve_thinking", False)
    history: list = []

    for i, sub_job in enumerate(job["sub_jobs"], 1):
        if sub_job.get("status") != "pending":
            continue
        label = sub_job.get("prompt_label") or sub_job["id"]
        sub_job_id = sub_job.get("sub_job_id")
        id_str = f" ({sub_job_id})" if sub_job_id is not None else ""
        typer.echo(f"  [{i}/{len(job['sub_jobs'])}]{id_str} {label}")

        try:
            start_res = httpx.post(
                f"{server_url}/api/jobs/{job['id']}/sub_jobs/{sub_job['id']}/start",
                headers=auth,
                timeout=10,
            )
            if not start_res.is_success:
                typer.echo(f"  Error: {start_res.status_code}", err=True)
                if start_res.status_code == 404:
                    job_res = httpx.get(f"{server_url}/api/jobs/{job['id']}", headers=auth, timeout=10)
                    if not job_res.is_success:
                        typer.echo(f"  job {job['id']} no longer exists, aborting", err=True)
                        break
                continue
            else:
                match start_res.json().get("status"):
                    case "job_cancelled":
                        typer.echo(f"  job {job['id']} cancelled, stopping")
                        break
                    case "skipped":
                        typer.echo(f"  sub-job {sub_job['id']}: skipped")
                        continue
        except httpx.RequestError as e:
            typer.echo(f"  Error: could not reach server on sub-job start: {e}", err=True)
            continue

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
                "error": None,
                "reasoning": llm_result.reasoning,
                "response": llm_result.response,
                "ttft_seconds": llm_result.ttft_seconds,
                "generation_seconds": llm_result.generation_seconds,
                "tokens_generated": llm_result.tokens_generated,
                "tokens_per_second": llm_result.tokens_per_second,
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
                f"{server_url}/api/jobs/{job['id']}/sub_jobs/{sub_job['id']}/result",
                json=result,
                headers=auth,
                timeout=10,
            )
        except httpx.RequestError as e:
            typer.echo(f"Error: could not submit result for sub-job {sub_job['id']}: {e}", err=True)

        if result["status"] == "ok":
            typer.echo(f"  sub-job {sub_job['id']}: ok | {result['tokens_generated']} tokens | {result['tokens_per_second']:.1f} tok/s | ttft={result['ttft_seconds']:.2f}s")

    return True
