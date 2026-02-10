# Ontology + LLM MVP (uv)

구성:
- Ontology: YAML (`data/ontology.yaml`)
- DB: SQLite (`data/ontology_memori.db`)
- Memory layer: optional `memori` (`MEMORI_ENABLED=1`일 때만 사용)
- LLM: OpenAI 또는 Local(OpenAI-compatible endpoint)

## 1) uv 환경 준비

```bash
uv venv
source .venv/bin/activate
uv sync
```

`memori`까지 함께 쓰려면(선택):

```bash
uv sync --extra memori
```

논문 기반 Method 확장 도구 설치(선택):

```bash
# method3/4 (GraphRAG, KG reasoning)
uv sync --extra method34

# method5 (Embedding retrieval)
uv sync --extra method5

# method6/7/8 (Neuro-symbolic, verification, ontology enrichment)
uv sync --extra method678

# method3~8 전체 연구 스택
uv sync --extra research-all
```

## 2) 환경변수 설정

```bash
cp .env.example .env
# .env에서 OPENAI_API_KEY 또는 LOCAL_* 설정
```

선택/권장 설정:
- `MEMORI_ENABLED`: `0`(기본, 비활성) / `1`(활성)
- `HF_TOKEN`: Hugging Face 인증(다운로드 속도/한도 개선)
- `MEMORI_EMBEDDINGS_MODEL`: Memori 임베딩 모델 지정
- `MAX_ONTOLOGY_FACTS`, `MAX_RELATIONS`, `MAX_CONTEXT_CHARS`: 온톨로지 컨텍스트 예산
- `PROMPT_BUDGET_MODE`: `strict` 또는 `balanced`
- `PROMPT_TOKEN_WARN_THRESHOLD`: 경고 임계치(기본 220)

## 3) DB 초기화 + 온톨로지 적재

```bash
uv run ontology-llm init-db
uv run ontology-llm ingest --yaml ./data/ontology.yaml
```

## 4) 질의

```bash
uv run ontology-llm chat "Starter Plan 환불 정책 알려줘"
```

## 5) 실험 실행(`app.py` 메인 + `exp` 서브커맨드)

```bash
# 특정 방법 1개 실행
uv run ontology-llm exp "빠나 우유 가격이 뭐야" --method method3 --auto-ingest

# 8개 방법 전체 실행
uv run ontology-llm exp "빠나 우유 가격이 뭐야" --method all --auto-ingest
```

Method별 대표 예시 + 내부 세팅 자동화:

```bash
./scripts/setup_method_examples.sh
```

대표 예시 목록 문서:
- `docs/reference/method-run-examples.md`

## 6) 웹 테스트 화면(FastAPI + React)

백엔드(FastAPI):

```bash
uv run ontology-api
```

프론트엔드(React/Vite):

```bash
cd frontend
npm install
npm run dev
```

접속:
- 프론트엔드: `http://localhost:5173`
- 백엔드 API: `http://localhost:8000`

웹 화면에서 바로 확인 가능한 항목:
1. 온톨로지 활용 방식 시각화
   - Method 선택 기반 DAG(온톨로지 접근 + 질의 비교 경로)
2. 온톨로지 유형별 테스트 현황
3. 최대 토큰 한도 대응 단계별 현황

## OpenAI 사용

`.env`:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4o-mini
```

## Local SLM 사용 (예: Ollama OpenAI 호환 엔드포인트)

`.env`:

```env
LLM_PROVIDER=local
LOCAL_BASE_URL=http://localhost:11434/v1
LOCAL_API_KEY=local
LOCAL_MODEL=qwen2.5:3b
```

## 참고
- `MEMORI_ENABLED=0`이면 memori 없이 동작합니다(기본).
- `MEMORI_ENABLED=1`이면 memori를 OpenAI client에 등록해 대화 기록을 저장합니다.
- 온톨로지 매칭은 현재 키워드 기반 MVP이며, 추후 임베딩/그래프 추론으로 확장 가능합니다.
