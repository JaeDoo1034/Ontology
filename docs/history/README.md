# 히스토리 문서 가이드

`docs/history`는 대화/구현 히스토리를 **일자별 폴더**로 누적 관리합니다.

## 폴더 구조
- `docs/history/YYYY-MM-DD/`
  - `session.md`: 해당 일자 세션 요약
  - `change-log.md`: 해당 일자 파일/기능 변경점
  - `decisions.md`: 해당 일자 주요 의사결정
  - `plans.md`: 해당 일자 작업 계획/설계 기록

## 신규 일자 기록 규칙
1. 날짜 폴더 생성: `docs/history/YYYY-MM-DD`
2. 아래 3개 파일 생성
   - `session.md`
   - `change-log.md`
   - `decisions.md`
3. `session.md`는 아래 섹션 순서를 유지
   1. `## 목표`
   2. `## 요청 흐름 타임라인`
   3. `## 주요 구현 결과`
   4. `## 이슈와 해결`
   5. `## 현재 상태`
   6. `## 다음 액션`

## 업데이트 순서
1. `session.md` 갱신
2. `change-log.md` 갱신
3. `decisions.md` 갱신

## 일자 인덱스
- [2026-02-07](./2026-02-07/session.md)
  - [change-log](./2026-02-07/change-log.md)
  - [decisions](./2026-02-07/decisions.md)
  - [plans](./2026-02-07/plans.md)

## 변경 하이라이트
### 2026-02-07
- `app.py`를 메인 실행 엔트리로 통합하고 `exp` 서브커맨드 추가
- `src/ontology_llm/exp/` 하위 8개 실험 실행 파일 + 컨트롤러 구성
- method별 온톨로지 8종(`data/ontologies/method1..8.yaml`) 추가
- `--auto-ingest`로 method별 온톨로지 자동 적재 지원
- 바나나우유 질의에 function calling(`get_today_date`) 연동
- `docs/reference/`에 실험/구조 설명 문서 확장

## 연계 문서
- [앱 실행 흐름도](../app-flow.md)
- [온톨로지-LLM 동작 설명](../how-ontology-feeds-llm.md)
- [참고자료](../reference.md)
