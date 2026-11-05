"""Tool adapter base + sandboxed container runner. All analysis tools execute inside
the pinned analysis image, never on the host (docs/WORKFLOW.md sandboxing)."""
from __future__ import annotations
import subprocess

IMAGE = "seclab-web3/analysis:latest"


def run_tool(args: list[str], workdir: str, timeout: int = 600, image: str = IMAGE):
    """Run a tool in the analysis container over a mounted workdir. Returns (rc, out, err)."""
    cmd = ["docker", "run", "--rm", "-v", f"{workdir}:/work", "-w", "/work", image, *args]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout, p.stderr


class Verifier:
    """Protocol: given a hypothesis + target workdir, return Evidence or None."""
    kind = "base"

    def verify(self, hypothesis, target):  # pragma: no cover - interface
        raise NotImplementedError
