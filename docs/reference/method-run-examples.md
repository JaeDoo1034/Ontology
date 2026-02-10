# Method별 대표 예시 실행 가이드

아래 질문은 현재 `data/ontologies/method1..8_*.yaml` 기준으로 바로 테스트 가능한 대표 예시입니다.

## 빠른 내부 세팅(권장)
```bash
./scripts/setup_method_examples.sh
```

## Method별 대표 질문
| Method | 대표 질문 예시 | 기대 관찰 포인트 |
|---|---|---|
| method1 | 빠나 우유 가격 알려줘 | alias/label lexical 매칭으로 `price_krw`를 우선 반환 |
| method2 | 바나나우유 가격을 규칙에 맞는 문장으로 답해줘 | Constraint/Policy 규칙을 적용해 가격 우선 문장 생성 |
| method3 | 빠나 우유가 왜 3000원인지 관계 근거까지 설명해줘 | Product-Store-Policy relation evidence를 함께 제시 |
| method4 | 빠나 우유가 생산부터 강남 매장까지 오는 경로를 설명해줘 | 멀티홉 경로 추론 trace(브랜드-공장-허브-매장) |
| method5 | 노란 용기 달콤한 바나나 향 우유 가격 알려줘 | descriptor 기반 유사도 검색 후 후보 재정렬 |
| method6 | 빠나 우유 가격과 재고를 규칙 위반 없이 자연스럽게 답해줘 | 생성 결과를 rule/constraint로 검증해 위반 교정 |
| method7 | 후보 답을 검증해서 빠나 우유 가격을 가장 확실하게 알려줘 | 후보 생성 후 검증(CoVe)으로 저신뢰 후보 탈락 |
| method8 | 빠나 우유에 누락된 속성이 뭐고 어떻게 보강하면 좋아? | missing_property 기반 ontology 보강 제안 |

## CLI 실행 예시
```bash
# 단일 Method 실행
uv run ontology-llm chat "빠나 우유 가격 알려줘" --method method1

# method3 (관계 근거형)
uv run ontology-llm chat "빠나 우유가 왜 3000원인지 관계 근거까지 설명해줘" --method method3

# method8 (보강 제안형)
uv run ontology-llm chat "빠나 우유에 누락된 속성이 뭐고 어떻게 보강하면 좋아?" --method method8
```

## 대시보드(UI) 실행 방법
1. 좌측에서 Method 선택
2. 우측 `대표 예시 시나리오`에서 예시 질문 버튼 클릭
3. `대표 예시 바로 실행` 또는 `질문 실행` 클릭
4. `필수 세팅 점검` 배지에서 의존성/환경변수 준비 상태 확인
