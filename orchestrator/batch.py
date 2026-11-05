"""Batch runner: feed a list of targets (addresses / explorer URLs / repo URLs / local
paths, one per line), scan every one as an isolated subprocess, and rank them in a
leaderboard. So you harvest a corpus and let the lab churn — no hand-picking."""
from __future__ import annotations
import os, re, sys, json, time, subprocess, concurrent.futures as cf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS = os.path.join(ROOT, "results", "runs")
BATCHES = os.path.join(ROOT, "results", "batches")


def parse_targets_file(path):
    out = []
    for ln in open(path):
        s = ln.split("#", 1)[0].strip()
        if not s:
            continue
        parts = re.split(r"[,\s]+", s)
        chain = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
        out.append((parts[0], chain))
    return out


def _slug(t):
    return (re.sub(r"[^a-zA-Z0-9]+", "-", t)[-36:].strip("-").lower() or "t")


def _row_from_manifest(target, rid, man_path, status):
    m = json.load(open(man_path))
    return {"target": target, "run_id": rid, "status": status,
            "findings": m.get("findings", 0), "reportable": m.get("reportable", 0),
            "proven": m.get("proven", 0), "wall_s": m.get("wall_s", 0.0),
            "basis": m.get("basis"), "engines": m.get("engines")}


def _run_one(idx, target, chain, batch_id, basis, flags, timeout, resume):
    rid = f"{batch_id}-{idx:04d}-{_slug(target)}"
    man = os.path.join(RUNS, rid, "run_manifest.json")
    if resume and os.path.exists(man):
        return _row_from_manifest(target, rid, man, "cached")
    cmd = [sys.executable, "-m", "orchestrator.cli", "go", target,
           "--basis", basis, "--run-id", rid] + list(flags)
    if chain:
        cmd += ["--chain", str(chain)]
    t0 = time.time()
    status = "ok"
    try:
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
        if p.returncode == 2:
            status = "error"
        elif p.returncode != 0:
            status = f"exit{p.returncode}"
    except subprocess.TimeoutExpired:
        status = "timeout"
    if os.path.exists(man):
        return _row_from_manifest(target, rid, man, status)
    return {"target": target, "run_id": rid, "status": status, "findings": 0,
            "reportable": 0, "proven": 0, "wall_s": round(time.time() - t0, 1)}


def run_batch(path, basis="own", flags=(), jobs=1, timeout=3600, batch_id=None,
              resume=True, log=print):
    targets = parse_targets_file(path)
    if not targets:
        raise SystemExit(f"no targets in {path}")
    batch_id = batch_id or f"batch-{int(time.time())}"
    out_dir = os.path.join(BATCHES, batch_id)
    os.makedirs(out_dir, exist_ok=True)
    log(f"batch {batch_id}: {len(targets)} targets, jobs={jobs}, basis={basis}, "
        f"engines={'fast' if '--fast' in flags else 'full'}")
    rows, t0 = [], time.time()
    with cf.ThreadPoolExecutor(max_workers=max(1, jobs)) as ex:
        futs = {ex.submit(_run_one, i, t, c, batch_id, basis, flags, timeout, resume): t
                for i, (t, c) in enumerate(targets)}
        for n, fut in enumerate(cf.as_completed(futs), 1):
            r = fut.result()
            rows.append(r)
            log(f"  [{n}/{len(targets)}] {r['status']:>8}  "
                f"proven={r['proven']} reportable={r['reportable']} "
                f"findings={r['findings']}  {r['target'][:60]}")
    rows.sort(key=lambda r: (r["proven"], r["reportable"], r["findings"]), reverse=True)
    summary = {"batch_id": batch_id, "targets": len(targets),
               "scanned": sum(1 for r in rows if r["status"] in ("ok", "cached", "error")),
               "with_reportable": sum(1 for r in rows if r["reportable"]),
               "with_proven": sum(1 for r in rows if r["proven"]),
               "errors": sum(1 for r in rows if r["status"] not in ("ok", "cached")),
               "wall_s": round(time.time() - t0, 1), "basis": basis,
               "engines": "fast" if "--fast" in flags else "full", "results": rows}
    json.dump(summary, open(os.path.join(out_dir, "leaderboard.json"), "w"), indent=2)
    md = [f"# Batch {batch_id}", "",
          f"- targets: **{summary['targets']}**  scanned: **{summary['scanned']}**  "
          f"errors: **{summary['errors']}**",
          f"- with reportable findings: **{summary['with_reportable']}**  "
          f"with PROVEN: **{summary['with_proven']}**  wall: {summary['wall_s']}s", "",
          "| # | target | PROVEN | reportable | findings | status | run |",
          "|---|--------|--------|-----------|----------|--------|-----|"]
    for i, r in enumerate(rows, 1):
        md.append(f"| {i} | `{r['target'][:48]}` | {r['proven']} | {r['reportable']} "
                  f"| {r['findings']} | {r['status']} | {r['run_id']} |")
    open(os.path.join(out_dir, "leaderboard.md"), "w").write("\n".join(md) + "\n")
    log(f"leaderboard -> {out_dir}/leaderboard.md  "
        f"(with-proven={summary['with_proven']} with-reportable={summary['with_reportable']})")
    return summary
