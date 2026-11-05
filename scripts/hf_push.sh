#!/usr/bin/env bash
# Push a trained adapter/model folder to a PRIVATE Hugging Face repo.
# Usage: HF_TOKEN=hf_xxx scripts/hf_push.sh <hf-user/repo> <folder> [--public]
# Token needs WRITE scope: https://huggingface.co/settings/tokens
set -euo pipefail
REPO="${1:?usage: hf_push.sh <hf-user/repo> <folder> [--public]}"
FOLDER="${2:?folder required}"
PRIVATE="true"; [ "${3:-}" = "--public" ] && PRIVATE="false"
: "${HF_TOKEN:?export HF_TOKEN (write-scoped) first}"
PY=/opt/pytorch/bin/python
"$PY" -c "import huggingface_hub" 2>/dev/null || "$PY" -m pip install -q huggingface_hub
HF_TOKEN="$HF_TOKEN" "$PY" - "$REPO" "$FOLDER" "$PRIVATE" <<'PYIN'
import os, sys
from huggingface_hub import HfApi, create_repo
repo, folder, private = sys.argv[1], sys.argv[2], sys.argv[3] == "true"
token = os.environ["HF_TOKEN"]
create_repo(repo, repo_type="model", private=private, exist_ok=True, token=token)
HfApi().upload_folder(folder_path=folder, repo_id=repo, repo_type="model", token=token)
print(f"pushed {folder} -> https://huggingface.co/{repo}  (private={private})")
PYIN
