#!/usr/bin/env bash
# Prod retrain on the full curated dataset. Waits for any in-progress run to free the GPU,
# preserves the baseline adapter for comparison, then runs the standard training pipeline
# (train.sh regenerates training/data from the curated default sources).
set -uo pipefail
cd "$(dirname "$0")/.."
echo "[retrain] waiting for GPU to free (baseline run)..."
while nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null | grep -q .; do sleep 60; done
echo "[retrain] GPU free at $(date -u +%H:%M:%SZ)"
[ -d model/adapters ] && cp -r model/adapters model/adapters_baseline 2>/dev/null || true
[ -f results/train_metrics.jsonl ] && cp results/train_metrics.jsonl results/train_metrics_baseline.jsonl 2>/dev/null || true
exec scripts/train.sh
