# "바나나맛 우유" 질문이 온톨로지의 "바나나우유"로 매칭되는 흐름

아래는 현재 `src/ontology_llm/app.py` 기준으로, 사용자 질문이 온톨로지 엔티티로 연결되는 과정을 시각화한 다이어그램입니다.

```mermaid
---
id: f9fb53b1-e014-4c6e-aaad-76af0c8c0beb
---
flowchart TD
   A["사용자 질문 입력<br/>\"바나나맛 우유 가격이 뭐야?\""] --> B["run_chat(question, db_path)"]
    B --> C["lookup_ontology_context(conn, question)"]

    C --> D["질문 토큰화<br/>예: 바나나맛, 우유, 가격"]
    D --> E["SQL LIKE 매칭"]
    E --> E1["id/class_name/label 검색"]
    E --> E2["property key/value 검색"]
    E1 --> F["후보 인스턴스 수집"]
    E2 --> F

    F --> G["예: MILK001(label=바나나우유) 매칭"]
    G --> H["관련 property/relations 결합"]
    H --> I["Ontology facts 문자열 생성"]

    B --> J["is_price_question(question)"]
    J --> K["extract_priority_price_fact(conn, question)"]
    K --> L["price_krw=3000 추출 시 Priority fact 생성"]

    I --> M["LLM 프롬프트 구성<br/>[Priority fact] + [Ontology facts] + [User question]"]
    L --> M
    M --> N["OpenAI/Local LLM 호출"]
    N --> O["최종 답변 출력"]
```

## 핵심 포인트
- 매칭은 `lookup_ontology_context()`에서 수행됩니다.
- 질문을 토큰으로 나눈 뒤, `label` + `properties(alias 포함)`를 `LIKE` 조건으로 조회합니다.
- 가격 질문이면 `extract_priority_price_fact()`가 `price_krw`를 우선 추출해 프롬프트 상단에 배치합니다.
- 최종적으로 LLM은 온톨로지에서 검색된 사실을 근거로 답변을 생성합니다.
