#!/usr/bin/env bash
# Prod retrain on the full curated dataset. Waits for the in-progress baseline training
# pipeline (finetune + evaluate) to finish, preserves the baseline adapter, then runs the
# standard pipeline (train.sh regenerates training/data from the curated default sources).
set -uo pipefail
cd "$(dirname "$0")/.."
echo "[retrain] $(date -u +%H:%M:%SZ) waiting for baseline training to finish..."
while pgrep -f 'training/finetune.py' >/dev/null || pgrep -f 'training/evaluate.py' >/dev/null; do sleep 60; done
echo "[retrain] $(date -u +%H:%M:%SZ) baseline done; preserving its adapter"
[ -d model/adapters ] && cp -r model/adapters model/adapters_baseline 2>/dev/null || true
[ -f results/train_metrics.jsonl ] && cp results/train_metrics.jsonl results/train_metrics_baseline.jsonl 2>/dev/null || true
docker stop seclab-ollama >/dev/null 2>&1 || true
echo "[retrain] $(date -u +%H:%M:%SZ) launching prod training on the curated set"
exec scripts/train.sh
