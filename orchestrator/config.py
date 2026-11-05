"""Config loading for model.yaml and the pinned versions.env."""
from __future__ import annotations
import os, yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_model_config(path: str | None = None) -> dict:
    path = path or os.path.join(ROOT, "config", "model.yaml")
    with open(path) as f:
        return yaml.safe_load(f)


def load_versions(path: str | None = None) -> dict:
    path = path or os.path.join(ROOT, "config", "versions.env")
    env = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.split(" #")[0].strip()
    return env
