import json
import time
from abc import ABC, abstractmethod
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


class Runtime(ABC):
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    @abstractmethod
    def list_models(self) -> list[str]: ...

    @abstractmethod
    def run_prompt(self, prompt: str, model: str, *, temperature: float | None = None, thinking: bool = True, preserve_thinking: bool | None = None, history: list | None = None) -> LLMResult: ...

    def _openai_stream(self, prompt: str, model: str, *, temperature: float | None = None, thinking: bool = True, preserve_thinking: bool | None = None, history: list | None = None, extra_messages: list | None = None) -> LLMResult:
        messages = (history or []) + [{"role": "user", "content": prompt}]
        if extra_messages:
            messages += extra_messages
        payload: dict = {
            "model": model,
            "messages": messages,
            "stream": True,
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
        token_count = 0
        response_parts: list[str] = []
        reasoning_parts: list[str] = []

        with httpx.stream("POST", f"{self.base_url}/v1/chat/completions", json=payload, timeout=None) as resp:
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
                delta = chunk.get("choices", [{}])[0].get("delta", {})
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
        tps = (token_count / gen_time) if gen_time > 0 else 0.0

        return LLMResult(
            response="".join(response_parts),
            reasoning="".join(reasoning_parts),
            ttft_seconds=ttft,
            generation_seconds=gen_time,
            tokens_generated=token_count,
            tokens_per_second=tps,
        )
