# Ontology LLM App Flow

아래 다이어그램은 `src/ontology_llm/app.py`의 실행 흐름입니다.

```mermaid
flowchart TD
    A[CLI 시작: main()] --> B[load_dotenv()]
    B --> C[argparse: init-db / ingest / chat]

    C -->|init-db| D[get_db(db_path)]
    D --> E[init_schema(conn)]
    E --> F[출력: Initialized schema]

    C -->|ingest| G[get_db(db_path)]
    G --> H[init_schema(conn)]
    H --> I[ingest_ontology_yaml(conn, yaml_path)]
    I --> J[출력: Ingested ontology YAML]

    C -->|chat| K[run_chat(question, db_path)]
    K --> L[get_db(db_path)]
    L --> M[lookup_ontology_context(conn, question)]
    K --> N[build_client()]
    N -->|LLM_PROVIDER=openai| O[OpenAI(api_key), OPENAI_MODEL]
    N -->|LLM_PROVIDER=local| P[OpenAI(base_url, api_key), LOCAL_MODEL]
    K --> Q[attach_memori(client, db_path)]
    Q --> R[Memori(conn=sqlite3.connect)]
    R --> S[memori.llm.register(client)]
    S --> T[memori.attribution(entity_id, process_id)]
    T --> U[memori.config.storage.build()]
    K --> V[chat.completions.create(...)]
    V --> W[응답 텍스트 반환/출력]
```

## 데이터 흐름 요약
- 온톨로지: YAML -> `ingest_ontology_yaml()` -> SQLite 온톨로지 테이블
- 질의: 질문 -> `lookup_ontology_context()` -> LLM 프롬프트
- 메모리: `attach_memori()` -> SQLite 메모리 테이블/기록
