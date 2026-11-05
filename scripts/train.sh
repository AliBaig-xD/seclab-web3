#!/usr/bin/env bash
# Production training run. Frees the GPU (stops inference) for exclusive training.
# Usage: scripts/train.sh [--dry]   (--dry: tiny base + few steps to validate the pipeline)
set -euo pipefail
cd "$(dirname "$0")/.."
VENV=/opt/dlami/nvme/seclab/trainvenv
PYBASE=/opt/pytorch/bin/python
[ -d "$VENV" ] || "$PYBASE" -m venv --system-site-packages "$VENV"
"$VENV/bin/pip" install -q -U pip
"$VENV/bin/pip" install -q -r training/requirements.txt
PY="$VENV/bin/python"
export HF_HOME=/opt/dlami/nvme/seclab/hf PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

OLLAMA_WAS_UP=0
if docker ps --format '{{.Names}}' | grep -q seclab-ollama; then
  OLLAMA_WAS_UP=1; echo "[gpu] stopping ollama to free VRAM for training"; docker stop seclab-ollama >/dev/null
fi
restore(){ [ "$OLLAMA_WAS_UP" = 1 ] && docker start seclab-ollama >/dev/null 2>&1 && echo "[gpu] ollama restarted" || true; }
trap restore EXIT

"$PY" training/data_pipeline.py >/dev/null
echo "[data] prepared: $(wc -l < training/data/train.jsonl) train / $(wc -l < training/data/val.jsonl) val / $(wc -l < training/data/test.jsonl) test"

if [ "${1:-}" = "--dry" ]; then
  BASE="Qwen/Qwen2.5-0.5B-Instruct"; OUT=/opt/dlami/nvme/seclab/adapter-dry
  "$PY" training/finetune.py --base "$BASE" --max-steps 5 --out "$OUT"
  "$PY" training/evaluate.py --base "$BASE" --adapter "$OUT" --sample 8
else
  "$PY" training/finetune.py
  BASE=$(grep "^base_model" config/train.yaml | cut -d\" -f2)
  "$PY" training/evaluate.py --base "$BASE" --adapter model/adapters --sample 40
fi
