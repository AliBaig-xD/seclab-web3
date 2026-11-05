#!/usr/bin/env bash
# Serve the trained model (base + LoRA adapter) via vLLM (OpenAI-compatible) so the lab
# uses the specialized model. After it is up, point the lab at it:
#   config/model.yaml -> server: vllm, endpoint: http://127.0.0.1:8001, model_ref: seclab
set -euo pipefail
cd "$(dirname "$0")/.."
VENV=/opt/dlami/nvme/seclab/servevenv
PYBASE=/opt/pytorch/bin/python
[ -d "$VENV" ] || "$PYBASE" -m venv --system-site-packages "$VENV"
"$VENV/bin/pip" install -q -U vllm
BASE=$(grep "^base_model" config/train.yaml | cut -d\" -f2)
[ -f model/adapters/adapter_config.json ] || { echo "no adapter in model/adapters — train first"; exit 1; }
docker stop seclab-ollama >/dev/null 2>&1 || true   # free VRAM for vLLM
export HF_HOME=/opt/dlami/nvme/seclab/hf
echo "serving $BASE + adapter(seclab) on :8001 ..."
exec "$VENV/bin/python" -m vllm.entrypoints.openai.api_server \
  --model "$BASE" --enable-lora --lora-modules seclab=model/adapters \
  --port 8001 --max-model-len 4096 --gpu-memory-utilization 0.85 --dtype bfloat16
