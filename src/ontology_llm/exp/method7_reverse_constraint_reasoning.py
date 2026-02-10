from __future__ import annotations

import argparse

from ontology_llm.exp.base import basic_context, format_result, llm_answer

METHOD_ID = "method7"
METHOD_NAME = "Reverse Constraint Reasoning"


def run(question: str, db_path: str) -> dict:
    _, context, price_hint = basic_context(question, db_path)

    system_prompt = (
        "Generate 2 candidate answers, then validate candidates against ontology facts. "
        "Output only validated final answer."
    )
    constraint = price_hint or "No hard numeric constraint available."
    user_prompt = (
        f"[Ontology Constraint]\n{constraint}\n\n"
        f"[Ontology Context]\n{context}\n\n"
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
