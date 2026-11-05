# Runbook — Training the specialized model

The pipeline is config-driven and model/hardware agnostic: switch the base model by
editing `config/train.yaml` (or `--base`); the same code scales to A100/multi-GPU.

## Data
`python3 training/data_pipeline.py` curates from all sources into `training/data/`
(train/val/test.jsonl + data_card.json). Leakage-safe split BY CONTRACT; provenance +
license per example. Sources: SmartBugs-curated, SolidiFI, DeFiHackLabs (PoCs), Web3Bugs,
not-so-smart, DeFiVulnLabs, our corpus, and `slither_wild` (self-labeled flywheel).
Grow the self-labeled set: `bash scripts/run_harvest.sh` (Slither over a raw corpus).

## Train + eval (frees the GPU automatically)
```
bash scripts/train.sh            # full run on config/train.yaml
bash scripts/train.sh --dry      # tiny model + few steps to validate the pipeline
```
`train.sh` stops the Ollama container (frees VRAM), prepares data, fine-tunes (QLoRA),
evaluates (perplexity + detection accuracy + PoC structural), and restarts Ollama.
Artifacts: `model/adapters/` (adapter + tokenizer + train_config + data_card + model card),
`results/train_metrics.jsonl`, `results/eval_report.json`.

## Scale to bigger hardware / model
Edit `config/train.yaml`: `base_model`, `method` (qlora|lora|full), `lora.r/alpha`,
`train.seq_len/batch_size/grad_accum/attn_implementation`. No code change.

## Publish (private)
```
HF_TOKEN=hf_xxx scripts/hf_push.sh <user>/seclab-web3-adapter model/adapters
```
Creates a PRIVATE repo and uploads. Weights never leave your control.
