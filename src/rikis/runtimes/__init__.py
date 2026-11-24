# Copyright 2026 Protorikis
# SPDX-License-Identifier: Apache-2.0

from rikis.runtimes.base import Runtime, LLMResult
from rikis.runtimes.llama_cpp import LlamaCppRuntime
from rikis.runtimes.lmstudio import LMStudioRuntime
from rikis.runtimes.ollama import OllamaRuntime
from rikis.runtimes.omlx import OMLXRuntime

RUNTIME_TYPES: dict[str, type[Runtime]] = {
    "llama.cpp": LlamaCppRuntime,
    "lmstudio": LMStudioRuntime,
    "ollama": OllamaRuntime,
    "omlx": OMLXRuntime,
}


def create_runtime(type: str, url: str, api_key: str | None = None) -> Runtime:
    cls = RUNTIME_TYPES.get(type)
    if not cls:
        raise ValueError(f"Unknown runtime type: {type!r}. Available: {', '.join(RUNTIME_TYPES)}")
    return cls(url, api_key=api_key)
