# Copyright 2026 Protorikis
# SPDX-License-Identifier: Apache-2.0

import json
import os
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("RIKIS_CONFIG_DIR", Path.home() / ".rikis"))
CONFIG_PATH = CONFIG_DIR / "config.json"

DEFAULT_SERVER_URL = "https://bench.protorikis.com"


def save_token(token: str) -> None:
    _save({"token": token})


def load_token() -> str | None:
    return _load_raw().get("token")


def load_server_url() -> str:
    return _load_raw().get("server_url", DEFAULT_SERVER_URL)


def add_runtime(type: str, url: str) -> None:
    data = _load_raw()
    runtimes = [r for r in data.get("runtimes", []) if r["url"] != url]
    runtimes.append({"type": type, "url": url})
    _save({"runtimes": runtimes})


def remove_runtime(url: str) -> bool:
    data = _load_raw()
    runtimes = data.get("runtimes", [])
    filtered = [r for r in runtimes if r["url"] != url]
    if len(filtered) == len(runtimes):
        return False
    _save({"runtimes": filtered})
    return True


def load_runtimes() -> list[dict]:
    return _load_raw().get("runtimes", [])


def _save(updates: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = _load_raw()
    data.update(updates)
    CONFIG_PATH.write_text(json.dumps(data, indent=2))


def _load_raw() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    return json.loads(CONFIG_PATH.read_text())
