from __future__ import annotations

import argparse
import json
import os
from collections import OrderedDict
from pathlib import Path

from dotenv import load_dotenv

from ontology_llm.tools.sql_tools import get_db, ingest_ontology_yaml, init_schema
from ontology_llm.exp import (
    method1_keyword_grounding,
    method2_ontology_prompting,
    method3_og_rag,
    method4_kg_reasoning_agent,
    method5_ontology_enhanced_embedding,
    method6_neuro_symbolic_hybrid,
    method7_reverse_constraint_reasoning,
    method8_llm_to_ontology,
)

METHODS = OrderedDict(
    [
        ("method1", method1_keyword_grounding),
        ("method2", method2_ontology_prompting),
        ("method3", method3_og_rag),
        ("method4", method4_kg_reasoning_agent),
        ("method5", method5_ontology_enhanced_embedding),
        ("method6", method6_neuro_symbolic_hybrid),
        ("method7", method7_reverse_constraint_reasoning),
        ("method8", method8_llm_to_ontology),
    ]
)


ONTOLOGY_MAP = {
    "method1": "data/ontologies/method1_keyword_grounding.yaml",
    "method2": "data/ontologies/method2_ontology_prompting.yaml",
    "method3": "data/ontologies/method3_og_rag.yaml",
    "method4": "data/ontologies/method4_kg_reasoning_agent.yaml",
    "method5": "data/ontologies/method5_ontology_enhanced_embedding.yaml",
    "method6": "data/ontologies/method6_neuro_symbolic_hybrid.yaml",
    "method7": "data/ontologies/method7_reverse_constraint_reasoning.yaml",
    "method8": "data/ontologies/method8_llm_to_ontology.yaml",
}


def reset_ontology_tables(db_path: str) -> None:
    conn = get_db(db_path)
    conn.execute("DELETE FROM onto_relations")
    conn.execute("DELETE FROM onto_properties")
    conn.execute("DELETE FROM onto_instances")
    conn.execute("DELETE FROM onto_classes")
    conn.commit()


def auto_ingest_for_method(method_key: str, db_path: str) -> None:
    ontology_path = ONTOLOGY_MAP.get(method_key)
    if not ontology_path:
        raise ValueError(f"No ontology mapping for method: {method_key}")
    if not Path(ontology_path).exists():
        raise FileNotFoundError(f"Ontology file not found: {ontology_path}")

    conn = get_db(db_path)
    init_schema(conn)
    reset_ontology_tables(db_path)
    ingest_ontology_yaml(conn, ontology_path)


def run_selected(question: str, db_path: str, method_key: str | None, auto_ingest: bool) -> list[dict]:
    if method_key and method_key != "all":
        if method_key not in METHODS:
            raise ValueError(f"Unknown method: {method_key}. Use one of: {', '.join(METHODS.keys())}, all")
        if auto_ingest:
            auto_ingest_for_method(method_key, db_path)
        return [METHODS[method_key].run(question, db_path)]

    results: list[dict] = []
    for key, module in METHODS.items():
        if auto_ingest:
            auto_ingest_for_method(key, db_path)
        results.append(module.run(question, db_path))
    return results


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Run ontology-LLM integration experiments")
    parser.add_argument("question", help="User question for experiment")
    parser.add_argument(
        "--method",
        default="all",
        help="method1..method8 or all",
    )
    parser.add_argument("--db", default=os.getenv("SQLITE_PATH", "./data/ontology_memori.db"))
    parser.add_argument(
        "--format",
        default="text",
        choices=["text", "json"],
        help="Output format",
    )
    parser.add_argument(
        "--auto-ingest",
        action="store_true",
        help="Automatically ingest method-specific ontology before running each method",
    )
    args = parser.parse_args()

    results = run_selected(args.question, args.db, args.method, args.auto_ingest)

    if args.format == "json":
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return

    for item in results:
        print(f"[{item['method_id']}] {item['method_name']}")
        print(item["answer"])
        print("-" * 80)


if __name__ == "__main__":
    main()
