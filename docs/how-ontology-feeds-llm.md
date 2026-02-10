# 온톨로지를 읽고 LLM이 답변하는 방식

이 문서는 `src/ontology_llm/app.py` 기준으로, 실제 채팅 시 온톨로지 정보가 어떻게 LLM 답변으로 연결되는지 설명합니다.

## 전체 흐름
1. 사용자가 `uv run ontology-llm chat "질문"`을 실행합니다.
2. `run_chat(question, db_path)`가 호출됩니다.
3. SQLite에서 `lookup_ontology_context()`로 질문 관련 온톨로지 사실을 조회합니다.
4. 가격 질문이면 `extract_priority_price_fact()`가 `price_krw`를 우선 사실로 뽑습니다.
5. OpenAI 또는 Local SLM 클라이언트를 만들고(`build_client()`), Memori를 연결합니다(`attach_memori()`).
6. 프롬프트에 아래 3가지를 함께 넣습니다.
   - `[Priority fact]` (가격 질문일 때만)
   - `[Ontology facts]` (조회된 온톨로지 사실)
   - `[User question]`
7. LLM이 위 컨텍스트를 바탕으로 답변합니다.

## 가격 질문 우선 규칙
- `is_price_question()`이 질문에 `가격`, `얼마`, `원`, `price`, `cost`, `krw` 같은 키워드가 있는지 검사합니다.
- 가격 질문으로 판단되면 `extract_priority_price_fact()`가 `onto_properties.key = 'price_krw'`를 우선 조회합니다.
- 찾은 값은 `[Priority fact]`에 들어가며, system prompt에도 다음 정책이 명시됩니다.
  - "가격 질문이고 `price_krw`가 있으면 그 값을 먼저 답하라"

## 예시: "빠나 우유 가격이 뭐야"
온톨로지(`data/ontology.yaml`)에 다음이 있으면:
- `label: 바나나우유`
- `alias: 빠나 우유`
- `item_type: 우유`
- `category: 사물`
- `price_krw: 3000`

질문 처리 시:
- 별칭(`빠나 우유`)으로 `MILK001`이 매칭되고
- `price_krw=3000`이 우선 사실로 올라가며
- LLM 답변 첫 부분에서 가격(`3000원`)을 먼저 말하도록 유도됩니다.

## 중요한 점
- 현재 구조는 "온톨로지 사실 주입 + LLM 생성" 방식입니다.
- 즉, 답변의 근거는 온톨로지에서 가져오되, 문장 생성은 LLM이 담당합니다.
- 온톨로지에 없는 내용은 불확실하다고 답하도록 system prompt에 정책을 넣어둔 상태입니다.
