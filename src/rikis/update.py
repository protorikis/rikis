# Copyright 2026 Protorikis
# SPDX-License-Identifier: Apache-2.0

import json
import time
from datetime import datetime
from importlib.metadata import version
from pathlib import Path

import httpx
import typer

_CACHE_PATH = Path.home() / ".rikis" / "update_cache.json"
_CHECK_INTERVAL = 86400  # 24 hours


def check_for_update() -> None:
    try:
        cache = json.loads(_CACHE_PATH.read_text()) if _CACHE_PATH.exists() else {}
        checked_at = cache.get("checked_at")
        age = time.time() - datetime.fromisoformat(checked_at).timestamp() if checked_at else _CHECK_INTERVAL + 1
        if age < _CHECK_INTERVAL:
            latest = cache.get("latest_version")
        else:
            res = httpx.get("https://pypi.org/pypi/rikis/json", timeout=5)
            latest = res.json()["info"]["version"]
            _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            now = datetime.now().astimezone().isoformat(timespec="seconds")
            _CACHE_PATH.write_text(json.dumps({"checked_at": now, "latest_version": latest}))

        current = version("rikis")
        if latest and latest != current:
            typer.echo(f"A new version of rikis is available: {current} → {latest}. Run: pipx upgrade rikis", err=True)
    except Exception:
        pass
