from rikis.runtimes.base import Runtime, LLMResult
from rikis.runtimes.llama_cpp import LlamaCppRuntime
from rikis.runtimes.lmstudio import LMStudioRuntime
from rikis.runtimes.ollama import OllamaRuntime

RUNTIME_TYPES: dict[str, type[Runtime]] = {
    "llama.cpp": LlamaCppRuntime,
    "lmstudio": LMStudioRuntime,
    "ollama": OllamaRuntime,
}


def create_runtime(type: str, url: str) -> Runtime:
    cls = RUNTIME_TYPES.get(type)
    if not cls:
        raise ValueError(f"Unknown runtime type: {type!r}. Available: {', '.join(RUNTIME_TYPES)}")
    return cls(url)
