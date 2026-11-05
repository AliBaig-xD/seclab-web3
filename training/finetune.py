"""Config-driven QLoRA/LoRA fine-tuning. Swap the base model by editing config/train.yaml
(or --base). Reproducible: fixed seed, pinned deps, saved adapter + model card."""
from __future__ import annotations
import argparse, os, yaml, torch
from transformers import (AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer,
                          DataCollatorForLanguageModeling)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from datasets import load_dataset


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/train.yaml")
    ap.add_argument("--data", default="training/data/train.jsonl")
    ap.add_argument("--base", help="override base_model (model-swappability)")
    ap.add_argument("--out", default=None)
    ap.add_argument("--max-steps", type=int, default=0)
    a = ap.parse_args()
    cfg = yaml.safe_load(open(a.config))
    base = a.base or cfg["base_model"]
    tr = cfg.get("train", {})
    lc = cfg.get("lora", {})
    out = a.out or cfg.get("output_dir", "model/adapters")

    tok = AutoTokenizer.from_pretrained(base, trust_remote_code=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    qlora = cfg.get("method", "qlora") == "qlora"
    mk = dict(torch_dtype=torch.bfloat16, device_map="auto", trust_remote_code=True)
    if qlora:
        from transformers import BitsAndBytesConfig
        mk["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type=cfg.get("quantization", "nf4"),
            bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True)
    model = AutoModelForCausalLM.from_pretrained(base, **mk)
    if qlora:
        model = prepare_model_for_kbit_training(model)
    model = get_peft_model(model, LoraConfig(
        r=lc.get("r", 16), lora_alpha=lc.get("alpha", 32), lora_dropout=lc.get("dropout", 0.05),
        target_modules=lc.get("target_modules", "all-linear"), task_type="CAUSAL_LM"))
    model.print_trainable_parameters()

    ds = load_dataset("json", data_files=a.data, split="train")
    seq = tr.get("seq_len", 2048)

    def fmt(ex):
        msgs = [{"role": "user", "content": ex["instruction"] + (("\n\n" + ex["input"]) if ex.get("input") else "")},
                {"role": "assistant", "content": ex["output"]}]
        try:
            text = tok.apply_chat_template(msgs, tokenize=False)
        except Exception:
            text = msgs[0]["content"] + "\n\n" + msgs[1]["content"]
        o = tok(text, truncation=True, max_length=seq, padding="max_length")
        o["labels"] = o["input_ids"].copy()
        return o

    ds = ds.map(fmt, remove_columns=ds.column_names)
    args = TrainingArguments(
        output_dir=out, per_device_train_batch_size=tr.get("batch_size", 1),
        gradient_accumulation_steps=tr.get("grad_accum", 8),
        num_train_epochs=(tr.get("epochs", 3) if not a.max_steps else 1),
        max_steps=(a.max_steps or -1), learning_rate=tr.get("lr", 1e-4),
        bf16=True, logging_steps=1, save_strategy="no", seed=tr.get("seed", 0),
        gradient_checkpointing=True, report_to=[])
    Trainer(model=model, args=args, train_dataset=ds,
            data_collator=DataCollatorForLanguageModeling(tok, mlm=False)).train()
    os.makedirs(out, exist_ok=True)
    model.save_pretrained(out)
    tok.save_pretrained(out)
    with open(os.path.join(out, "README.md"), "w") as f:
        f.write(f"# seclab-web3 adapter\n\n- Base model: `{base}`\n- Method: {cfg.get('method')}\n"
                f"- LoRA: r={lc.get('r')} alpha={lc.get('alpha')}\n- Intended use: EVM security "
                f"research (detection, reasoning, PoC generation).\n- Dual-use: authorized "
                f"security research only.\n")
    print("saved adapter ->", out)


if __name__ == "__main__":
    main()
