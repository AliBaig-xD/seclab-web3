import sqlite3
from orchestrator.dashboard import generate


def test_dashboard_html(tmp_path):
    db = tmp_path / "run_index.db"
    c = sqlite3.connect(str(db))
    c.execute("CREATE TABLE runs(run_id TEXT,target TEXT,basis TEXT,findings INT,reportable INT,"
              "proven INT,wall_s REAL,ts TEXT)")
    c.execute("INSERT INTO runs VALUES('run-1','vault','own',8,1,1,35.8,'2026-11-05')")
    c.commit(); c.close()
    out = tmp_path / "d.html"
    path, n = generate(index_db=str(db), out=str(out))
    doc = open(path).read()
    assert n == 1 and "run-1" in doc and "runs/run-1/report.md" in doc and "seclab-web3" in doc


def test_dashboard_empty(tmp_path):
    out = tmp_path / "d.html"
    _p, n = generate(index_db=str(tmp_path / "nope.db"), out=str(out))
    assert n == 0 and "runs: 0" in open(out).read()
