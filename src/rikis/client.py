# Copyright 2026 Protorikis
# SPDX-License-Identifier: Apache-2.0

from importlib.metadata import version
import httpx

USER_AGENT = f"rikis/{version('rikis')}"


def create_client(token: str | None = None) -> httpx.Client:
    headers: dict = {"User-Agent": USER_AGENT}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return httpx.Client(headers=headers)


def get_detail(res: httpx.Response) -> str:
    if res.headers.get("content-type", "").startswith("application/json"):
        return res.json().get("detail", res.text)
    return str(res.status_code)
