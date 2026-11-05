"""Sandboxed tool runner. Tools run as root INSIDE the analysis container (the
sandbox), with HOME on scratch so solc/svm caches persist. Host paths are passed
directly (orchestrator runs on the host). Outputs are world-readable."""
from __future__ import annotations
import os, subprocess

IMAGE = os.environ.get("SECLAB_IMAGE", "seclab-web3/analysis:latest")
SCRATCH = os.environ.get("SECLAB_SCRATCH", "/opt/dlami/nvme/seclab")


def run_tool(target_dir: str, cmd: str, timeout: int = 900, image: str = IMAGE):
    """Run `cmd` in the analysis container over an absolute host target_dir."""
    cache = f"{SCRATCH}/toolcache"
    os.makedirs(cache, exist_ok=True)
    dcmd = ["docker", "run", "--rm", "-e", "HOME=/cache",
            "-v", f"{cache}:/cache", "-v", f"{target_dir}:/work", "-w", "/work",
            image, "bash", "-c", cmd]
    p = subprocess.run(dcmd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout, p.stderr


class Verifier:
    kind = "base"
    def verify(self, hypothesis, target):  # pragma: no cover
        raise NotImplementedError
