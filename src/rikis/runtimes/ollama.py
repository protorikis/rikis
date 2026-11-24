# Copyright 2026 Protorikis
# SPDX-License-Identifier: Apache-2.0

import httpx
from rikis.runtimes.base import Runtime


class OllamaRuntime(Runtime):
    def list_models(self) -> list[str]:
        resp = httpx.get(f"{self.base_url}/api/tags", headers=self.headers, timeout=10)
        resp.raise_for_status()
        return [m["name"] for m in resp.json().get("models", [])]
