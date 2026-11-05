"""Ingestion: detect build system and read Solidity sources for the LLM.
(Local targets now; on-chain source-fetch + fork is the next addition.)"""
from __future__ import annotations
import os, glob


def detect_build(target_dir: str) -> str:
    if os.path.exists(os.path.join(target_dir, "foundry.toml")):
        return "foundry"
    for c in ("hardhat.config.js", "hardhat.config.ts"):
        if os.path.exists(os.path.join(target_dir, c)):
            return "hardhat"
    return "unknown"


def read_sources(target_dir: str, max_chars: int = 40000) -> str:
    files = []
    for base in ("src", "contracts"):
        d = os.path.join(target_dir, base)
        files += glob.glob(os.path.join(d, "**", "*.sol"), recursive=True)
    parts, total = [], 0
    for p in sorted(set(files)):
        try:
            txt = open(p).read()
        except Exception:
            continue
        chunk = f"// FILE: {os.path.relpath(p, target_dir)}\n{txt}\n"
        if total + len(chunk) > max_chars:
            break
        parts.append(chunk)
        total += len(chunk)
    return "".join(parts)
