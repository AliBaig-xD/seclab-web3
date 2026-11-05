#!/usr/bin/env bash
# Run orchestrator unit tests in a clean Python 3.11 container (reproducible).
set -euo pipefail
cd "$(dirname "$0")/.."
docker run --rm -v "$PWD":/w -w /w python:3.11-slim bash -lc \
  "pip install -q -r orchestrator/requirements.txt pytest && python -m pytest -q tests"
