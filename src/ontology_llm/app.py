from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
from typing import Any, Callable

from dotenv import load_dotenv

from ontology_llm.tools.llm_tools import build_client, try_attach_memori
from ontology_llm.tools.method_tools import build_system_prompt, normalize_method_id
from ontology_llm.tools.prompt_tools import (
    TOKEN_WARN_THRESHOLD_DEFAULT,
    compress_ontology_context,
    estimate_prompt_budget,
    get_env_int,
    get_memori_embedding_model,
    get_prompt_budget_mode,
    log_prompt_budget,
)
from ontology_llm.tools.sql_tools import (
    extract_priority_price_fact,
    get_db,
    ingest_ontology_yaml,
    init_schema,
    is_price_question,
    lookup_ontology_context_by_method,
)


def _emit_event(
    on_event: Callable[[dict[str, Any]], None] | None,
    *,
    stage: str,
    status: str,
    message: str,
    input_data: Any | None = None,
    output_data: Any | None = None,
    meta: dict[str, Any] | None = None,
) -> None:
    if on_event is None:
        return
    payload: dict[str, Any] = {
        "event": "stage",
        "stage": stage,
        "status": status,
        "message": message,
    }
    if meta:
        payload["meta"] = meta
    if input_data is not None:
        payload["input"] = input_data
    if output_data is not None:
        payload["output"] = output_data
    on_event(payload)


METHOD_IDS = {
    "method1",
    "method2",
    "method3",
    "method4",
    "method5",
    "method6",
    "method7",
    "method8",
}

METHOD_SYSTEM_PROMPTS: dict[str, str] = {
    "method1": (
        "You are an ontology-grounded assistant using lexical/entity-link retrieval. "
        "Answer from matched ontology facts first."
    ),
    "method2": (
        "You are a policy-constrained ontology assistant. "
        "Always satisfy explicit Constraint/Rule facts before drafting an answer."
    ),
    "method3": (
        "You are a graph-RAG assistant. "
        "Use both node facts and relation evidence and cite relation rationale briefly."
    ),
    "method4": (
        "You are a KG reasoning agent. "
        "Prefer answers supported by explicit multi-hop relation paths."
    ),
    "method5": (
        "You are an embedding-augmented ontology assistant. "
        "Use dense retrieval ranking and explain with top-ranked evidence."
    ),
    "method6": (
        "You are a neuro-symbolic assistant. "
        "Generate naturally, but never violate symbolic constraints."
    ),
    "method7": (
        "You are a verification-first assistant. "
        "Generate candidate answers internally and keep only evidence-validated output."
    ),
    "method8": (
        "You are an ontology enrichment assistant. "
        "Answer safely from current facts and explicitly mark missing ontology properties."
    ),
}


def _normalize_method_id(method_id: str | None) -> str:
    if not method_id:
        return "method1"
    normalized = method_id.strip().lower()
    return normalized if normalized in METHOD_IDS else "method1"


def _constraint_facts(conn, limit: int) -> list[str]:
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


def _relation_evidence(conn, seed_ids: list[str], limit: int) -> list[str]:
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


def _multihop_paths(conn, seed_ids: list[str], per_hop_limit: int = 12) -> list[str]:
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


def _dense_proxy_context(conn, question: str, limit: int) -> tuple[str, dict[str, Any]]:
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


def _enrichment_targets(conn, limit: int) -> list[dict[str, str]]:
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


def _lookup_by_method(
    conn,
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
        constraints = _constraint_facts(conn, limit=max(3, limit // 2))
        method_trace["constraint_count"] = len(constraints)
        context = base_context
        if constraints:
            context = "[Constraint Facts]\n" + "\n".join(constraints) + "\n\n[Entity Facts]\n" + base_context
        return context, {**base_debug, "constraint_hits": constraints}, method_trace

    if method_id == "method3":
        rel_lines = _relation_evidence(conn, seed_ids, limit=max(6, limit * 2))
        method_trace["relation_evidence_count"] = len(rel_lines)
        context = base_context
        if rel_lines:
            context = base_context + "\nrelations:\n" + "\n".join(rel_lines)
        return context, {**base_debug, "graph_relations": rel_lines}, method_trace

    if method_id == "method4":
        path_lines = _multihop_paths(conn, seed_ids, per_hop_limit=max(6, limit))
        method_trace["multi_hop_path_count"] = len(path_lines)
        context = base_context
        if path_lines:
            context = base_context + "\nreasoning_paths:\n" + "\n".join(path_lines)
        return context, {**base_debug, "reasoning_paths": path_lines}, method_trace

    if method_id == "method5":
        dense_context, dense_debug = _dense_proxy_context(conn, question, limit=limit)
        method_trace["retrieval_type"] = "dense-proxy"
        return dense_context, {**base_debug, **dense_debug}, method_trace

    if method_id == "method6":
        dense_context, dense_debug = _dense_proxy_context(conn, question, limit=limit)
        constraints = _constraint_facts(conn, limit=max(3, limit // 2))
        method_trace["retrieval_type"] = "neuro-symbolic"
        method_trace["constraint_count"] = len(constraints)
        context = dense_context
        if constraints:
            context = "[Symbolic Rules]\n" + "\n".join(constraints) + "\n\n[Neural Retrieval]\n" + dense_context
        return context, {**base_debug, **dense_debug, "constraint_hits": constraints}, method_trace

    if method_id == "method7":
        rel_lines = _relation_evidence(conn, seed_ids, limit=max(4, limit))
        method_trace["verification_evidence_count"] = len(rel_lines)
        context = base_context
        if rel_lines:
            context = base_context + "\nvalidation_evidence:\n" + "\n".join(rel_lines)
        return context, {**base_debug, "verification_evidence": rel_lines}, method_trace

    if method_id == "method8":
        targets = _enrichment_targets(conn, limit=max(3, limit))
        method_trace["enrichment_target_count"] = len(targets)
        context = base_context
        if targets:
            lines = [
                f"- {row['id']} label='{row['label']}' missing_key={row['missing_key']} value='{row['value']}'"
                for row in targets
            ]
            context = "[Current Facts]\n" + base_context + "\n\n[Missing Property Signals]\n" + "\n".join(lines)
        return context, {**base_debug, "enrichment_targets": targets}, method_trace

    return base_context, base_debug, method_trace


def run_chat_trace(
    question: str,
    db_path: str,
    on_event: Callable[[dict[str, Any]], None] | None = None,
    method_id: str | None = None,
) -> dict[str, Any]:
    selected_method = _normalize_method_id(method_id)
    normalized_question = question.strip()
    _emit_event(
        on_event,
        stage="received",
        status="running",
        message="질문 접수",
        input_data={"question": question, "method_id": selected_method},
    )
    conn = get_db(db_path)
    max_facts = get_env_int("MAX_ONTOLOGY_FACTS", 5)
    max_relations = get_env_int("MAX_RELATIONS", 3, minimum=0)
    max_context_chars = get_env_int("MAX_CONTEXT_CHARS", 1200)
    budget_mode = get_prompt_budget_mode()
    token_warn_threshold = get_env_int(
        "PROMPT_TOKEN_WARN_THRESHOLD", TOKEN_WARN_THRESHOLD_DEFAULT
    )
    embedding_model = get_memori_embedding_model()
    _emit_event(
        on_event,
        stage="received",
        status="done",
        message="질문 접수 완료",
        output_data={
            "normalized_question": normalized_question,
            "method_id": selected_method,
        },
        meta={"question_chars": len(question)},
    )

    _emit_event(
        on_event,
        stage="lookup",
        status="running",
        message="온톨로지 검색 시작",
        input_data={
            "question": normalized_question,
            "lookup_limit": max(max_facts * 3, max_facts),
            "method_id": selected_method,
        },
    )
    raw_context, lookup_debug, lookup_trace = _lookup_by_method(
        conn,
        question=normalized_question,
        method_id=selected_method,
        limit=max(max_facts * 3, max_facts),
    )
    _emit_event(
        on_event,
        stage="lookup",
        status="done",
        message="온톨로지 검색 완료",
        output_data={
            "raw_context": raw_context,
            "lookup_debug": lookup_debug,
            "method_lookup_trace": lookup_trace,
        },
        meta={"raw_context_chars": len(raw_context)},
    )

    _emit_event(
        on_event,
        stage="compare",
        status="running",
        message="비교/컨텍스트 구성 시작",
        input_data={
            "raw_context_chars": len(raw_context),
            "budget_mode": budget_mode,
            "max_facts": max_facts,
            "max_relations": max_relations,
            "max_context_chars": max_context_chars,
            "method_id": selected_method,
        },
    )
    ontology_context = compress_ontology_context(
        question=normalized_question,
        ontology_context=raw_context,
        max_facts=max_facts,
        max_relations=max_relations,
        max_context_chars=max_context_chars,
        mode=budget_mode,
    )
    price_hint = None
    if is_price_question(normalized_question):
        price_hint = extract_priority_price_fact(conn, normalized_question)

    client, model = build_client()
    memori_attached, memori_status = try_attach_memori(client, db_path)

    system_prompt = METHOD_SYSTEM_PROMPTS.get(
        selected_method,
        METHOD_SYSTEM_PROMPTS["method1"],
    )

    prompt_parts: list[str] = []
    prompt_parts.append(f"[Method]\n{selected_method}")
    if price_hint:
        prompt_parts.append(f"[Priority fact]\n{price_hint}")
    prompt_parts.append(f"[Ontology facts]\n{ontology_context}")
    prompt_parts.append(f"[User question]\n{normalized_question}")
    user_prompt = "\n\n".join(prompt_parts)

    budget = estimate_prompt_budget(
        question=normalized_question,
        ontology_context=ontology_context,
        user_prompt=user_prompt,
        embedding_model=embedding_model,
        token_warn_threshold=token_warn_threshold,
    )
    log_prompt_budget(budget)
    _emit_event(
        on_event,
        stage="compare",
        status="done",
        message="비교/컨텍스트 구성 완료",
        output_data={
            "price_hint": price_hint,
            "ontology_context": ontology_context,
            "user_prompt_preview": user_prompt[:600],
            "method_compare_trace": {
                "method_id": selected_method,
                "candidate_count": len(lookup_debug.get("candidates", [])),
                "has_constraint_hits": bool(lookup_debug.get("constraint_hits")),
                "has_graph_relations": bool(lookup_debug.get("graph_relations")),
                "has_reasoning_paths": bool(lookup_debug.get("reasoning_paths")),
                "has_enrichment_targets": bool(lookup_debug.get("enrichment_targets")),
                "memori_attached": memori_attached,
                "memori_status": memori_status,
            },
        },
        meta={
            "context_chars": len(ontology_context),
            "prompt_tokens": budget.get("user_prompt_tokens"),
        },
    )

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_today_date",
                "description": "Return today's date. Use when user asks about 바나나우유 (or 빠나 우유).",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                    "additionalProperties": False,
                },
            },
        }
    ]

    messages: list[dict[str, object]] = [
        {"role": "system", "content": system_prompt},
        {
            "role": "system",
            "content": "If question mentions 바나나우유 or 빠나 우유, call get_today_date before final answer.",
        },
        {"role": "user", "content": user_prompt},
    ]

    _emit_event(
        on_event,
        stage="generate",
        status="running",
        message="결과 생성 시작",
        input_data={
            "model": model,
            "prompt_preview": user_prompt[:600],
            "tool_enabled": True,
            "method_id": selected_method,
            "memori_attached": memori_attached,
            "memori_status": memori_status,
        },
    )
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools,
        tool_choice="auto",
        temperature=0.2,
    )
    msg = resp.choices[0].message

    if msg.tool_calls:
        messages.append(
            {
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.function.name,
                            "arguments": call.function.arguments,
                        },
                    }
                    for call in msg.tool_calls
                ],
            }
        )

        for call in msg.tool_calls:
            if call.function.name == "get_today_date":
                tool_result = {"today": date.today().isoformat()}
            else:
                tool_result = {"error": f"Unknown function: {call.function.name}"}

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(tool_result, ensure_ascii=False),
                }
            )

        final_resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.2,
        )
        answer = final_resp.choices[0].message.content or ""
        _emit_event(
            on_event,
            stage="generate",
            status="done",
            message="결과 생성 완료",
            output_data={"answer_preview": answer[:600], "tool_calls": True},
        )
        return {"answer": answer, "budget": budget}

    answer = msg.content or ""
    _emit_event(
        on_event,
        stage="generate",
        status="done",
        message="결과 생성 완료",
        output_data={"answer_preview": answer[:600], "tool_calls": False},
    )
    return {"answer": answer, "budget": budget}


def run_chat(question: str, db_path: str, method_id: str | None = None) -> str:
    result = run_chat_trace(question, db_path, method_id=method_id)
    return str(result["answer"])


def main() -> None:
    load_dotenv()
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=os.getenv("LOG_LEVEL", "INFO").strip().upper(),
            format="%(levelname)s %(message)s",
        )

    parser = argparse.ArgumentParser(description="Ontology + Memori + LLM MVP")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init-db", help="Initialize SQLite schema")
    p_init.add_argument("--db", default=os.getenv("SQLITE_PATH", "./data/ontology_memori.db"))

    p_ingest = sub.add_parser("ingest", help="Ingest ontology YAML into SQLite")
    p_ingest.add_argument("--db", default=os.getenv("SQLITE_PATH", "./data/ontology_memori.db"))
    p_ingest.add_argument("--yaml", default="./data/ontology.yaml")

    p_chat = sub.add_parser("chat", help="Ask ontology-aware question")
    p_chat.add_argument("question")
    p_chat.add_argument("--db", default=os.getenv("SQLITE_PATH", "./data/ontology_memori.db"))
    p_chat.add_argument("--method", default="method1", help="method1..method8")

    p_exp = sub.add_parser("exp", help="Run experiment methods under exp/")
    p_exp.add_argument("question", help="User question for experiment")
    p_exp.add_argument("--method", default="all", help="method1..method8 or all")
    p_exp.add_argument("--db", default=os.getenv("SQLITE_PATH", "./data/ontology_memori.db"))
    p_exp.add_argument("--format", default="text", choices=["text", "json"], help="Output format")
    p_exp.add_argument(
        "--auto-ingest",
        action="store_true",
        help="Automatically ingest method-specific ontology before running each method",
    )

    args = parser.parse_args()

    if args.cmd == "init-db":
        Path(args.db).parent.mkdir(parents=True, exist_ok=True)
        conn = get_db(args.db)
        init_schema(conn)
        print(f"Initialized schema at {args.db}")
        return

    if args.cmd == "ingest":
        conn = get_db(args.db)
        init_schema(conn)
        ingest_ontology_yaml(conn, args.yaml)
        print(f"Ingested ontology YAML: {args.yaml} -> {args.db}")
        return

    if args.cmd == "chat":
        answer = run_chat(args.question, args.db, method_id=args.method)
        print(answer)
        return

    if args.cmd == "exp":
        from ontology_llm.exp.controller import run_selected

        results = run_selected(args.question, args.db, args.method, args.auto_ingest)
        if args.format == "json":
            print(json.dumps(results, ensure_ascii=False, indent=2))
            return
        for item in results:
            print(f"[{item['method_id']}] {item['method_name']}")
            print(item["answer"])
            print("-" * 80)
        return


if __name__ == "__main__":
    main()
