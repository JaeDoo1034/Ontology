from __future__ import annotations

import re
import sqlite3
from typing import Any

import yaml

INIT_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS onto_classes (
    name TEXT PRIMARY KEY,
    description TEXT
);

CREATE TABLE IF NOT EXISTS onto_instances (
    id TEXT PRIMARY KEY,
    class_name TEXT NOT NULL,
    label TEXT,
    FOREIGN KEY(class_name) REFERENCES onto_classes(name)
);

CREATE TABLE IF NOT EXISTS onto_properties (
    instance_id TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT,
    PRIMARY KEY(instance_id, key),
    FOREIGN KEY(instance_id) REFERENCES onto_instances(id)
);

CREATE TABLE IF NOT EXISTS onto_relations (
    source_id TEXT NOT NULL,
    type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    PRIMARY KEY(source_id, type, target_id),
    FOREIGN KEY(source_id) REFERENCES onto_instances(id),
    FOREIGN KEY(target_id) REFERENCES onto_instances(id)
);
"""

LOOKUP_QUERY_TEMPLATE = """
SELECT i.id, i.class_name, COALESCE(i.label, ''),
       COALESCE(group_concat(p.key || '=' || p.value, '; '), '')
FROM onto_instances i
LEFT JOIN onto_properties p ON p.instance_id = i.id
WHERE {where_clause}
GROUP BY i.id, i.class_name, i.label
LIMIT ?
"""

RELATIONS_BY_IDS_TEMPLATE = """
SELECT source_id, type, target_id
FROM onto_relations
WHERE source_id IN ({qmarks})
"""

PRICE_FACT_QUERY_TEMPLATE = """
SELECT i.id, COALESCE(i.label, ''), p.value
FROM onto_instances i
JOIN onto_properties p ON p.instance_id = i.id
WHERE p.key = 'price_krw'
  AND ({where_clause})
LIMIT 1
"""


def get_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(INIT_SCHEMA_SQL)
    conn.commit()


def ingest_ontology_yaml(conn: sqlite3.Connection, yaml_path: str) -> None:
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    for elem in data.get("classes", []):
        conn.execute(
            "INSERT OR REPLACE INTO onto_classes(name, description) VALUES (?, ?)",
            (elem.get("name"), elem.get("description")),
        )

    for inst in data.get("instances", []):
        inst_id = inst.get("id")
        class_name = inst.get("class")
        label = (inst.get("label") or "").strip() or None
        conn.execute(
            "INSERT OR REPLACE INTO onto_instances(id, class_name, label) VALUES (?, ?, ?)",
            (inst_id, class_name, label),
        )
        for prop in inst.get("properties", []):
            conn.execute(
                "INSERT OR REPLACE INTO onto_properties(instance_id, key, value) VALUES (?, ?, ?)",
                (inst_id, prop.get("key"), str(prop.get("value")) if prop.get("value") is not None else None),
            )

    for rel in data.get("relations", []):
        conn.execute(
            "INSERT OR REPLACE INTO onto_relations(source_id, type, target_id) VALUES (?, ?, ?)",
            (rel.get("source"), rel.get("type"), rel.get("target")),
        )

    conn.commit()


def extract_query_terms(question: str) -> list[str]:
    terms = [question.strip().lower()]
    terms.extend(
        token.lower()
        for token in re.findall(r"[0-9A-Za-z가-힣]+", question)
        if len(token) >= 2
    )
    deduped = list(dict.fromkeys(t for t in terms if t))
    return deduped or [""]


def _build_lookup_where_clause(terms: list[str]) -> tuple[str, list[object]]:
    where_per_term = """
        lower(i.id) LIKE ?
        OR lower(i.class_name) LIKE ?
        OR lower(COALESCE(i.label, '')) LIKE ?
        OR EXISTS (
            SELECT 1 FROM onto_properties p2
            WHERE p2.instance_id = i.id
            AND (lower(p2.key) LIKE ? OR lower(COALESCE(p2.value, '')) LIKE ?)
        )
    """
    where_clause = " OR ".join([f"({where_per_term})" for _ in terms])
    params: list[object] = []
    for term in terms:
        pattern = f"%{term}%"
        params.extend([pattern, pattern, pattern, pattern, pattern])
    return where_clause, params


def lookup_ontology_debug(
    conn: sqlite3.Connection, question: str, limit: int = 5
) -> dict[str, Any]:
    terms = extract_query_terms(question)
    where_clause, params = _build_lookup_where_clause(terms)
    params.append(limit)

    rows = conn.execute(
        LOOKUP_QUERY_TEMPLATE.format(where_clause=where_clause),
        params,
    ).fetchall()

    candidates: list[dict[str, Any]] = []
    keyword_scores: dict[str, int] = {t: 0 for t in terms}
    for inst_id, cls, label, props in rows:
        inst_id_l = (inst_id or "").lower()
        cls_l = (cls or "").lower()
        label_l = (label or "").lower()
        props_l = (props or "").lower()

        matched_terms: list[str] = []
        matched_fields: set[str] = set()
        score = 0
        for t in terms:
            if not t:
                continue
            in_id = t in inst_id_l
            in_class = t in cls_l
            in_label = t in label_l
            in_props = t in props_l
            if in_id or in_class or in_label or in_props:
                matched_terms.append(t)
                keyword_scores[t] += 1
                if in_id:
                    matched_fields.add("id")
                    score += 3
                if in_class:
                    matched_fields.add("class")
                    score += 1
                if in_label:
                    matched_fields.add("label")
                    score += 4
                if in_props:
                    matched_fields.add("properties")
                    score += 2
        if "alias=" in props_l:
            score += 1
        if "price_krw=" in props_l:
            score += 1

        candidates.append(
            {
                "id": inst_id,
                "class_name": cls,
                "label": label,
                "matched_terms": matched_terms,
                "matched_fields": sorted(matched_fields),
                "score": score,
            }
        )

    prioritized_terms = [
        term
        for term, _ in sorted(
            keyword_scores.items(),
            key=lambda item: (-item[1], -len(item[0]), item[0]),
        )
        if term
    ]
    candidates.sort(key=lambda item: (-item["score"], item["id"]))
    return {
        "query_terms": [t for t in terms if t],
        "prioritized_terms": prioritized_terms,
        "candidates": candidates,
    }


def lookup_ontology_context(conn: sqlite3.Connection, question: str, limit: int = 5) -> str:
    terms = extract_query_terms(question)
    where_clause, params = _build_lookup_where_clause(terms)
    params.append(limit)

    rows = conn.execute(
        LOOKUP_QUERY_TEMPLATE.format(where_clause=where_clause),
        params,
    ).fetchall()

    if not rows:
        return "No matching ontology facts found."

    lines: list[str] = []
    for inst_id, cls, label, props in rows:
        lines.append(f"- {inst_id} ({cls}) label='{label}' props=[{props}]")

    qmarks = ",".join("?" for _ in rows)
    rels = conn.execute(
        RELATIONS_BY_IDS_TEMPLATE.format(qmarks=qmarks),
        [r[0] for r in rows],
    ).fetchall()
    if rels:
        lines.append("relations:")
        lines.extend([f"- {s} -[{t}]-> {d}" for s, t, d in rels])

    return "\n".join(lines)


def is_price_question(question: str) -> bool:
    q = question.lower()
    keywords = ("가격", "얼마", "원", "price", "cost", "krw")
    return any(k in q for k in keywords)


def extract_priority_price_fact(conn: sqlite3.Connection, question: str) -> str | None:
    terms = extract_query_terms(question)
    if not terms:
        return None

    where_parts: list[str] = []
    params: list[str] = []
    for term in terms:
        pattern = f"%{term}%"
        where_parts.append(
            """
            lower(i.id) LIKE ?
            OR lower(COALESCE(i.label, '')) LIKE ?
            OR EXISTS (
                SELECT 1 FROM onto_properties p2
                WHERE p2.instance_id = i.id
                AND (lower(p2.key) LIKE ? OR lower(COALESCE(p2.value, '')) LIKE ?)
            )
            """
        )
        params.extend([pattern, pattern, pattern, pattern])

    row = conn.execute(
        PRICE_FACT_QUERY_TEMPLATE.format(
            where_clause=" OR ".join(f"({part})" for part in where_parts)
        ),
        params,
    ).fetchone()

    if not row:
        return None
    inst_id, label, price = row
    if price is None:
        return None
    return f"{label or inst_id}의 가격은 {price}원입니다. (source: price_krw={price})"


def constraint_facts(conn: sqlite3.Connection, limit: int) -> list[str]:
    rows = conn.execute(
        """
        SELECT i.id, COALESCE(i.label, ''), COALESCE(group_concat(p.key || '=' || p.value, '; '), '')
        FROM onto_instances i
        LEFT JOIN onto_properties p ON p.instance_id = i.id
        WHERE lower(i.class_name) IN ('constraint', 'rule', 'policy', 'guardrail')
           OR EXISTS (
                SELECT 1
                FROM onto_properties p2
                WHERE p2.instance_id = i.id
                  AND lower(p2.key) IN ('constraint', 'rule', 'template', 'policy', 'guardrail')
           )
        GROUP BY i.id, i.label
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [f"- {inst_id} label='{label}' props=[{props}]" for inst_id, label, props in rows]


def relation_evidence(
    conn: sqlite3.Connection,
    seed_ids: list[str],
    limit: int,
) -> list[str]:
    if not seed_ids:
        return []
    qmarks = ",".join("?" for _ in seed_ids)
    params: list[Any] = [*seed_ids, *seed_ids, limit]
    rows = conn.execute(
        f"""
        SELECT source_id, type, target_id
        FROM onto_relations
        WHERE source_id IN ({qmarks}) OR target_id IN ({qmarks})
        ORDER BY source_id, type, target_id
        LIMIT ?
        """,
        params,
    ).fetchall()
    return [f"- {source} -[{rel}]-> {target}" for source, rel, target in rows]


def multihop_paths(
    conn: sqlite3.Connection,
    seed_ids: list[str],
    per_hop_limit: int = 12,
) -> list[str]:
    if not seed_ids:
        return []
    qmarks = ",".join("?" for _ in seed_ids)
    first_hop = conn.execute(
        f"""
        SELECT source_id, type, target_id
        FROM onto_relations
        WHERE source_id IN ({qmarks})
        LIMIT ?
        """,
        [*seed_ids, per_hop_limit],
    ).fetchall()
    if not first_hop:
        return []

    targets = list({target for _, _, target in first_hop})
    qmarks2 = ",".join("?" for _ in targets)
    second_hop = conn.execute(
        f"""
        SELECT source_id, type, target_id
        FROM onto_relations
        WHERE source_id IN ({qmarks2})
        LIMIT ?
        """,
        [*targets, per_hop_limit],
    ).fetchall()

    paths: list[str] = []
    second_by_source: dict[str, list[tuple[str, str, str]]] = {}
    for s2, r2, t2 in second_hop:
        second_by_source.setdefault(s2, []).append((s2, r2, t2))
    for s1, r1, t1 in first_hop:
        chained = second_by_source.get(t1, [])
        if not chained:
            paths.append(f"- {s1} -[{r1}]-> {t1}")
            continue
        for _, r2, t2 in chained:
            paths.append(f"- {s1} -[{r1}]-> {t1} -[{r2}]-> {t2}")
    return paths[: per_hop_limit * 2]


def dense_proxy_context(
    conn: sqlite3.Connection,
    question: str,
    limit: int,
) -> tuple[str, dict[str, Any]]:
    tokens = [t for t in extract_query_terms(question) if t and len(t) >= 2]
    rows = conn.execute(
        """
        SELECT i.id, i.class_name, COALESCE(i.label, ''),
               COALESCE(group_concat(p.key || '=' || p.value, '; '), '')
        FROM onto_instances i
        LEFT JOIN onto_properties p ON p.instance_id = i.id
        GROUP BY i.id, i.class_name, i.label
        """
    ).fetchall()
    scored: list[dict[str, Any]] = []
    for inst_id, class_name, label, props in rows:
        text_id = (inst_id or "").lower()
        text_class = (class_name or "").lower()
        text_label = (label or "").lower()
        text_props = (props or "").lower()
        score = 0
        matched: list[str] = []
        for token in tokens:
            hit = False
            if token in text_id:
                score += 3
                hit = True
            if token in text_class:
                score += 1
                hit = True
            if token in text_label:
                score += 5
                hit = True
            if token in text_props:
                score += 2
                hit = True
            if hit:
                matched.append(token)
        if score > 0:
            scored.append(
                {
                    "id": inst_id,
                    "class_name": class_name,
                    "label": label,
                    "props": props,
                    "score": score,
                    "matched_terms": sorted(set(matched)),
                }
            )
    scored.sort(key=lambda item: (-item["score"], item["id"]))
    top = scored[:limit]
    if not top:
        return "No matching ontology facts found.", {"tokens": tokens, "scored_candidates": []}
    lines = [
        f"- {item['id']} ({item['class_name']}) label='{item['label']}' score={item['score']} props=[{item['props']}]"
        for item in top
    ]
    return "\n".join(lines), {"tokens": tokens, "scored_candidates": top}


def enrichment_targets(conn: sqlite3.Connection, limit: int) -> list[dict[str, str]]:
    rows = conn.execute(
        """
        SELECT i.id, COALESCE(i.label, ''), p.key, COALESCE(p.value, '')
        FROM onto_instances i
        JOIN onto_properties p ON p.instance_id = i.id
        WHERE lower(COALESCE(p.value, '')) IN ('', 'unknown', 'todo', 'n/a', '?')
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [
        {"id": inst_id, "label": label, "missing_key": key, "value": value}
        for inst_id, label, key, value in rows
    ]


def lookup_ontology_context_by_method(
    conn: sqlite3.Connection,
    *,
    question: str,
    method_id: str,
    limit: int,
) -> tuple[str, dict[str, Any], dict[str, Any]]:
    base_context = lookup_ontology_context(conn, question, limit=limit)
    base_debug = lookup_ontology_debug(conn, question, limit=limit)
    seed_ids = [item["id"] for item in base_debug.get("candidates", [])[:5] if item.get("id")]
    method_trace: dict[str, Any] = {"method_id": method_id}

    if method_id == "method1":
        method_trace["retrieval_type"] = "lexical-grounding"
        return base_context, base_debug, method_trace

    if method_id == "method2":
        constraints = constraint_facts(conn, limit=max(3, limit // 2))
        method_trace["constraint_count"] = len(constraints)
        context = base_context
        if constraints:
            context = "[Constraint Facts]\n" + "\n".join(constraints) + "\n\n[Entity Facts]\n" + base_context
        return context, {**base_debug, "constraint_hits": constraints}, method_trace

    if method_id == "method3":
        rel_lines = relation_evidence(conn, seed_ids, limit=max(6, limit * 2))
        method_trace["relation_evidence_count"] = len(rel_lines)
        context = base_context
        if rel_lines:
            context = base_context + "\nrelations:\n" + "\n".join(rel_lines)
        return context, {**base_debug, "graph_relations": rel_lines}, method_trace

    if method_id == "method4":
        path_lines = multihop_paths(conn, seed_ids, per_hop_limit=max(6, limit))
        method_trace["multi_hop_path_count"] = len(path_lines)
        context = base_context
        if path_lines:
            context = base_context + "\nreasoning_paths:\n" + "\n".join(path_lines)
        return context, {**base_debug, "reasoning_paths": path_lines}, method_trace

    if method_id == "method5":
        dense_context, dense_debug = dense_proxy_context(conn, question, limit=limit)
        method_trace["retrieval_type"] = "dense-proxy"
        return dense_context, {**base_debug, **dense_debug}, method_trace

    if method_id == "method6":
        dense_context, dense_debug = dense_proxy_context(conn, question, limit=limit)
        constraints = constraint_facts(conn, limit=max(3, limit // 2))
        method_trace["retrieval_type"] = "neuro-symbolic"
        method_trace["constraint_count"] = len(constraints)
        context = dense_context
        if constraints:
            context = "[Symbolic Rules]\n" + "\n".join(constraints) + "\n\n[Neural Retrieval]\n" + dense_context
        return context, {**base_debug, **dense_debug, "constraint_hits": constraints}, method_trace

    if method_id == "method7":
        rel_lines = relation_evidence(conn, seed_ids, limit=max(4, limit))
        method_trace["verification_evidence_count"] = len(rel_lines)
        context = base_context
        if rel_lines:
            context = base_context + "\nvalidation_evidence:\n" + "\n".join(rel_lines)
        return context, {**base_debug, "verification_evidence": rel_lines}, method_trace

    if method_id == "method8":
        targets = enrichment_targets(conn, limit=max(3, limit))
        method_trace["enrichment_target_count"] = len(targets)
        context = base_context
        if targets:
            lines = [
                f"- {row['id']} label='{row['label']}' missing_key={row['missing_key']} value='{row['value']}'"
                for row in targets
            ]
            context = "[Current Facts]\n" + base_context + "\n\n[Missing Property Signals]\n" + "\n".join(lines)
        return context, {**base_debug, "enrichment_targets": targets}, method_trace

    method_trace["retrieval_type"] = "default-lexical"
    return base_context, base_debug, method_trace
