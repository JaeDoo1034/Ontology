from __future__ import annotations

import argparse

from ontology_llm.exp.base import basic_context, fetch_relations, format_result, llm_answer

METHOD_ID = "method4"
METHOD_NAME = "KG Reasoning Agent"


def run(question: str, db_path: str) -> dict:
    conn, context, _ = basic_context(question, db_path)
    seed_rows = conn.execute(
        "SELECT id FROM onto_instances WHERE lower(label) LIKE '%' || lower(?) || '%' LIMIT 3",
        (question,),
    ).fetchall()
    seeds = [row[0] for row in seed_rows]
    rels = fetch_relations(conn, seeds)
    paths = "\n".join([f"- {s} -> {t} -> {d}" for s, t, d in rels]) or "- no path found"

    system_prompt = "You are a graph reasoning agent. Explain answer with explicit relation paths."
    user_prompt = f"[Seed Nodes]\n{seeds}\n\n[Paths]\n{paths}\n\n[Context]\n{context}\n\n[Question]\n{question}"
    answer = llm_answer(db_path, system_prompt, user_prompt)
    return format_result(METHOD_ID, METHOD_NAME, question, user_prompt, answer)


def main() -> None:
    parser = argparse.ArgumentParser(description=METHOD_NAME)
    parser.add_argument("question")
    parser.add_argument("--db", default="./data/ontology_memori.db")
    args = parser.parse_args()
    result = run(args.question, args.db)
    print(result["answer"])


if __name__ == "__main__":
    main()
