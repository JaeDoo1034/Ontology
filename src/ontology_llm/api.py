from __future__ import annotations

import json
import os
import queue
import threading
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.responses import StreamingResponse

from ontology_llm.app import run_chat, run_chat_trace
from ontology_llm.dashboard_service import build_dashboard_payload
from ontology_llm.tools.sql_tools import get_db, init_schema


class ChatRequest(BaseModel):
    question: str
    db_path: str | None = None
    method_id: str | None = None


class ChatResponse(BaseModel):
    answer: str


load_dotenv()
ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DB = os.getenv("SQLITE_PATH", "./data/ontology_memori.db")

app = FastAPI(title="Ontology LLM API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/dashboard")
def dashboard() -> dict:
    return build_dashboard_payload(ROOT_DIR)


@app.post("/api/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    question = payload.question.strip()
    db_path = payload.db_path or DEFAULT_DB
    if not question:
        return ChatResponse(answer="질문을 입력해주세요.")
    answer = run_chat(question, db_path, method_id=payload.method_id)
    return ChatResponse(answer=answer)


@app.post("/api/chat/stream")
def chat_stream(payload: ChatRequest) -> StreamingResponse:
    question = payload.question.strip()
    db_path = payload.db_path or DEFAULT_DB
    method_id = payload.method_id

    def event_stream():
        if not question:
            yield json.dumps(
                {"event": "error", "message": "질문을 입력해주세요."}, ensure_ascii=False
            ) + "\n"
            return

        q: queue.Queue[dict | object] = queue.Queue()
        sentinel = object()

        def emit(data: dict) -> None:
            q.put(data)

        def worker() -> None:
            try:
                result = run_chat_trace(
                    question,
                    db_path,
                    on_event=emit,
                    method_id=method_id,
                )
                q.put({"event": "answer", "answer": result["answer"]})
                q.put({"event": "done"})
            except Exception as exc:
                q.put({"event": "error", "message": str(exc)})
            finally:
                q.put(sentinel)

        threading.Thread(target=worker, daemon=True).start()

        while True:
            item = q.get()
            if item is sentinel:
                break
            yield json.dumps(item, ensure_ascii=False) + "\n"

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


@app.post("/api/init-db")
def init_db(db_path: str = DEFAULT_DB) -> dict[str, str]:
    resolved = Path(db_path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    conn = get_db(str(resolved))
    init_schema(conn)
    return {"status": "ok", "db_path": str(resolved)}


def run() -> None:
    import uvicorn

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run("ontology_llm.api:app", host=host, port=port, reload=True)


if __name__ == "__main__":
    run()
