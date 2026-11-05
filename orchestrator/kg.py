"""Knowledge Graph over a contract: entities (Contract, Function, StateVar, Role,
VulnClass) + relations (calls, reads, writes, inherits, guarded_by, has_finding).
Built from code intelligence; queryable; persistable. Complements the RAG vector KB."""
from __future__ import annotations
import json, sqlite3, os
from .codeintel import functions, call_graph, reachable, is_privileged, interaction_pairs


class KnowledgeGraph:
    def __init__(self):
        self.nodes = {}   # id -> {type, **attrs}
        self.edges = []   # (src, rel, dst)

    def _n(self, nid, ntype, **attrs):
        self.nodes[nid] = {"type": ntype, **attrs}

    def _e(self, s, rel, d):
        self.edges.append((s, rel, d))

    @classmethod
    def from_model(cls, model: dict) -> "KnowledgeGraph":
        g = cls()
        for c in model.get("contracts", []):
            cid = f"contract:{c['contract']}"
            g._n(cid, "Contract", name=c["contract"])
            for parent in c.get("inherits", []):
                g._e(cid, "inherits", f"contract:{parent}")
            for v in c.get("state_vars", []):
                g._n(f"state:{c['contract']}.{v}", "StateVar", name=v)
        cg = call_graph(model)
        for cname, f in functions(model):
            fid = f"func:{cname}.{f['name']}"
            g._n(fid, "Function", name=f["name"], contract=cname, visibility=f.get("vis"),
                 privileged=is_privileged(f), external=f.get("vis") in ("public", "external"))
            g._e(f"contract:{cname}", "declares", fid)
            for m in f.get("modifiers", []):
                g._n(f"role:{m}", "Role", name=m)
                g._e(fid, "guarded_by", f"role:{m}")
            for v in f.get("reads", []):
                g._e(fid, "reads", f"state:{cname}.{v}")
            for v in f.get("writes", []):
                g._e(fid, "writes", f"state:{cname}.{v}")
            for (c2, callee) in cg.get((cname, f["name"]), []):
                g._e(fid, "calls", f"func:{c2}.{callee}")
        return g

    # ---- queries ----
    def privileged_functions(self):
        return [n for n, a in self.nodes.items() if a["type"] == "Function" and a.get("privileged")]

    def external_entrypoints(self):
        return [n for n, a in self.nodes.items() if a["type"] == "Function" and a.get("external")]

    def functions_touching(self, state_var_name: str):
        sid_suffix = f".{state_var_name}"
        out = set()
        for s, rel, d in self.edges:
            if rel in ("reads", "writes") and d.endswith(sid_suffix):
                out.add(s)
        return sorted(out)

    def unguarded_state_writers(self):
        """External functions that WRITE state but are NOT guarded by any role."""
        writers = {s for s, rel, _ in self.edges if rel == "writes"}
        guarded = {s for s, rel, _ in self.edges if rel == "guarded_by"}
        return sorted(f for f in writers if f in self.nodes
                      and self.nodes[f].get("external") and f not in guarded)

    def attach_findings(self, findings):
        for f in findings:
            vid = f"vuln:{f.hypothesis.vuln_type}"
            self._n(vid, "VulnClass", name=f.hypothesis.vuln_type)
            self._e(f"finding:{f.hypothesis.id}", "has_vuln", vid)

    def save(self, path: str):
        d = os.path.dirname(path)
        if d:
            os.makedirs(d, exist_ok=True)
        c = sqlite3.connect(path)
        c.execute("CREATE TABLE IF NOT EXISTS nodes(id TEXT PRIMARY KEY, data TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS edges(src TEXT, rel TEXT, dst TEXT)")
        c.execute("DELETE FROM nodes"); c.execute("DELETE FROM edges")
        c.executemany("INSERT INTO nodes VALUES(?,?)",
                      [(k, json.dumps(v)) for k, v in self.nodes.items()])
        c.executemany("INSERT INTO edges VALUES(?,?,?)", self.edges)
        c.commit(); c.close()

    def stats(self):
        import collections
        nt = collections.Counter(a["type"] for a in self.nodes.values())
        rt = collections.Counter(r for _, r, _ in self.edges)
        return {"nodes": dict(nt), "edges": dict(rt)}
