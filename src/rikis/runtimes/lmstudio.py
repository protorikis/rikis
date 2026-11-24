# Copyright 2026 Protorikis
# SPDX-License-Identifier: Apache-2.0

from rikis.runtimes.base import Runtime, LLMResult


class LMStudioRuntime(Runtime):
    def run_prompt(self, prompt: str, model: str, *, temperature: float | None = None, thinking: bool = True, preserve_thinking: bool | None = None, history: list | None = None) -> LLMResult:
        extra_messages = [{"role": "assistant", "content": "<think>\n</think>"}] if not thinking else None
        return self._openai_stream(prompt, model, temperature=temperature, thinking=thinking, preserve_thinking=preserve_thinking, history=history, extra_messages=extra_messages)
