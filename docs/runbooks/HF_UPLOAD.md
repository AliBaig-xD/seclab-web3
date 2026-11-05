# Upload your trained model to Hugging Face (private)

After training, the LoRA adapter is at `model/adapters/` (the baseline 1.5B adapter was
copied to `model/adapters_baseline/`). You push the **adapter** (a few hundred MB), not the
whole base model — anyone pulls it by naming the base + this adapter.

## 1. Get a write token (once)
https://huggingface.co/settings/tokens -> "New token" -> type **Write**. Copy `hf_...`.

## 2. Push it (one command)
```
cd ~/seclab-web3
HF_TOKEN=hf_xxxxx scripts/hf_push.sh AliBaig-xD/seclab-web3-7b model/adapters
```
- Private by default. Add `--public` as a 3rd arg to make it public.
- The script creates the repo if missing and uploads `model/adapters/` (adapter_config.json,
  adapter weights, tokenizer). It prints the URL.

## 3. (Optional) push a model card so the repo is self-describing
```
cat > model/adapters/README.md <<'CARD'
---
base_model: Qwen/Qwen2.5-Coder-7B-Instruct
library_name: peft
tags: [security, solidity, evm, smart-contract-audit]
license: apache-2.0
---
# seclab-web3-7b
QLoRA adapter for EVM smart-contract security review. Base: Qwen2.5-Coder-7B-Instruct.
Trained on a curated, provenance-tracked mix of real audit findings (FORGE), CVEs, real
exploit PoCs (DeFiHackLabs, learn-evm-attacks), and labeled vuln corpora. Proof-gated lab:
the model proposes, tools + Foundry PoCs verify.
CARD
HF_TOKEN=hf_xxxxx scripts/hf_push.sh AliBaig-xD/seclab-web3-7b model/adapters
```

## 4. Pull it back later (any machine)
```
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer
base = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-Coder-7B-Instruct")
model = PeftModel.from_pretrained(base, "AliBaig-xD/seclab-web3-7b")   # private -> pass token
```

Auto-push after training: `scripts/train.sh "" --push` with `HF_TOKEN` and `HF_REPO` set.
