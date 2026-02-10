from __future__ import annotations

import argparse

from ontology_llm.exp.base import basic_context, format_result, llm_answer

METHOD_ID = "method8"
METHOD_NAME = "LLM -> Ontology Enrichment"


def run(question: str, db_path: str) -> dict:
    _, context, _ = basic_context(question, db_path)
    system_prompt = (
        "You are an ontology curation assistant. Suggest ontology updates as YAML snippets. "
        "Do not assert facts not implied by given context and question."
    )
    user_prompt = (
        f"[Current Ontology Context]\n{context}\n\n"
        f"[User Question]\n{question}\n\n"
        "[Task]\nPropose optional ontology additions (aliases/properties/relations) in YAML."
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
