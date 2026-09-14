"""RAG store for business rules / SOPs.

Uses pgvector's `<=>` cosine operator when running on PostgreSQL (the Docker/demo path),
and falls back to in-Python cosine similarity on SQLite (tests / no-infra runs).
"""
from __future__ import annotations

import json
import math
from typing import List, Tuple

from sqlalchemy import text

from app.db.session import engine, is_postgres
from app.llm.provider import get_embedder


def _cosine(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


def init_and_seed(rules: List[str]) -> None:
    """(Re)create the business_rules store and load the SOP corpus."""
    embedder = get_embedder()
    vectors = embedder.embed(rules)

    if is_postgres():
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.execute(text("DROP TABLE IF EXISTS business_rules"))
            conn.execute(
                text(
                    f"CREATE TABLE business_rules ("
                    f"  rule_id SERIAL PRIMARY KEY,"
                    f"  rule_text TEXT NOT NULL,"
                    f"  embedding vector({embedder.dim})"
                    f")"
                )
            )
            for rule_text, vec in zip(rules, vectors):
                conn.execute(
                    text("INSERT INTO business_rules (rule_text, embedding) VALUES (:t, :e)"),
                    {"t": rule_text, "e": "[" + ",".join(str(x) for x in vec) + "]"},
                )
    else:
        with engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS business_rules"))
            conn.execute(
                text(
                    "CREATE TABLE business_rules ("
                    "  rule_id INTEGER PRIMARY KEY AUTOINCREMENT,"
                    "  rule_text TEXT NOT NULL,"
                    "  embedding TEXT"
                    ")"
                )
            )
            for rule_text, vec in zip(rules, vectors):
                conn.execute(
                    text("INSERT INTO business_rules (rule_text, embedding) VALUES (:t, :e)"),
                    {"t": rule_text, "e": json.dumps(vec)},
                )


def retrieve(query: str, k: int = 4) -> List[str]:
    """Return the top-k most relevant SOP rule texts for a query."""
    embedder = get_embedder()
    qvec = embedder.embed([query])[0]

    if is_postgres():
        qstr = "[" + ",".join(str(x) for x in qvec) + "]"
        with engine.begin() as conn:
            rows = conn.execute(
                text(
                    "SELECT rule_text FROM business_rules "
                    "ORDER BY embedding <=> CAST(:q AS vector) LIMIT :k"
                ),
                {"q": qstr, "k": k},
            ).fetchall()
        return [r[0] for r in rows]

    # SQLite fallback: python cosine
    with engine.begin() as conn:
        rows = conn.execute(text("SELECT rule_text, embedding FROM business_rules")).fetchall()
    scored: List[Tuple[float, str]] = []
    for rule_text, emb in rows:
        scored.append((_cosine(qvec, json.loads(emb)), rule_text))
    scored.sort(key=lambda s: s[0], reverse=True)
    return [t for _, t in scored[:k]]
