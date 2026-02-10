# 우유 리테일 의사결정 온톨로지 Blueprint (Method 특화판)

이 문서는 `method1~method8`의 실험 목적에 맞게 같은 도메인(우유 리테일)을 어떻게 다르게 모델링해야 하는지 정리한 설계 문서입니다.

## 1) 공통 코어 모델
모든 Method에서 공통으로 유지할 최소 축입니다.

- 핵심 클래스: `Product`, `Brand`, `Store`, `Region`
- 공통 속성: `alias`, `price_krw`, `stock`, `category`
- 공통 관계: `made_by`, `sold_at`, `located_in`
- 공통 제품 세트: `BANANA_MILK`, `CHOCOLATE_MILK`, `STRAWBERRY_MILK`, `MELON_MILK`, `WATERMELON_MILK`

## 2) Method별 반영 매트릭스
| Method | 온톨로지 초점 | 필수 추가 요소 | 대표 검증 질문 |
|---|---|---|---|
| method1 | lexical grounding | `alias`, `keyword` 강화 | “빠나 우유 가격 알려줘” |
| method2 | prompt policy | `Constraint`/`rule`/`template` | “가격 규칙에 맞게 답해줘” |
| method3 | graph evidence | `Brand-Store-Region-Policy` 관계 | “왜 이 가격인지 근거 설명해줘” |
| method4 | multi-hop reasoning | `Factory/Hub/Store` 경로 체인 | “생산부터 매장까지 경로 설명해줘” |
| method5 | embedding retrieval | `descriptor`/동의어 확장 텍스트 | “노란 용기 달콤한 우유 가격?” |
| method6 | neuro-symbolic | `Rule` + `constrains`, `stock` 제약 | “가격/재고를 규칙 위반 없이 답해줘” |
| method7 | reverse verification | `CandidateAnswer`, `validates` 제약 | “후보 검증해서 확실한 답만 줘” |
| method8 | ontology enrichment | `QuestionLog`, `missing_property` | “누락 속성 뭐고 어떻게 보강해?” |

## 3) Method별 상세 설계
### method1: Keyword Grounding
- 필수 속성: `alias`, `keyword`, `price_krw`
- 필수 관계: `is_a` 또는 동등한 타입 앵커 관계
- 완료 기준: 표면형 질의(띄어쓰기/별칭 변형)에서도 동일 제품 매칭

### method2: Ontology Prompting
- 필수 클래스: `Constraint`
- 필수 속성: `rule`, `template`
- 필수 관계: `applies_to (Constraint -> Product)`
- 완료 기준: 가격 질문 시 첫 문장에 가격이 나오도록 규칙 반영

### method3: OG-RAG
- 필수 클래스: `Policy`, `Store`, `Region`
- 필수 관계: `made_by`, `sold_at`, `located_in`, `governed_by`
- 완료 기준: 답변에 노드 사실 + 관계 근거를 함께 제시

### method4: KG Reasoning Agent
- 필수 클래스: `Factory`, `LogisticsHub`, `Store`
- 필수 관계: `operates`, `distributed_via`, `supplies` 등 멀티홉 체인
- 완료 기준: 최소 2-hop 이상 경로를 추적 가능한 구조

### method5: Ontology-Enhanced Embedding
- 필수 속성: `descriptor`(다양한 서술), `alias`(영문/한글 변형)
- 필수 관계: `similar_to`(선택, 유사 후보 연결)
- 완료 기준: 키워드가 달라도 의미가 유사하면 후보 검색 가능

### method6: Neuro-Symbolic Hybrid
- 필수 클래스: `Rule`
- 필수 속성: `if`, `then`, `stock`, `price_krw`
- 필수 관계: `constrains (Rule -> Product)`
- 완료 기준: 생성 결과가 규칙 위반 시 수정 가능한 근거 보유

### method7: Reverse Constraint Reasoning
- 필수 클래스: `CandidateAnswer`, `Constraint`
- 필수 관계: `validates`, `grounded_on`
- 완료 기준: 후보 답안과 실제 사실(`price_krw`) 대조 검증 가능

### method8: LLM -> Ontology Enrichment
- 필수 클래스: `QuestionLog`
- 필수 속성: `needs_enrichment`, `missing_property`, `suggested_new_alias`
- 필수 관계: `refers_to`, `suggests_update_for`
- 완료 기준: 질의 로그 기반 보강 후보를 자동 도출 가능

## 4) 데이터 볼륨 권장(1차)
- Product: 20~30
- Store: 5~10
- Region: 3~5
- Rule/Constraint/Policy: 10+
- QuestionLog: 50+
- Relations: 150~300

## 5) 구현 파일
- Method 독립 베이스: `data/ontologies/milk_retail_blueprint.yaml`
- Method 전용 파일: `data/ontologies/method1_*.yaml` ~ `method8_*.yaml`

적재:
```bash
uv run ontology-llm init-db
uv run ontology-llm ingest --yaml data/ontologies/milk_retail_blueprint.yaml
```

## 6) 운영 체크리스트
1. 신규 제품 추가 시 `alias + price_krw + stock` 최소 3종 속성 입력
2. Method2/6/7은 규칙 노드 누락 여부 우선 점검
3. Method3/4는 끊긴 경로(고립 노드) 여부 점검
4. Method8은 `QuestionLog`와 `missing_property` 갱신 주기 설정
