# 변경로그

## 2026-02-07
- 변경 대상 파일: `pyproject.toml`
  - 변경 내용: `uv` 기반 의존성 관리 구성, `PyYAML`, `sqlalchemy`, `memori`, `openai` 등 의존성 정리
  - 의도/효과: 설치/실행 경로를 일관화하고 Memori 런타임 오류를 방지

- 변경 대상 파일: `src/ontology_llm/app.py`
  - 변경 내용: YAML ingest 도입, Memori attribution API 호환 수정, 토큰 기반 온톨로지 조회, 가격 질문 시 `price_krw` 우선 규칙 추가
  - 의도/효과: 한국어 자연어 질의 적중률 및 가격 응답 일관성 강화

- 변경 대상 파일: `data/ontology.yaml`
  - 변경 내용: 바나나우유 예시 데이터(별칭 `빠나 우유`, 가격 `3000원`, 분류 `우유/사물`) 및 관계 정보 반영
  - 의도/효과: 실제 사용자 질의 시나리오 기반 검증 가능

- 변경 대상 파일: `docs/app-flow.md`
  - 변경 내용: `app.py` 실행 흐름 Mermaid 다이어그램 추가
  - 의도/효과: 코드 구조를 시각적으로 빠르게 파악

- 변경 대상 파일: `docs/how-ontology-feeds-llm.md`
  - 변경 내용: 온톨로지 조회 -> 프롬프트 주입 -> LLM 답변 생성의 데이터 흐름 설명 작성
  - 의도/효과: 채팅 시 동작 원리를 문서로 재사용 가능

- 변경 대상 파일: `docs/reference.md`
  - 변경 내용: Memori/OpenMemory 관련 참고 링크 정리
  - 의도/효과: 조사 출처 재확인 및 후속 확장 참고

- 변경 대상 파일: `docs/history/README.md`, `docs/history/2026-02-07/session.md`, `docs/history/2026-02-07/change-log.md`, `docs/history/2026-02-07/decisions.md`
  - 변경 내용: 히스토리 문서를 일자별 폴더(`YYYY-MM-DD`) 구조로 전환하고 기록 체계를 정리
  - 의도/효과: 세션별 이력 추적과 문서 유지보수 단순화

- 변경 대상 파일: `src/ontology_llm/exp/base.py`, `src/ontology_llm/exp/controller.py`, `src/ontology_llm/exp/method1_keyword_grounding.py`, `src/ontology_llm/exp/method2_ontology_prompting.py`, `src/ontology_llm/exp/method3_og_rag.py`, `src/ontology_llm/exp/method4_kg_reasoning_agent.py`, `src/ontology_llm/exp/method5_ontology_enhanced_embedding.py`, `src/ontology_llm/exp/method6_neuro_symbolic_hybrid.py`, `src/ontology_llm/exp/method7_reverse_constraint_reasoning.py`, `src/ontology_llm/exp/method8_llm_to_ontology.py`
  - 변경 내용: 8개 실험 메서드를 개별 실행 파일로 분리하고 컨트롤러에서 통합 실행 지원
  - 의도/효과: 실험 방법별 독립 실행/비교가 가능하고 확장성이 향상됨

- 변경 대상 파일: `data/ontologies/method1_keyword_grounding.yaml`, `data/ontologies/method2_ontology_prompting.yaml`, `data/ontologies/method3_og_rag.yaml`, `data/ontologies/method4_kg_reasoning_agent.yaml`, `data/ontologies/method5_ontology_enhanced_embedding.yaml`, `data/ontologies/method6_neuro_symbolic_hybrid.yaml`, `data/ontologies/method7_reverse_constraint_reasoning.yaml`, `data/ontologies/method8_llm_to_ontology.yaml`, `data/ontologies/README.md`
  - 변경 내용: method별 실험 목적에 맞는 전용 온톨로지 8종 추가
  - 의도/효과: 동일 질문에 대해 통합 방식별 실험을 재현 가능하게 구성

- 변경 대상 파일: `src/ontology_llm/exp/controller.py`
  - 변경 내용: `--auto-ingest` 옵션 추가, method별 온톨로지 자동 적재/테이블 초기화 로직 추가
  - 의도/효과: 실험 반복 시 수동 ingest 비용 감소 및 실수 방지

- 변경 대상 파일: `src/ontology_llm/app.py`
  - 변경 내용: `exp` 서브커맨드 추가로 메인 실행 엔트리 통합, function calling(`get_today_date`) 추가
  - 의도/효과: `app.py` 중심 실행 체계 확립 및 도구 호출 실험 기능 확장

- 변경 대상 파일: `src/ontology_llm/app.py`
  - 변경 내용: prompt budget 측정(`estimate_prompt_budget`), 경고 로깅, 컨텍스트 압축(`compress_ontology_context`) 및 관련 환경변수 지원 추가
  - 의도/효과: Memori 임베딩 단계의 길이 초과 위험을 사전에 완화하고 원인 분석 지표 확보

- 변경 대상 파일: `.env.example`, `README.md`
  - 변경 내용: `HF_TOKEN`, `MEMORI_EMBEDDINGS_MODEL`, `MAX_ONTOLOGY_FACTS`, `MAX_RELATIONS`, `MAX_CONTEXT_CHARS`, `PROMPT_BUDGET_MODE`, `PROMPT_TOKEN_WARN_THRESHOLD` 안내 추가
  - 의도/효과: 토큰 예산 제어 및 운영 설정 재현성 강화

- 변경 대상 파일: `test/Ontology_token_exceed.md`
  - 변경 내용: 토큰 초과 재현/완화 테스트 시나리오 문서화
  - 의도/효과: 동일 문제를 반복 검증할 수 있는 실행 기준 제공

- 변경 대상 파일: `docs/history/2026-02-07/plans.md`, `docs/history/README.md`, `docs/history/2026-02-07/session.md`
  - 변경 내용: 작업 계획 설명을 별도 문서(`plans.md`)로 통합 기록하고 인덱스/세션 문서에서 링크 연결
  - 의도/효과: 구현 이력과 계획 이력을 분리해 추적성과 가독성 향상

- 변경 대상 파일: `src/ontology_llm/experiments/*` (삭제)
  - 변경 내용: 기존 `experiments` 경로를 `exp` 경로로 재배치 후 레거시 파일 제거
  - 의도/효과: 폴더 구조 단순화 및 실행 경로 혼선 제거

- 변경 대상 파일: `docs/reference/ontology-llm-integration-summary.md`, `docs/reference/experiment-method-libraries.md`, `docs/reference/method-ontology-map.md`, `docs/reference/method-ontology-characteristics.md`, `docs/reference/how-banana-flavor-matches-ontology.md`, `docs/reference.md`
  - 변경 내용: 8개 통합 방식 요약, 라이브러리 목록, method-온톨로지 매핑, 특성 비교표, 바나나맛 우유 매칭 Mermaid 문서 추가/갱신
  - 의도/효과: 실험 설계/학습/운영 참고 문서 체계를 확장
