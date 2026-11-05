#!/usr/bin/env bash
# Resume the 7B training from the latest checkpoint after a crash/restart.
set -euo pipefail
cd "$(dirname "$0")/.."
VENV=/opt/dlami/nvme/seclab/trainvenv
export HF_HOME=/opt/dlami/nvme/seclab/hf
docker stop seclab-ollama >/dev/null 2>&1 || true   # free VRAM
ls model/adapters/checkpoint-* >/dev/null 2>&1 || { echo "no checkpoint yet; start fresh with scripts/train.sh"; exit 1; }
echo "resuming from latest checkpoint in model/adapters ..."
exec "$VENV/bin/python" training/finetune.py --resume
