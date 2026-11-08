# Publish your trained adapter to Hugging Face

After training, the LoRA adapter is at `model/adapters/` (the baseline 1.5B adapter was
copied to `model/adapters_baseline/`). You push the **adapter** (a few hundred MB), not the
whole base model — anyone pulls it by naming the base + this adapter.

Current public release: https://huggingface.co/iamalibaig/seclab-web3-adapter

## 1. Get a write token (once)
https://huggingface.co/settings/tokens -> "New token" -> type **Write**. Copy `hf_...`.

## 2. Push it (one command)
```
cd ~/seclab-web3
read -rsp "HF write token: " HF_TOKEN; echo
HF_TOKEN="$HF_TOKEN" scripts/hf_push.sh iamalibaig/seclab-web3-adapter model/adapters --public
unset HF_TOKEN
```
- The script creates the repo if missing and uploads the adapter, tokenizer, metadata, and
  model card. It prints the URL.
- `upload_folder` does not delete files already present remotely. Remove obsolete remote files
  explicitly or recreate the repository before a clean release; do not repeatedly rerun the
  upload command to try to delete old files.
- Never paste tokens into chat, commit them, or leave them in shell history. Revoke exposed
  tokens immediately.

## 3. (Optional) push a model card so the repo is self-describing
```
cat > model/adapters/README.md <<'CARD'
---
base_model: Qwen/Qwen2.5-Coder-7B-Instruct
library_name: peft
tags: [security, solidity, evm, smart-contract-audit]
license: apache-2.0
---
# seclab-web3 adapter
QLoRA adapter for EVM security research. Base: Qwen2.5-Coder-7B-Instruct.
Proof-gated lab: the model proposes, tools + Foundry PoCs verify.
CARD
HF_TOKEN="$HF_TOKEN" scripts/hf_push.sh iamalibaig/seclab-web3-adapter model/adapters --public
```

## 4. Pull it back later (any machine)
```
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer
base = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-Coder-7B-Instruct")
model = PeftModel.from_pretrained(base, "iamalibaig/seclab-web3-adapter")
```

Auto-push after training: `scripts/train.sh "" --push` with `HF_TOKEN` and `HF_REPO` set.
Review the file list before publishing; do not publish checkpoints, datasets, or run artifacts
unless intentionally required.
