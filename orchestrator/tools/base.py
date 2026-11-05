"""Sandboxed tool runner with container hardening (the lab analyzes UNTRUSTED contract
code). Resource limits + no-new-privileges prevent a hostile contract from DoSing the box
through a tool. Also provides tool-version provenance for reproducibility."""
from __future__ import annotations
import json, os, subprocess

IMAGE = os.environ.get("SECLAB_IMAGE", "seclab-web3/analysis:latest")
SCRATCH = os.environ.get("SECLAB_SCRATCH", "/opt/dlami/nvme/seclab")

# hardening applied to every analysis container
DOCKER_SAFE = ["--security-opt", "no-new-privileges",
               "--memory", os.environ.get("SECLAB_MEM", "6g"),
               "--memory-swap", os.environ.get("SECLAB_MEM", "6g"),
               "--pids-limit", "2048"]


def run_tool(target_dir: str, cmd: str, timeout: int = 900, image: str = IMAGE,
             network: bool = True):
    """Run cmd in the hardened analysis container over target_dir. Returns (rc, out, err)."""
    cache = f"{SCRATCH}/toolcache"
    os.makedirs(cache, exist_ok=True)
    base = ["docker", "run", "--rm", *DOCKER_SAFE, "-e", "HOME=/cache",
            "-v", f"{cache}:/cache", "-v", f"{target_dir}:/work", "-w", "/work"]
    if not network:
        base += ["--network", "none"]
    dcmd = base + [image, "bash", "-c", cmd]
    try:
        p = subprocess.run(dcmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s"
    except Exception as e:
        return 1, "", f"docker error: {e}"


def tool_versions(image: str = IMAGE, cache_path: str = None) -> dict:
    """Record exact tool versions once (cached) for per-run provenance."""
    cache_path = cache_path or os.path.join(SCRATCH, "tool_versions.json")
    if os.path.exists(cache_path):
        try:
            return json.load(open(cache_path))
        except Exception:
            pass
    cmds = {"forge": "forge --version", "slither": "slither --version",
            "semgrep": "semgrep --version", "aderyn": "aderyn --version",
            "halmos": "halmos --version", "echidna": "echidna --version",
            "medusa": "medusa --version", "solc": "solc --version"}
    out = {}
    for name, c in cmds.items():
        try:
            r = subprocess.run(["docker", "run", "--rm", image, "bash", "-c", c],
                               capture_output=True, text=True, timeout=60)
            text = (r.stdout or r.stderr).strip()
            out[name] = text.splitlines()[0] if text else "?"
        except Exception:
            out[name] = "?"
    try:
        myth = subprocess.run(["docker", "run", "--rm",
                               os.environ.get("SECLAB_MYTHRIL_IMAGE", "seclab-web3/mythril:latest"),
                               "version"], capture_output=True, text=True, timeout=60)
        out["mythril"] = (myth.stdout or myth.stderr).strip().splitlines()[0] if (myth.stdout or myth.stderr) else "?"
    except Exception:
        out["mythril"] = "?"
    try:
        json.dump(out, open(cache_path, "w"))
    except Exception:
        pass
    return out


class Verifier:
    kind = "base"
    def verify(self, hypothesis, target):
        raise NotImplementedError  # pragma: no cover (abstract interface)
