# 세션 기록 - 2026-02-07

## 목표
- 온톨로지를 활용하는 LLM MVP를 구성하고, Memori(SQL 네이티브 메모리 계층)를 통합한다.
- 스택을 `Ontology + SQLite + OpenAI/Local SLM + Memori + uv`로 정리한다.
- 실제 예시 질문("빠나 우유 가격이 뭐야")이 온톨로지 기반으로 동작하도록 맞춘다.

## 요청 흐름 타임라인
1. 온톨로지 기반 LLM 구현 방향 요청 및 Memori 사용 의도 확인
2. 프로젝트 초기 골격 생성 및 `uv` 기반 패키지 관리로 전환
3. 온톨로지 포맷을 XML에서 YAML로 변경
4. Memori 연동 중 `sqlalchemy` 누락/호환 이슈 해결
5. `app.py` 흐름 Mermaid 문서화 (`docs/app-flow.md`)
6. 온톨로지-LLM 연결 설명 문서화 (`docs/how-ontology-feeds-llm.md`)
7. "빠나 우유" 예시 온톨로지 반영 및 가격 우선 답변 규칙 추가
8. 히스토리 문서를 `docs/history/YYYY-MM-DD/` 일자 폴더 구조로 재정리
9. 8가지 통합 방식 요약 문서 및 레퍼런스 문서 묶음 확장
10. 8개 실험 메서드를 개별 파일로 분리하고 컨트롤러 추가
11. method별 전용 온톨로지(`data/ontologies/method1..8.yaml`) 구성
12. 컨트롤러 `--auto-ingest` 도입(메서드별 온톨로지 자동 적재)
13. `app.py`를 단일 메인 실행 파일로 재정렬하고 `exp` 서브커맨드 통합
14. `바나나우유` 질문 시 오늘 날짜를 반환하는 function calling 기능 추가
15. Memori 토큰 길이 초과 대응(길이 측정/경고 로깅/컨텍스트 예산 압축) 적용

## 주요 구현 결과
- 런타임/패키지
  - `uv` 기반 프로젝트 구성(`pyproject.toml`, `uv.lock`)
  - OpenAI + Local(OpenAI-compatible) 분기 지원
- 온톨로지/DB
  - YAML 온톨로지 적재 로직 구현 (`ingest_ontology_yaml`)
  - SQLite 스키마/적재/조회 흐름 정리
- 메모리 계층
  - Memori를 OpenAI client에 등록해 대화 메모리 기록
  - `memori.attribution(...)` 호출 방식으로 API 호환 수정
- 검색/응답 품질
  - 질문 토큰 기반 매칭으로 한국어 질의 매칭 강화
  - 가격 질문 시 `price_krw`를 우선 사실로 추출해 프롬프트에 우선 주입
  - `바나나우유/빠나 우유` 질의 시 function calling(`get_today_date`) 연동
  - 프롬프트 길이 예산(`MAX_ONTOLOGY_FACTS`, `MAX_RELATIONS`, `MAX_CONTEXT_CHARS`) 기반 컨텍스트 압축
  - 임베딩 모델 기준 토큰 추정 및 임계치(`PROMPT_TOKEN_WARN_THRESHOLD`) 경고 로깅
- 도메인 예시
  - `data/ontology.yaml`에 바나나우유(별칭: 빠나 우유, 가격: 3000원, 분류: 우유/사물) 반영
- 실험 프레임워크
  - `src/ontology_llm/exp/` 하위에 8개 실험 실행 파일 구성
  - `src/ontology_llm/exp/controller.py`에서 단건/전체 실험 및 `--auto-ingest` 지원
  - 공통 모듈(`src/ontology_llm/exp/base.py`)에서 Memori 최초 1회 초기화 보장
- 실험 데이터
  - `data/ontologies/`에 method별 특화 온톨로지 8종 구성
- 문서 체계
  - `docs/reference/`에 방법별 라이브러리, 온톨로지 맵, 특성 비교, 매칭 흐름 문서 추가
  - 히스토리 문서를 `docs/history/2026-02-07/` 하위로 일자별 정리

## 이슈와 해결
- 이슈: `ModuleNotFoundError: No module named 'sqlalchemy'`
  - 해결: 의존성에 SQLAlchemy 추가 및 `uv sync` 반영
- 이슈: Memori attribution API 호출 오류 (`AttributeError`)
  - 해결: 체이닝 호출 대신 `memori.attribution(entity_id=..., process_id=...)`로 수정
- 이슈: 질문 전체 문자열 매칭만으로는 자연어 질의 적중률 낮음
  - 해결: 토큰 기반 검색 조건으로 확장
- 이슈: 실행 진입점이 분산되어 `app.py` 메인 중심 구조 요구
  - 해결: `app.py`에 `exp` 서브커맨드를 추가하고 실험 실행을 메인 엔트리로 통합
- 이슈: 메서드별 온톨로지 적재를 수동으로 할 때 실험 반복 비용 증가
  - 해결: 컨트롤러에 `--auto-ingest` 옵션 추가해 메서드별 YAML 자동 적재
- 이슈: Memori 임베딩 단계에서 입력 길이 초과 경고 발생
  - 해결: prompt budget 측정/압축 로직 도입 및 토큰 임계치 경고 체계 추가

## 현재 상태
- YAML 온톨로지 기반 ingest/chat 동작 가능
- 가격 질문의 경우 `price_krw` 우선 답변 유도 가능
- `app.py` 메인에서 `init-db/ingest/chat/exp` 서브커맨드로 실행 가능
- `src/ontology_llm/exp/` 기반 8개 실험 실행 구조 운영 중
- method별 전용 온톨로지(`data/ontologies/method1..8.yaml`) 준비 완료
- `.env.example`에 HF/Memori/Prompt budget 관련 설정 템플릿 반영
- 흐름도/설명 문서가 분리되어 존재함
  - [앱 흐름도](../../app-flow.md)
  - [온톨로지-LLM 동작 설명](../../how-ontology-feeds-llm.md)
  - [8개 방법별 요약](../../reference/ontology-llm-integration-summary.md)
  - [Method-온톨로지 매핑](../../reference/method-ontology-map.md)
  - [온톨로지 형태별 특징 비교](../../reference/method-ontology-characteristics.md)
  - [바나나맛 우유 매칭 흐름](../../reference/how-banana-flavor-matches-ontology.md)
- 계획 문서가 분리되어 존재함
  - [작업 계획 기록](./plans.md)

## 다음 액션
1. function calling 결과(오늘 날짜)의 출력 포맷 고정 여부 결정
2. method별 자동 ingest 로그(현재 로딩된 YAML 표시) 추가
3. 토큰 예산 측정치를 실험 리포트(JSON)로 저장하는 자동화 추가
