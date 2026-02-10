from __future__ import annotations

import sqlite3
from typing import Any

from ontology_llm.tools.llm_tools import build_client, try_attach_memori
from ontology_llm.tools.sql_tools import (
    extract_priority_price_fact,
    extract_query_terms,
    get_db,
    is_price_question,
    lookup_ontology_context,
)

_CLIENT = None
_MODEL = None
_MEMORI_ATTACHED = False
_MEMORI_ATTACH_ATTEMPTED = False


def get_client_model(db_path: str):
    global _CLIENT, _MODEL, _MEMORI_ATTACHED, _MEMORI_ATTACH_ATTEMPTED
    if _CLIENT is None:
        _CLIENT, _MODEL = build_client()
    if not _MEMORI_ATTACH_ATTEMPTED:
        _MEMORI_ATTACHED, _ = try_attach_memori(_CLIENT, db_path)
        _MEMORI_ATTACH_ATTEMPTED = True
    return _CLIENT, _MODEL


def llm_answer(db_path: str, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
    client, model = get_client_model(db_path)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
    )
    return resp.choices[0].message.content or ""


def parse_tokens(question: str) -> list[str]:
    return [t for t in extract_query_terms(question) if t]


def fetch_relations(conn: sqlite3.Connection, source_ids: list[str]) -> list[tuple[str, str, str]]:
    if not source_ids:
        return []
    qmarks = ",".join("?" for _ in source_ids)
    return conn.execute(
        f"SELECT source_id, type, target_id FROM onto_relations WHERE source_id IN ({qmarks})",
        source_ids,
    ).fetchall()


def basic_context(question: str, db_path: str) -> tuple[sqlite3.Connection, str, str | None]:
    conn = get_db(db_path)
    context = lookup_ontology_context(conn, question)
    price_hint = extract_priority_price_fact(conn, question) if is_price_question(question) else None
    return conn, context, price_hint


def format_result(method_id: str, method_name: str, question: str, prompt: str, answer: str) -> dict[str, Any]:
    return {
        "method_id": method_id,
        "method_name": method_name,
        "question": question,
        "prompt": prompt,
        "answer": answer,
    }
