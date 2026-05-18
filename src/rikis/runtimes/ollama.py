import httpx
from rikis.runtimes.base import Runtime, LLMResult


class OllamaRuntime(Runtime):
    def list_models(self) -> list[str]:
        resp = httpx.get(f"{self.base_url}/api/tags", timeout=10)
        resp.raise_for_status()
        return [m["name"] for m in resp.json().get("models", [])]

    def run_prompt(self, prompt: str, model: str, *, temperature: float | None = None, no_think: bool = False) -> LLMResult:
        return self._openai_stream(prompt, model, temperature=temperature, no_think=no_think)
