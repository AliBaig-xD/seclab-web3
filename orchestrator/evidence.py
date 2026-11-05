"""Durable, auditable evidence store (stdlib sqlite3). Every finding + its evidence
is persisted so results are traceable and reproducible (docs/WORKFLOW.md L1)."""
from __future__ import annotations
import sqlite3, json, time, os
from dataclasses import asdict
from .schema import Finding, finding_json

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs(
  id TEXT PRIMARY KEY, target TEXT, started REAL, meta TEXT);
CREATE TABLE IF NOT EXISTS findings(
  id TEXT PRIMARY KEY, run_id TEXT, tier TEXT, severity TEXT,
  vuln_type TEXT, location TEXT, reportable INT, repro_cmd TEXT, data TEXT);
CREATE TABLE IF NOT EXISTS evidence(
  id INTEGER PRIMARY KEY AUTOINCREMENT, finding_id TEXT, kind TEXT, tool TEXT,
  summary TEXT, artifact_path TEXT, digest TEXT, data TEXT);
"""


class EvidenceStore:
    def __init__(self, path: str):
        d = os.path.dirname(path)
        if d:
            os.makedirs(d, exist_ok=True)
        self._c = sqlite3.connect(path)
        self._c.executescript(SCHEMA)
        self._c.commit()

    def start_run(self, run_id: str, target: str, meta: dict | None = None):
        self._c.execute(
            "INSERT OR REPLACE INTO runs VALUES(?,?,?,?)",
            (run_id, target, time.time(), json.dumps(meta or {})),
        )
        self._c.commit()

    def save_finding(self, run_id: str, f: Finding):
        self._c.execute(
            "INSERT OR REPLACE INTO findings VALUES(?,?,?,?,?,?,?,?,?)",
            (f.hypothesis.id, run_id, f.tier.value, f.severity.value,
             f.hypothesis.vuln_type, f.hypothesis.location,
             int(f.reportable), f.repro_cmd, json.dumps(finding_json(f))),
        )
        self._c.execute("DELETE FROM evidence WHERE finding_id=?", (f.hypothesis.id,))
        for e in f.evidence:
            self._c.execute(
                "INSERT INTO evidence(finding_id,kind,tool,summary,artifact_path,digest,data)"
                " VALUES(?,?,?,?,?,?,?)",
                (f.hypothesis.id, e.kind, e.tool, e.summary, e.artifact_path,
                 e.digest(), json.dumps(asdict(e), default=str)),
            )
        self._c.commit()

    def reportable_findings(self, run_id: str) -> list[dict]:
        cur = self._c.execute(
            "SELECT id,tier,severity,vuln_type,location,repro_cmd"
            " FROM findings WHERE run_id=? AND reportable=1", (run_id,))
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    def close(self):
        self._c.close()
