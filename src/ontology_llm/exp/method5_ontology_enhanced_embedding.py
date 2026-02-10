from __future__ import annotations

import argparse

from ontology_llm.exp.base import basic_context, format_result, llm_answer, parse_tokens

METHOD_ID = "method5"
METHOD_NAME = "Ontology-Enhanced Embedding (Token-score proxy)"


def run(question: str, db_path: str) -> dict:
    conn, context, _ = basic_context(question, db_path)
    q_tokens = set(parse_tokens(question))
    rows = conn.execute(
        """
        SELECT i.id, COALESCE(i.label, ''), COALESCE(group_concat(p.value, ' '), '')
        FROM onto_instances i
        LEFT JOIN onto_properties p ON p.instance_id = i.id
        GROUP BY i.id, i.label
        """
    ).fetchall()

    scored = []
    for inst_id, label, values in rows:
        text = f"{inst_id} {label} {values}".lower()
        score = sum(1 for tok in q_tokens if tok in text)
        if score > 0:
            scored.append((score, inst_id, label, values))
    scored.sort(reverse=True)
    top = scored[:5]
    score_text = "\n".join([f"- score={s} id={i} label={l} values={v}" for s, i, l, v in top]) or "- no scored node"

    system_prompt = "You are an assistant that uses ontology-enhanced retrieval scores."
    user_prompt = f"[Scored Nodes]\n{score_text}\n\n[Context]\n{context}\n\n[Question]\n{question}"
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
