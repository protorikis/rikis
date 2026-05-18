import httpx
from rikis.runtimes.base import Runtime, LLMResult


class LMStudioRuntime(Runtime):
    def list_models(self) -> list[str]:
        resp = httpx.get(f"{self.base_url}/v1/models", timeout=10)
        resp.raise_for_status()
        return [m["id"] for m in resp.json().get("data", [])]

    def run_prompt(self, prompt: str, model: str, *, temperature: float | None = None, no_think: bool = False) -> LLMResult:
        return self._openai_stream(prompt, model, temperature=temperature, no_think=no_think)
