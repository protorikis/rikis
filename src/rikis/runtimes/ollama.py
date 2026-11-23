# Copyright 2026 Protorikis
# SPDX-License-Identifier: Apache-2.0

import httpx
from rikis.runtimes.base import Runtime, LLMResult


class OllamaRuntime(Runtime):
    def list_models(self) -> list[str]:
        resp = httpx.get(f"{self.base_url}/api/tags", headers=self.headers, timeout=10)
        resp.raise_for_status()
        return [m["name"] for m in resp.json().get("models", [])]

    def run_prompt(self, prompt: str, model: str, *, temperature: float | None = None, thinking: bool = True, preserve_thinking: bool | None = None, history: list | None = None) -> LLMResult:
        return self._openai_stream(prompt, model, temperature=temperature, thinking=thinking, preserve_thinking=preserve_thinking, history=history)
