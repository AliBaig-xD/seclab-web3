#!/usr/bin/env bash
# Idempotent, staged provisioning of the seclab-web3 box.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source config/versions.env; set +a
log(){ echo "[$(date +%H:%M:%S)] $*"; }
CF="docker/compose.yml"

stage_check(){
  log "docker $(docker version --format '{{.Server.Version}}')"
  docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi -L >/dev/null \
    && log "GPU-in-docker OK" || { log "GPU-in-docker FAIL"; exit 1; }
}
stage_dirs(){ for d in ollama work models forkcache runs; do mkdir -p "$SCRATCH/$d"; done; log "scratch ready: $SCRATCH"; }
stage_model(){
  docker compose -f "$CF" up -d ollama
  log "waiting for ollama API..."
  for i in $(seq 1 90); do curl -sf http://127.0.0.1:11434/api/version >/dev/null && break; sleep 2; done
  curl -sf http://127.0.0.1:11434/api/version >/dev/null || { log "ollama API down"; exit 1; }
  log "pulling $MODEL_REF (large, resumable)..."
  docker exec seclab-ollama ollama pull "$MODEL_REF"
  docker exec seclab-ollama ollama list
}
stage_analysis(){ log "building analysis image..."; docker build -f docker/analysis.Dockerfile -t seclab-web3/analysis:latest .; }
stage_symbolic(){ log "building custom mythril image..."; docker build -f docker/mythril.Dockerfile -t seclab-web3/mythril:latest .; }

case "${1:-all}" in
  check) stage_check;;
  dirs) stage_dirs;;
  model) stage_dirs; stage_model;;
  analysis) stage_analysis;;
  symbolic) stage_symbolic;;
  all) stage_check; stage_dirs; stage_model; stage_analysis; stage_symbolic; log "provision complete -> run scripts/doctor.sh";;
  *) echo "usage: provision.sh [check|dirs|model|analysis|all]"; exit 2;;
esac
