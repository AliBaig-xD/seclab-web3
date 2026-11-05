#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
D=/opt/dlami/nvme/seclab/datasets
if [ ! -d "$D/smartbugs-wild/.git" ]; then
  rm -rf "$D/smartbugs-wild"
  echo "cloning smartbugs-wild (large)..."
  git clone --depth 1 https://github.com/smartbugs/smartbugs-wild "$D/smartbugs-wild"
fi
N=$(find "$D/smartbugs-wild" -name "*.sol" | wc -l)
echo "wild contracts available: $N"
python3 training/harvest_slither.py --corpus "$D/smartbugs-wild" --n 6000 --workers 3 --budget-min 75
