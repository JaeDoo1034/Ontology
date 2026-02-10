from __future__ import annotations

METHOD_IDS: tuple[str, ...] = (
    "method1",
    "method2",
    "method3",
    "method4",
    "method5",
    "method6",
    "method7",
    "method8",
)

DEFAULT_METHOD_ID = METHOD_IDS[0]

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

GLOBAL_SYSTEM_GUARD = (
    "Use only the provided ontology facts as the primary evidence. "
    "If evidence is insufficient, explicitly say that ontology evidence is insufficient."
)


def normalize_method_id(method_id: str | None) -> str:
    if not method_id:
        return DEFAULT_METHOD_ID
    normalized = method_id.strip().lower()
    return normalized if normalized in METHOD_IDS else DEFAULT_METHOD_ID


def get_method_system_prompt(method_id: str) -> str:
    return METHOD_SYSTEM_PROMPTS.get(method_id, METHOD_SYSTEM_PROMPTS[DEFAULT_METHOD_ID])


def build_system_prompt(method_id: str) -> str:
    return f"{get_method_system_prompt(method_id)}\n\n{GLOBAL_SYSTEM_GUARD}"
