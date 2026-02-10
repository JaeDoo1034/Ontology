from __future__ import annotations

import logging
import os
import re
from functools import lru_cache
from typing import Any

from ontology_llm.tools.sql_tools import extract_query_terms, is_price_question

logger = logging.getLogger(__name__)
TOKEN_WARN_THRESHOLD_DEFAULT = 220


def get_env_int(name: str, default: int, minimum: int = 1) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw.strip())
    except ValueError:
        return default
    return max(value, minimum)


def get_prompt_budget_mode() -> str:
    mode = os.getenv("PROMPT_BUDGET_MODE", "balanced").strip().lower()
    return mode if mode in {"strict", "balanced"} else "balanced"


def get_memori_embedding_model() -> str:
    return os.getenv("MEMORI_EMBEDDINGS_MODEL", "all-MiniLM-L6-v2").strip()


def dedupe_fact_properties(line: str) -> str:
    marker = "props=["
    start = line.find(marker)
    if start == -1:
        return line
    end = line.rfind("]")
    if end <= start + len(marker):
        return line

    raw = line[start + len(marker) : end]
    props = [p.strip() for p in raw.split(";") if p.strip()]
    deduped = list(dict.fromkeys(props))
    return f"{line[:start]}props=[{'; '.join(deduped)}]{line[end + 1:]}"


def fact_id_from_line(line: str) -> str | None:
    if not line.startswith("- "):
        return None
    payload = line[2:]
    token = payload.split(" ", 1)[0].strip()
    return token or None


def relation_source_from_line(line: str) -> str | None:
    if not line.startswith("- "):
        return None
    payload = line[2:]
    if " -[" not in payload:
        return None
    source = payload.split(" -[", 1)[0].strip()
    return source or None


def compress_ontology_context(
    *,
    question: str,
    ontology_context: str,
    max_facts: int,
    max_relations: int,
    max_context_chars: int,
    mode: str,
) -> str:
    if not ontology_context or ontology_context == "No matching ontology facts found.":
        return ontology_context

    lines = [line.strip() for line in ontology_context.splitlines() if line.strip()]
    fact_lines: list[str] = []
    relation_lines: list[str] = []
    in_relations = False
    for line in lines:
        if line.lower() == "relations:":
            in_relations = True
            continue
        if in_relations:
            relation_lines.append(line)
        else:
            fact_lines.append(dedupe_fact_properties(line))

    if not fact_lines:
        return ontology_context[:max_context_chars] if len(ontology_context) > max_context_chars else ontology_context

    terms = set(extract_query_terms(question))
    price_q = is_price_question(question)

    scored_facts: list[tuple[int, int, str]] = []
    for idx, line in enumerate(fact_lines):
        low = line.lower()
        score = 0
        if price_q and "price_krw=" in low:
            score += 100
        score += sum(1 for t in terms if t and t in low)
        if "alias=" in low:
            score += 2
        if "label='" in low:
            score += 1
        scored_facts.append((score, idx, line))

    scored_facts.sort(key=lambda x: (-x[0], x[1]))
    selected_facts = [line for _, _, line in scored_facts[: max(1, max_facts)]]
    selected_ids = {fact_id_from_line(line) for line in selected_facts}
    selected_ids.discard(None)

    scored_relations: list[tuple[int, int, str]] = []
    for idx, line in enumerate(relation_lines):
        low = line.lower()
        source = relation_source_from_line(line)
        score = 0
        if source in selected_ids:
            score += 10
        score += sum(1 for t in terms if t and t in low)
        scored_relations.append((score, idx, line))
    scored_relations.sort(key=lambda x: (-x[0], x[1]))
    selected_relations = [line for _, _, line in scored_relations[: max(0, max_relations)]]

    if mode == "strict":
        selected_facts = selected_facts[: min(len(selected_facts), 3)]
        selected_relations = selected_relations[: min(len(selected_relations), 1)]

    def render_context(facts: list[str], rels: list[str]) -> str:
        output: list[str] = []
        output.extend(facts)
        if rels:
            output.append("relations:")
            output.extend(rels)
        return "\n".join(output)

    context = render_context(selected_facts, selected_relations)
    while selected_relations and len(context) > max_context_chars:
        selected_relations.pop()
        context = render_context(selected_facts, selected_relations)

    while len(selected_facts) > 1 and len(context) > max_context_chars:
        selected_facts.pop()
        context = render_context(selected_facts, selected_relations)

    if len(context) > max_context_chars:
        if max_context_chars <= 3:
            return context[:max_context_chars]
        return context[: max_context_chars - 3].rstrip() + "..."
    return context


@lru_cache(maxsize=4)
def load_budget_tokenizer(model_name: str) -> tuple[Any | None, str]:
    try:
        from transformers import AutoTokenizer
    except Exception:
        return None, "heuristic(no-transformers)"

    candidates = [model_name]
    if "/" not in model_name:
        candidates.append(f"sentence-transformers/{model_name}")

    for candidate in candidates:
        try:
            tokenizer = AutoTokenizer.from_pretrained(candidate, local_files_only=True)
            return tokenizer, f"hf-local:{candidate}"
        except Exception:
            continue
    return None, "heuristic(regex)"


def estimate_token_len(text: str, embedding_model: str) -> tuple[int, str]:
    tokenizer, source = load_budget_tokenizer(embedding_model)
    if tokenizer is not None:
        try:
            return len(tokenizer.encode(text, add_special_tokens=True)), source
        except Exception:
            pass

    heuristic = len(re.findall(r"[0-9A-Za-z]+|[가-힣]|[^\s]", text))
    return max(1, heuristic), source


def estimate_prompt_budget(
    *,
    question: str,
    ontology_context: str,
    user_prompt: str,
    embedding_model: str,
    token_warn_threshold: int = TOKEN_WARN_THRESHOLD_DEFAULT,
) -> dict[str, Any]:
    q_tokens, source = estimate_token_len(question, embedding_model)
    ctx_tokens, _ = estimate_token_len(ontology_context, embedding_model)
    prompt_tokens, _ = estimate_token_len(user_prompt, embedding_model)
    return {
        "embedding_model": embedding_model,
        "token_source": source,
        "token_warn_threshold": token_warn_threshold,
        "question_chars": len(question),
        "ontology_context_chars": len(ontology_context),
        "user_prompt_chars": len(user_prompt),
        "question_tokens": q_tokens,
        "ontology_context_tokens": ctx_tokens,
        "user_prompt_tokens": prompt_tokens,
        "memori_recall_query_chars_proxy": len(user_prompt),
        "memori_recall_query_tokens_proxy": prompt_tokens,
    }


def log_prompt_budget(metrics: dict[str, Any]) -> None:
    logger.info(
        "PromptBudget model=%s source=%s chars(q=%d ctx=%d prompt=%d) tokens(q=%d ctx=%d prompt=%d) threshold=%d",
        metrics["embedding_model"],
        metrics["token_source"],
        metrics["question_chars"],
        metrics["ontology_context_chars"],
        metrics["user_prompt_chars"],
        metrics["question_tokens"],
        metrics["ontology_context_tokens"],
        metrics["user_prompt_tokens"],
        metrics["token_warn_threshold"],
    )
    threshold = int(metrics["token_warn_threshold"])
    if (
        metrics["question_tokens"] > threshold
        or metrics["ontology_context_tokens"] > threshold
        or metrics["user_prompt_tokens"] > threshold
    ):
        logger.warning(
            "Token budget exceeded (threshold=%d): question=%d, context=%d, prompt=%d",
            threshold,
            metrics["question_tokens"],
            metrics["ontology_context_tokens"],
            metrics["user_prompt_tokens"],
        )
