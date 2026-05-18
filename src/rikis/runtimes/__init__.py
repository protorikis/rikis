from rikis.runtimes.base import Runtime, LLMResult
from rikis.runtimes.ollama import OllamaRuntime
from rikis.runtimes.llama_cpp import LlamaCppRuntime
from rikis.runtimes.lmstudio import LMStudioRuntime

RUNTIME_TYPES: dict[str, type[Runtime]] = {
    "ollama": OllamaRuntime,
    "llama.cpp": LlamaCppRuntime,
    "lmstudio": LMStudioRuntime,
}


def create_runtime(type: str, url: str) -> Runtime:
    cls = RUNTIME_TYPES.get(type)
    if not cls:
        raise ValueError(f"Unknown runtime type: {type!r}. Available: {', '.join(RUNTIME_TYPES)}")
    return cls(url)
