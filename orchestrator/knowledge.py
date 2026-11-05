"""Self-hosted RAG knowledge base. Pluggable embedder (deterministic hash-based offline
default; Ollama semantic embeddings when available), SQLite vector store, cosine search.
Grounds the LLM in vuln-class knowledge (swappable to pgvector/Qdrant later)."""
from __future__ import annotations
import hashlib, json, math, os, re, sqlite3, urllib.request


def cosine(a, b) -> float:
    s = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return s / (na * nb) if na and nb else 0.0


class HashEmbedder:
    """Deterministic lexical embedding: dependency-free, offline, good for keyword recall."""
    dim = 256
    name = "hash-256"

    def embed(self, text: str):
        v = [0.0] * self.dim
        for tok in re.findall(r"[a-zA-Z_]{3,}", (text or "").lower()):
            v[int(hashlib.md5(tok.encode()).hexdigest(), 16) % self.dim] += 1.0
        n = math.sqrt(sum(x * x for x in v))
        return [x / n for x in v] if n else v


class OllamaEmbedder:
    def __init__(self, endpoint: str, model: str = "nomic-embed-text"):
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.name = f"ollama-{model}"

    def embed(self, text: str):
        req = urllib.request.Request(
            self.endpoint + "/api/embeddings",
            data=json.dumps({"model": self.model, "prompt": text}).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())["embedding"]


class KnowledgeBase:
    def __init__(self, db_path: str, embedder=None):
        self.embedder = embedder or HashEmbedder()
        d = os.path.dirname(db_path)
        if d:
            os.makedirs(d, exist_ok=True)
        self._c = sqlite3.connect(db_path)
        self._c.execute("CREATE TABLE IF NOT EXISTS kb(id INTEGER PRIMARY KEY, source TEXT, "
                        "title TEXT, text TEXT, emb TEXT)")
        self._c.commit()

    def add(self, source: str, title: str, text: str):
        emb = json.dumps(self.embedder.embed(f"{title}\n{text}"))
        self._c.execute("INSERT INTO kb(source,title,text,emb) VALUES(?,?,?,?)",
                        (source, title, text, emb))
        self._c.commit()

    def count(self) -> int:
        return self._c.execute("SELECT COUNT(*) FROM kb").fetchone()[0]

    def query(self, text: str, k: int = 4):
        q = self.embedder.embed(text)
        rows = self._c.execute("SELECT title,text,emb FROM kb").fetchall()
        scored = [(cosine(q, json.loads(e)), t, x) for t, x, e in rows]
        scored.sort(reverse=True)
        return [{"title": t, "text": x, "score": round(s, 3)} for s, t, x in scored[:k] if s > 0]

    def seed_from_cards(self, cards_path: str) -> int:
        cards = json.load(open(cards_path))
        for c in cards:
            self.add(c.get("source", "card"), c["title"], c["text"])
        return len(cards)
