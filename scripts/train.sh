#!/usr/bin/env bash
# Set up the training venv (reuses DLAMI torch), prepare data, fine-tune, eval.
# Usage: scripts/train.sh [--dry]   (--dry uses a tiny base model + few steps to validate)
set -euo pipefail
cd "$(dirname "$0")/.."
VENV=/opt/dlami/nvme/seclab/trainvenv
PYBASE=/opt/pytorch/bin/python
if [ ! -d "$VENV" ]; then
  "$PYBASE" -m venv --system-site-packages "$VENV"
fi
"$VENV/bin/pip" install -q -U pip
"$VENV/bin/pip" install -q -r training/requirements.txt
PY="$VENV/bin/python"
"$PY" training/prepare_data.py
if [ "${1:-}" = "--dry" ]; then
  BASE="Qwen/Qwen2.5-0.5B-Instruct"
  HF_HOME=/opt/dlami/nvme/seclab/hf "$PY" training/finetune.py --base "$BASE" \
     --max-steps 3 --out /opt/dlami/nvme/seclab/adapter-dry
  HF_HOME=/opt/dlami/nvme/seclab/hf "$PY" training/eval.py --base "$BASE" \
     --adapter /opt/dlami/nvme/seclab/adapter-dry || true
else
  HF_HOME=/opt/dlami/nvme/seclab/hf "$PY" training/finetune.py
fi
