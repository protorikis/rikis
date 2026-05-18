import json
from pathlib import Path

CONFIG_PATH = Path.home() / ".rikis" / "config.json"

# TODO: make configurable via `rikis configure --portal <url>`
DEFAULT_PORTAL_URL = "http://localhost:8000"
DEFAULT_LLM_URL = "http://localhost:1234"


def save_token(token: str) -> None:
    _save({"token": token})


def load_token() -> str | None:
    return _load_raw().get("token")


def load_portal_url() -> str:
    return _load_raw().get("portal_url", DEFAULT_PORTAL_URL)


def save_llm(url: str | None = None, model: str | None = None) -> None:
    data: dict = {}
    if url is not None:
        data["llm_url"] = url
    if model is not None:
        data["llm_model"] = model
    _save(data)


def load_llm() -> tuple[str, str | None]:
    raw = _load_raw()
    return raw.get("llm_url", DEFAULT_LLM_URL), raw.get("llm_model")


def _save(updates: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = _load_raw()
    data.update(updates)
    CONFIG_PATH.write_text(json.dumps(data))


def _load_raw() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    return json.loads(CONFIG_PATH.read_text())
