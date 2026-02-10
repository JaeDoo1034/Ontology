from __future__ import annotations

import argparse

from ontology_llm.exp.base import basic_context, format_result, llm_answer

METHOD_ID = "method3"
METHOD_NAME = "Ontology/Graph RAG"


def run(question: str, db_path: str) -> dict:
    conn, context, _ = basic_context(question, db_path)
    rows = conn.execute(
        """
        SELECT source_id, type, target_id
        FROM onto_relations
        ORDER BY source_id, type, target_id
        LIMIT 20
        """
    ).fetchall()
    rel_text = "\n".join([f"- {s} -[{t}]-> {d}" for s, t, d in rows]) or "- (none)"

    system_prompt = "You are a retrieval-augmented assistant grounded on ontology graph structure."
    user_prompt = (
        f"[Node Retrieval]\n{context}\n\n"
        f"[Graph Retrieval]\n{rel_text}\n\n"
        f"[Question]\n{question}"
    )
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
