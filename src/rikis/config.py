import json
from pathlib import Path

CONFIG_PATH = Path.home() / ".rikis" / "config.json"

DEFAULT_PORTAL_URL = "http://localhost:8000"


def save_token(token: str) -> None:
    _save({"token": token})


def load_token() -> str | None:
    return _load_raw().get("token")


def load_portal_url() -> str:
    return _load_raw().get("portal_url", DEFAULT_PORTAL_URL)


def add_runtime(type: str, url: str) -> None:
    data = _load_raw()
    runtimes = [r for r in data.get("runtimes", []) if r["url"] != url]
    runtimes.append({"type": type, "url": url})
    _save({"runtimes": runtimes})


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
