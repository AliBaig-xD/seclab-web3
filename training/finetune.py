"""Production SFT (QLoRA/LoRA/full), config-driven and model/hardware agnostic.
Completion-only loss masking, dynamic padding, warmup+cosine, eval+checkpoint+resume,
best-model selection, paged 8-bit optimizer, reproducible (seed + config/data snapshot)."""
from __future__ import annotations
import argparse, json, os, shutil, time, yaml, torch
from transformers import (AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer,
                          TrainerCallback, set_seed)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class JsonlLogger(TrainerCallback):
    def __init__(self, path):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w").close()
    def on_log(self, args, state, control, logs=None, **kw):
        if logs:
            with open(self.path, "a") as f:
                f.write(json.dumps({"step": state.global_step, **logs}) + "\n")


def tokenize(ex, tok, seq_len):
    user = ex["instruction"] + (("\n\n" + ex["input"]) if ex.get("input") else "")
    try:
        prompt = tok.apply_chat_template([{"role": "user", "content": user}],
                                         add_generation_prompt=True, tokenize=False)
        full = tok.apply_chat_template([{"role": "user", "content": user},
                                        {"role": "assistant", "content": ex["output"]}], tokenize=False)
    except Exception:
        prompt = user + "\n"
        full = user + "\n" + ex["output"]
    p_ids = tok(prompt, add_special_tokens=False)["input_ids"]
    f_ids = tok(full, add_special_tokens=False)["input_ids"][:seq_len]
    labels = list(f_ids)
    for i in range(min(len(p_ids), len(f_ids))):
        labels[i] = -100
    return {"input_ids": f_ids, "attention_mask": [1] * len(f_ids), "labels": labels,
            "length": len(f_ids)}


class Collator:
    def __init__(self, pad_id):
        self.pad = pad_id
    def __call__(self, batch):
        m = max(len(b["input_ids"]) for b in batch)
        ii, am, lb = [], [], []
        for b in batch:
            n = m - len(b["input_ids"])
            ii.append(b["input_ids"] + [self.pad] * n)
            am.append(b["attention_mask"] + [0] * n)
            lb.append(b["labels"] + [-100] * n)
        return {"input_ids": torch.tensor(ii), "attention_mask": torch.tensor(am),
                "labels": torch.tensor(lb)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/train.yaml")
    ap.add_argument("--data-dir", default="training/data")
    ap.add_argument("--base")
    ap.add_argument("--out")
    ap.add_argument("--max-steps", type=int, default=0)
    ap.add_argument("--resume", action="store_true")
    a = ap.parse_args()
    cfg = yaml.safe_load(open(a.config))
    tr, lc = cfg.get("train", {}), cfg.get("lora", {})
    base = a.base or cfg["base_model"]
    out = a.out or cfg.get("output_dir", "model/adapters")
    set_seed(tr.get("seed", 0))

    from datasets import load_dataset
    files = {"train": os.path.join(a.data_dir, "train.jsonl")}
    valp = os.path.join(a.data_dir, "val.jsonl")
    has_val = os.path.exists(valp) and os.path.getsize(valp) > 0
    if has_val:
        files["validation"] = valp
    ds = load_dataset("json", data_files=files)

    tok = AutoTokenizer.from_pretrained(base, trust_remote_code=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    seq = tr.get("seq_len", 2048)
    ds = ds.map(lambda e: tokenize(e, tok, seq), remove_columns=ds["train"].column_names)

    qlora = cfg.get("method", "qlora") == "qlora"
    mk = dict(torch_dtype=torch.bfloat16, device_map="auto", trust_remote_code=True,
              attn_implementation=tr.get("attn_implementation", "sdpa"))
    if qlora:
        from transformers import BitsAndBytesConfig
        mk["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type=cfg.get("quantization", "nf4"),
            bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True)
    model = AutoModelForCausalLM.from_pretrained(base, **mk)
    model.config.use_cache = False
    if qlora:
        model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
    if cfg.get("method") != "full":
        model = get_peft_model(model, LoraConfig(
            r=lc.get("r", 32), lora_alpha=lc.get("alpha", 64), lora_dropout=lc.get("dropout", 0.05),
            target_modules=lc.get("target_modules", "all-linear"), task_type="CAUSAL_LM"))
        model.print_trainable_parameters()

    args = TrainingArguments(
        output_dir=out, per_device_train_batch_size=tr.get("batch_size", 1),
        per_device_eval_batch_size=1, gradient_accumulation_steps=tr.get("grad_accum", 16),
        num_train_epochs=(tr.get("epochs", 3) if not a.max_steps else 1),
        max_steps=(a.max_steps or -1), learning_rate=float(tr.get("lr", 2e-4)),
        warmup_ratio=tr.get("warmup_ratio", 0.03), weight_decay=tr.get("weight_decay", 0.01),
        lr_scheduler_type=tr.get("lr_scheduler", "cosine"), max_grad_norm=tr.get("max_grad_norm", 0.3),
        bf16=True, gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        logging_strategy="steps", logging_steps=tr.get("logging_steps", 5),
        eval_strategy=("steps" if has_val else "no"), eval_steps=tr.get("eval_steps", 50),
        save_strategy="steps", save_steps=tr.get("save_steps", 50),
        save_total_limit=tr.get("save_total_limit", 3),
        load_best_model_at_end=has_val, metric_for_best_model="eval_loss", greater_is_better=False,
        group_by_length=tr.get("group_by_length", True), length_column_name="length",
        optim=tr.get("optim", "paged_adamw_8bit"), seed=tr.get("seed", 0),
        report_to=[])
    trainer = Trainer(model=model, args=args, train_dataset=ds["train"],
                      eval_dataset=(ds["validation"] if has_val else None),
                      data_collator=Collator(tok.pad_token_id),
                      callbacks=[JsonlLogger(os.path.join(ROOT, "results", "train_metrics.jsonl"))])
    t0 = time.time()
    trainer.train(resume_from_checkpoint=a.resume)
    os.makedirs(out, exist_ok=True)
    model.save_pretrained(out)
    tok.save_pretrained(out)
    # reproducibility snapshot + model card
    shutil.copy(a.config, os.path.join(out, "train_config.yaml"))
    dc = os.path.join(a.data_dir, "data_card.json")
    if os.path.exists(dc):
        shutil.copy(dc, os.path.join(out, "data_card.json"))
    with open(os.path.join(out, "README.md"), "w") as f:
        f.write(f"# seclab-web3 adapter\n\n- Base model: `{base}`\n- Method: {cfg.get('method')}\n"
                f"- LoRA: r={lc.get('r')} alpha={lc.get('alpha')} dropout={lc.get('dropout')}\n"
                f"- Train examples: {len(ds['train'])}\n- Wall time: {time.time()-t0:.0f}s\n"
                f"- Intended use: EVM security research (detection, protocol reasoning, PoC generation).\n"
                f"- Dual-use: authorized security research only.\n")
    print("saved adapter ->", out)


if __name__ == "__main__":
    main()
