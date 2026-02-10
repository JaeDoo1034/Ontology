# 작업 계획 기록 - 2026-02-07

이 문서는 2026-02-07에 수립/실행한 주요 작업 계획과 적용 상태를 모아둔 기록입니다.

## 계획 A: Ontology + LLM MVP 구축
- 목적: 온톨로지 기반 응답을 하는 LLM MVP 구성
- 범위:
  - 온톨로지 저장: YAML
  - DB: SQLite
  - LLM: OpenAI + Local(OpenAI-compatible)
  - 메모리: Memori
- 구현 상태: 완료
- 핵심 산출물:
  - `src/ontology_llm/app.py`
  - `data/ontology.yaml`
  - `README.md`

## 계획 B: 실험 프레임워크 분리
- 목적: 8가지 통합 방법을 독립 실행/비교 가능하게 구성
- 범위:
  - `src/ontology_llm/exp/method1..8_*.py`
  - `src/ontology_llm/exp/controller.py`
  - method별 온톨로지 8종
- 구현 상태: 완료
- 핵심 산출물:
  - `src/ontology_llm/exp/*.py`
  - `data/ontologies/method1..8*.yaml`
  - `docs/reference/method-ontology-map.md`

## 계획 C: 실행 구조 단일화
- 목적: `app.py`를 단일 메인 실행 파일로 유지
- 범위:
  - `init-db`, `ingest`, `chat`, `exp` 서브커맨드 제공
  - `exp` 실행을 메인 CLI에서 직접 제어
- 구현 상태: 완료
- 실행 예시:
```bash
uv run ontology-llm exp "빠나 우유 가격이 뭐야" --method method3 --auto-ingest
```

## 계획 D: Memori 토큰 길이 초과 대응
- 목적: 임베딩 길이 초과 경고/실패 위험 완화 + 원인 진단 가능화
- 범위:
  1. 길이 분리 측정
  2. 컨텍스트 예산 압축
  3. 설정 기반 운영 제어
- 구현 상태: 1차 완료

### D-1. 길이 분리 측정
- 적용:
  - `estimate_prompt_budget()`
  - `log_prompt_budget()`
- 기록 항목:
  - question chars/tokens
  - ontology_context chars/tokens
  - user_prompt chars/tokens
- 임계치:
  - `PROMPT_TOKEN_WARN_THRESHOLD` (기본 220)

### D-2. 즉시 완화(컨텍스트 예산)
- 적용:
  - `compress_ontology_context()`
- 제어 변수:
  - `MAX_ONTOLOGY_FACTS`
  - `MAX_RELATIONS`
  - `MAX_CONTEXT_CHARS`
  - `PROMPT_BUDGET_MODE` (`strict|balanced`)
- 우선순위:
  - 가격 질의 시 `price_krw` 우선
  - alias/label 매칭 우선
  - 핵심 relation 우선

### D-3. 운영 설정 보강
- `.env.example` 반영 완료:
  - `HF_TOKEN`
  - `MEMORI_EMBEDDINGS_MODEL`
  - Prompt budget 관련 변수
- 검증 문서:
  - `test/Ontology_token_exceed.md`

## 계획 E: 중기 구조 개선(보류)
- 상태: 보류 (설계만 기록)
- 후보 방향:
  - RAPTOR 계열 계층형 요약 검색
  - GraphRAG 계열 그래프 기반 검색
  - ColBERTv2 계열 재순위화
- 비고:
  - 현재는 애플리케이션 레벨 압축/측정으로 1차 안정화 우선

## 참고 근거(Primary Sources)
- RAG: https://arxiv.org/abs/2005.11401
- ColBERTv2: https://arxiv.org/abs/2112.01488
- Lost in the Middle: https://arxiv.org/abs/2307.03172
- LongLLMLingua: https://arxiv.org/abs/2310.06839
- RAPTOR: https://arxiv.org/abs/2401.18059
- GraphRAG: https://arxiv.org/abs/2404.16130
- Self-RAG: https://arxiv.org/abs/2310.11511
- Sentence-Transformers: https://www.sbert.net/examples/sentence_transformer/applications/computing-embeddings/README.html
