from __future__ import annotations

import os
import sqlite3
from typing import Tuple

from openai import OpenAI


def get_env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def build_client() -> tuple[OpenAI, str]:
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    if provider == "local":
        client = OpenAI(
            base_url=get_env("LOCAL_BASE_URL", "http://localhost:11434/v1"),
            api_key=get_env("LOCAL_API_KEY", "local"),
        )
        model = get_env("LOCAL_MODEL", "qwen2.5:3b")
        return client, model

    client = OpenAI(api_key=get_env("OPENAI_API_KEY"))
    model = get_env("OPENAI_MODEL", "gpt-4o-mini")
    return client, model


def _is_truthy(raw: str | None) -> bool:
    if raw is None:
        return False
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def is_memori_enabled() -> bool:
    # Default OFF to avoid external Memori quota dependency.
    return _is_truthy(os.getenv("MEMORI_ENABLED", "0"))


def attach_memori(client: OpenAI, sqlite_path: str) -> None:
    try:
        from memori import Memori
    except ModuleNotFoundError as e:
        missing = e.name or "dependency"
        raise RuntimeError(
            f"Memori dependency missing: {missing}. Run `uv sync` and retry."
        ) from e

    memori = Memori(conn=lambda: sqlite3.connect(sqlite_path))
    memori.llm.register(client)
    memori.attribution(
        entity_id=get_env("ENTITY_ID", "user-001"),
        process_id=get_env("PROCESS_ID", "ontology-agent"),
    )
    memori.config.storage.build()


def try_attach_memori(client: OpenAI, sqlite_path: str) -> Tuple[bool, str]:
    if not is_memori_enabled():
        return False, "disabled"
    try:
        attach_memori(client, sqlite_path)
        return True, "enabled"
    except Exception as exc:  # pragma: no cover - runtime/env dependent
        return False, f"error:{exc}"
