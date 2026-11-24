# Copyright 2026 Protorikis
# SPDX-License-Identifier: Apache-2.0

import json
import time
from dataclasses import dataclass

import httpx


@dataclass
class LLMResult:
    response: str
    reasoning: str
    ttft_seconds: float
    generation_seconds: float
    tokens_generated: int
    tokens_per_second: float


class Runtime:
    """A runtime that speaks the OpenAI-compatible API. Subclasses override only what differs."""

    def __init__(self, base_url: str, api_key: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}

    def list_models(self) -> list[str]:
        resp = httpx.get(f"{self.base_url}/v1/models", headers=self.headers, timeout=10)
        resp.raise_for_status()
        return [m["id"] for m in resp.json().get("data", [])]

    def run_prompt(self, prompt: str, model: str, *, temperature: float | None = None, thinking: bool = True, preserve_thinking: bool | None = None, history: list | None = None) -> LLMResult:
        return self._openai_stream(prompt, model, temperature=temperature, thinking=thinking, preserve_thinking=preserve_thinking, history=history)

    def _openai_stream(self, prompt: str, model: str, *, temperature: float | None = None, thinking: bool = True, preserve_thinking: bool | None = None, history: list | None = None, extra_messages: list | None = None) -> LLMResult:
        messages = (history or []) + [{"role": "user", "content": prompt}]
        if extra_messages:
            messages += extra_messages
        payload: dict = {
            "model": model,
            "messages": messages,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        chat_template_kwargs: dict = {}
        if not thinking:
            chat_template_kwargs["enable_thinking"] = False
            payload["reasoning_effort"] = "none"
        if preserve_thinking:
            chat_template_kwargs["preserve_thinking"] = True
        if chat_template_kwargs:
            payload["chat_template_kwargs"] = chat_template_kwargs
        if temperature is not None:
            payload["temperature"] = temperature

        t_start = time.time()
        t_first_token: float | None = None
        token_count = 0  # streamed chunks with text; fallback when the server reports no usage
        reported_tokens: int | None = None
        response_parts: list[str] = []
        reasoning_parts: list[str] = []

        with httpx.stream("POST", f"{self.base_url}/v1/chat/completions", json=payload, headers=self.headers, timeout=None) as resp:
            resp.raise_for_status()
            for raw_line in resp.iter_lines():
                line = raw_line.strip()
                if not line.startswith("data: "):
                    continue
                data = line[len("data: "):]
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue
                usage = chunk.get("usage")
                if usage and usage.get("completion_tokens") is not None:
                    reported_tokens = usage["completion_tokens"]
                delta = (chunk.get("choices") or [{}])[0].get("delta", {})
                reasoning = delta.get("reasoning_content") or delta.get("reasoning") or ""
                content = delta.get("content") or ""
                if reasoning:
                    if t_first_token is None:
                        t_first_token = time.time()
                    token_count += 1
                    reasoning_parts.append(reasoning)
                if content:
                    if t_first_token is None:
                        t_first_token = time.time()
                    token_count += 1
                    response_parts.append(content)

        t_end = time.time()
        ttft = (t_first_token - t_start) if t_first_token else 0.0
        gen_time = (t_end - t_first_token) if t_first_token else 0.0
        tokens = reported_tokens if reported_tokens is not None else token_count
        tps = (tokens / gen_time) if gen_time > 0 else 0.0

        return LLMResult(
            response="".join(response_parts),
            reasoning="".join(reasoning_parts),
            ttft_seconds=ttft,
            generation_seconds=gen_time,
            tokens_generated=tokens,
            tokens_per_second=tps,
        )
