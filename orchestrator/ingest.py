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


def read_source_files(target_dir: str) -> dict:
    """{relative_path: content} for Solidity sources under src/ and contracts/."""
    out = {}
    for base in ("src", "contracts"):
        for p in glob.glob(os.path.join(target_dir, base, "**", "*.sol"), recursive=True):
            try:
                out[os.path.relpath(p, target_dir)] = open(p).read()
            except Exception:
                continue
    return out


def source_for_contract(files: dict, contract: str) -> str:
    import re as _re
    pat = _re.compile(r"\bcontract\s+" + _re.escape(contract) + r"\b")
    for _p, src in files.items():
        if pat.search(src):
            return src
    return ""
