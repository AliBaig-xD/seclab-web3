"""Production eval: perplexity on holdout + per-capability metrics (A detection accuracy,
C PoC structural validity). Writes results/eval_report.json. Honest, reproducible."""
from __future__ import annotations
import argparse, json, math, os, re, torch
from transformers import AutoModelForCausalLM, AutoTokenizer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(base, adapter):
    tok = AutoTokenizer.from_pretrained(base, trust_remote_code=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    offload_folder = os.environ.get(
        "SECLAB_EVAL_OFFLOAD", "/opt/dlami/nvme/seclab/eval-offload"
    )
    os.makedirs(offload_folder, exist_ok=True)
    m = AutoModelForCausalLM.from_pretrained(
        base,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        offload_folder=offload_folder,
        offload_state_dict=True,
        trust_remote_code=True,
    )
    if adapter and os.path.exists(os.path.join(adapter, "adapter_config.json")):
        from peft import PeftModel
        m = PeftModel.from_pretrained(m, adapter, offload_folder=offload_folder)
    m.eval()
    return tok, m


def generate(tok, m, instruction, inp, max_new=220):
    user = instruction + (("\n\n" + inp) if inp else "")
    ids = tok.apply_chat_template([{"role": "user", "content": user}],
                                  add_generation_prompt=True, return_tensors="pt").to(m.device)
    with torch.no_grad():
        out = m.generate(ids, max_new_tokens=max_new, do_sample=False, pad_token_id=tok.pad_token_id)
    return tok.decode(out[0][ids.shape[1]:], skip_special_tokens=True)


def perplexity(tok, m, rows, seq=1024):
    tot_loss, tot_tok = 0.0, 0
    for r in rows:
        user = r["instruction"] + (("\n\n" + r.get("input", "")) if r.get("input") else "")
        prompt = tok.apply_chat_template([{"role": "user", "content": user}],
                                         add_generation_prompt=True, tokenize=False)
        full = tok.apply_chat_template([{"role": "user", "content": user},
                                        {"role": "assistant", "content": r["output"]}], tokenize=False)
        p = tok(prompt, add_special_tokens=False)["input_ids"]
        f = tok(full, add_special_tokens=False)["input_ids"][:seq]
        if len(f) <= len(p):
            continue
        ids = torch.tensor([f]).to(m.device)
        labels = ids.clone()
        labels[0, :len(p)] = -100
        with torch.no_grad():
            loss = m(ids, labels=labels).loss.item()
        n = int((labels != -100).sum().item())
        tot_loss += loss * n
        tot_tok += n
    return math.exp(tot_loss / tot_tok) if tot_tok else float("nan")


def poc_valid(text):
    mt = re.search(r"```(?:solidity|sol)?\s*(.*?)```", text, re.S)
    code = (mt.group(1) if mt else text)
    return ("contract" in code and ("is Test" in code or "function test" in code)
            and code.count("{") == code.count("}") and code.count("{") > 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--adapter", default=None)
    ap.add_argument("--data", default="training/data/test.jsonl")
    ap.add_argument("--sample", type=int, default=40)
    a = ap.parse_args()
    rows = [json.loads(l) for l in open(a.data)] if os.path.exists(a.data) else []
    tok, m = load(a.base, a.adapter)
    byc = {"A": [], "B": [], "C": []}
    for r in rows:
        byc.get(r.get("capability", "A"), byc["A"]).append(r)
    rep = {"base": a.base, "adapter": a.adapter, "test_rows": len(rows),
           "perplexity": round(perplexity(tok, m, rows[:a.sample]), 3) if rows else None}
    # A: detection accuracy
    A = byc["A"][:a.sample]
    hitA = 0
    for r in A:
        g = generate(tok, m, r["instruction"], r.get("input", "")).lower()
        if r["vuln_class"].replace("_", " ").split()[0] in g or r["vuln_class"] in g:
            hitA += 1
    rep["A_detection_accuracy"] = round(hitA / len(A), 3) if A else None
    # C: PoC structural validity
    C = byc["C"][:min(a.sample, 20)]
    okC = sum(poc_valid(generate(tok, m, r["instruction"], r.get("input", ""), max_new=400)) for r in C)
    rep["C_poc_structural_rate"] = round(okC / len(C), 3) if C else None
    rep["counts"] = {k: len(v) for k, v in byc.items()}
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    with open(os.path.join(ROOT, "results", "eval_report.json"), "w") as f:
        json.dump(rep, f, indent=2)
    print(json.dumps(rep, indent=2))


if __name__ == "__main__":
    main()
