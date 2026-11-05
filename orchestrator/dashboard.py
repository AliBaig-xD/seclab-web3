"""Static HTML run dashboard (lever #14): an at-a-glance view of every run from the run
index — findings, reportable, proven, wall time — with links to each run's report."""
from __future__ import annotations
import html, os, sqlite3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def generate(index_db: str = None, out: str = None) -> tuple[str, int]:
    index_db = index_db or os.path.join(ROOT, "results", "run_index.db")
    out = out or os.path.join(ROOT, "results", "dashboard.html")
    rows = []
    if os.path.exists(index_db):
        c = sqlite3.connect(index_db)
        try:
            rows = c.execute("SELECT run_id,target,basis,findings,reportable,proven,wall_s,ts "
                             "FROM runs ORDER BY ts DESC").fetchall()
        except Exception:
            rows = []
        c.close()
    def td(x):
        return f"<td>{html.escape(str(x))}</td>"
    trs = ""
    for r in rows:
        link = f'<a href="runs/{html.escape(str(r[0]))}/report.md">{html.escape(str(r[0]))}</a>'
        proven = int(r[5] or 0)
        badge = f'<span class="p">{proven}</span>' if proven else str(proven)
        trs += ("<tr>" + f"<td>{link}</td>" + "".join(td(r[i]) for i in (1, 2, 3, 4)) +
                f"<td>{badge}</td>" + td(r[6]) + td(r[7]) + "</tr>")
    totals = {
        "runs": len(rows),
        "reportable": sum(int(r[4] or 0) for r in rows),
        "proven": sum(int(r[5] or 0) for r in rows),
    }
    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>seclab-web3 runs</title><style>
:root{{color-scheme:dark}} body{{background:#0d1117;color:#c9d1d9;font:14px/1.5 system-ui;margin:0;padding:24px}}
h1{{font-size:18px}} .k{{color:#8b949e;margin-right:16px}} .p{{color:#3fb950;font-weight:600}}
table{{border-collapse:collapse;width:100%;margin-top:16px}} th,td{{text-align:left;padding:8px 10px;border-bottom:1px solid #21262d}}
th{{color:#8b949e;font-weight:600}} a{{color:#58a6ff;text-decoration:none}} tr:hover{{background:#161b22}}
</style></head><body>
<h1>seclab-web3 — research runs</h1>
<div><span class="k">runs: {totals['runs']}</span><span class="k">reportable: {totals['reportable']}</span>
<span class="k">proven: {totals['proven']}</span></div>
<table><thead><tr><th>run</th><th>target</th><th>basis</th><th>findings</th><th>reportable</th>
<th>proven</th><th>wall(s)</th><th>time</th></tr></thead><tbody>{trs}</tbody></table>
</body></html>"""
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        f.write(doc)
    return out, len(rows)
