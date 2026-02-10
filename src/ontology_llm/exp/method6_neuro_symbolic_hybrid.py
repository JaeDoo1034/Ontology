from __future__ import annotations

import argparse

from ontology_llm.exp.base import basic_context, format_result, llm_answer

METHOD_ID = "method6"
METHOD_NAME = "Neuro-Symbolic Hybrid"


def run(question: str, db_path: str) -> dict:
    _, context, price_hint = basic_context(question, db_path)
    symbolic_section = price_hint or "No deterministic symbolic fact found."

    system_prompt = (
        "You combine symbolic constraints and natural-language generation. "
        "Always keep symbolic facts unchanged."
    )
    user_prompt = (
        f"[Symbolic Constraint]\n{symbolic_section}\n\n"
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
