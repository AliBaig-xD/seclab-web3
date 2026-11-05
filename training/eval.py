"""Evaluate base+adapter on the holdout: generate for each test instruction and report a
simple keyword-recall over the expected answer (placeholder metric; extend in Phase 8)."""
from __future__ import annotations
import argparse, json, os, torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--adapter", default=None)
    ap.add_argument("--data", default="training/data/test.jsonl")
    ap.add_argument("--max-new", type=int, default=256)
    a = ap.parse_args()
    tok = AutoTokenizer.from_pretrained(a.base, trust_remote_code=True)
    m = AutoModelForCausalLM.from_pretrained(a.base, torch_dtype=torch.bfloat16,
                                             device_map="auto", trust_remote_code=True)
    if a.adapter and os.path.exists(a.adapter):
        m = PeftModel.from_pretrained(m, a.adapter)
    rows = [json.loads(l) for l in open(a.data)] if os.path.exists(a.data) else []
    hits = 0
    for r in rows:
        msgs = [{"role": "user", "content": r["instruction"] + "\n\n" + r.get("input", "")}]
        ids = tok.apply_chat_template(msgs, add_generation_prompt=True, return_tensors="pt").to(m.device)
        out = m.generate(ids, max_new_tokens=a.max_new, do_sample=False)
        gen = tok.decode(out[0][ids.shape[1]:], skip_special_tokens=True).lower()
        key = (r["output"].split()[0] if r["output"].split() else "").lower()
        if key and key in gen:
            hits += 1
    print(f"eval: {hits}/{len(rows)} first-token recall" if rows else "eval: no test rows")


if __name__ == "__main__":
    main()
