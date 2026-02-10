# Memori 토큰 길이 초과 대응 테스트

## 구현 요약
`src/ontology_llm/app.py`에 아래가 반영됨:
- 길이/토큰 측정: `estimate_prompt_budget()`
- 경고 로깅: `log_prompt_budget()`
- 컨텍스트 압축: `compress_ontology_context()`
- 설정 기반 예산 제어:
  - `MAX_ONTOLOGY_FACTS`
  - `MAX_RELATIONS`
  - `MAX_CONTEXT_CHARS`
  - `PROMPT_BUDGET_MODE` (`strict|balanced`)
  - `PROMPT_TOKEN_WARN_THRESHOLD`
- 임베딩 모델 기준 토큰 추정:
  - `MEMORI_EMBEDDINGS_MODEL`
  - 로컬 토크나이저 사용 시 실제 토큰 추정
  - 미가용 시 정규식 기반 heuristic fallback

## 빠른 실행
```bash
uv sync
uv run ontology-llm init-db
uv run ontology-llm ingest --yaml data/ontology.yaml
uv run ontology-llm chat "빠나 우유 가격이 뭐야"
```

## 재현/완화 검증

### 1) 재현 모드(완화 최소화)
```bash
export PROMPT_BUDGET_MODE=balanced
export MAX_ONTOLOGY_FACTS=20
export MAX_RELATIONS=20
export MAX_CONTEXT_CHARS=10000
export PROMPT_TOKEN_WARN_THRESHOLD=220
uv run ontology-llm chat "(긴 질문 또는 긴 온톨로지 상황)"
```

### 2) 완화 모드(권장)
```bash
export PROMPT_BUDGET_MODE=strict
export MAX_ONTOLOGY_FACTS=5
export MAX_RELATIONS=3
export MAX_CONTEXT_CHARS=1200
export PROMPT_TOKEN_WARN_THRESHOLD=220
uv run ontology-llm chat "빠나 우유 가격이 뭐야"
```

### 3) HF 인증 경고 해소
```bash
export HF_TOKEN=...   # 또는 .env에 설정
uv run ontology-llm chat "빠나 우유 가격이 뭐야"
```

## 확인 포인트
- INFO 로그에서 PromptBudget 확인:
  - `chars(q, ctx, prompt)`
  - `tokens(q, ctx, prompt)`
  - `threshold`
- WARNING 로그 발생 조건:
  - `question_tokens`, `ontology_context_tokens`, `user_prompt_tokens` 중 하나라도 threshold 초과

## 참고 근거(Primary Sources)
- RAG: https://arxiv.org/abs/2005.11401
- ColBERTv2: https://arxiv.org/abs/2112.01488
- Lost in the Middle: https://arxiv.org/abs/2307.03172
- LongLLMLingua: https://arxiv.org/abs/2310.06839
- RAPTOR: https://arxiv.org/abs/2401.18059
- GraphRAG: https://arxiv.org/abs/2404.16130
- Self-RAG: https://arxiv.org/abs/2310.11511
- Sentence-Transformers max sequence length:
  https://www.sbert.net/examples/sentence_transformer/applications/computing-embeddings/README.html
