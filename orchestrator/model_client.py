"""Deterministic Ollama client (temperature 0 + fixed seed). The model only ever
emits hypotheses; it never issues findings (docs/WORKFLOW.md L2)."""
from __future__ import annotations
import json, urllib.request, urllib.error


class OllamaClient:
    def __init__(self, endpoint: str, model: str, params: dict | None = None):
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.params = params or {}

    def available(self) -> bool:
        try:
            with urllib.request.urlopen(self.endpoint + "/api/version", timeout=5) as r:
                return r.status == 200
        except Exception:
            return False

    def generate(self, prompt: str, system: str | None = None) -> str:
        body = {
            "model": self.model, "prompt": prompt, "stream": False,
            "options": {
                "temperature": self.params.get("temperature", 0),
                "seed": self.params.get("seed", 0),
                "top_p": self.params.get("top_p", 1.0),
            },
        }
        if system:
            body["system"] = system
        req = urllib.request.Request(
            self.endpoint + "/api/generate",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=600) as r:
            return json.loads(r.read()).get("response", "")
