#!/usr/bin/env bash
# Push the repo to the EC2 box (code only; weights/artifacts excluded). Idempotent.
set -euo pipefail
cd "$(dirname "$0")/.."
source config/versions.env
KEY="${SECLAB_KEY:-$HOME/Downloads/tess-quiet-aws.pem}"
rsync -az --delete \
  --exclude '.git' --exclude 'model/weights' --exclude '*.gguf' \
  --exclude 'results/runs' --exclude 'eval/corpus/_cache' --exclude '__pycache__' \
  -e "ssh -i $KEY -o StrictHostKeyChecking=accept-new" \
  ./ "${BOX_USER}@${BOX_HOST}:${BOX_DIR}/"
echo "synced -> ${BOX_USER}@${BOX_HOST}:${BOX_DIR}"
