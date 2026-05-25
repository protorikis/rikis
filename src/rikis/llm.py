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


class LLMClient:
    def __init__(self, base_url: str, model: str):
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.model = model

    def run_prompt(
        self,
        prompt: str,
        *,
        temperature: float | None = None,
        thinking: bool = True,
    ) -> LLMResult:
        payload: dict = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
        }
        if not thinking:
            payload["chat_template_kwargs"] = {"enable_thinking": False}
            payload["reasoning_effort"] = "none"
        if temperature is not None:
            payload["temperature"] = temperature

        t_start = time.time()
        t_first_token: float | None = None
        token_count = 0
        response_parts: list[str] = []
        reasoning_parts: list[str] = []

        with httpx.stream("POST", self.url, json=payload, timeout=None) as resp:
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
