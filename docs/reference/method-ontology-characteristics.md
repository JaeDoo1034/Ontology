# 8개 온톨로지 형태별 특징 비교

## 한눈에 보는 비교표
| 방법 | 파일 | 핵심 모델링 포인트 | 논문 근거 | 추천 질문 유형 |
|---|---|---|---|---|
| Method1 Keyword Grounding | `data/ontologies/method1_keyword_grounding.yaml` | `alias`/표면형 중심 entity linking + lexical 매칭 | DBpedia Spotlight (2011) | "빠나 우유 가격"처럼 명시적 키워드 질의 |
| Method2 Ontology Prompting | `data/ontologies/method2_ontology_prompting.yaml` | `Constraint` 노드를 prompt guardrail로 사용 | Constitutional AI (2022) | 포맷/우선순위가 중요한 질의 |
| Method3 OG-RAG | `data/ontologies/method3_og_rag.yaml` | 노드 검색 + relation evidence(GraphRAG) 결합 | RAG (2020), GraphRAG (2024) | "어디서/왜 그 가격인지" 맥락 질의 |
| Method4 KG Reasoning Agent | `data/ontologies/method4_kg_reasoning_agent.yaml` | ReAct 기반 멀티홉 경로 탐색/검증 | ReAct (2023), Think-on-Graph (2023) | "제조/유통 경로" 같은 다단계 질의 |
| Method5 Ontology-Enhanced Embedding | `data/ontologies/method5_ontology_enhanced_embedding.yaml` | `descriptor`/동의어 확장 + dense retrieval | Sentence-BERT (2019), DPR (2020) | 표현이 다양한 유사 질의 |
| Method6 Neuro-Symbolic Hybrid | `data/ontologies/method6_neuro_symbolic_hybrid.yaml` | 신경망 생성 결과를 symbolic rule로 교정 | MRKL Systems (2022) | 가격/재고 같이 제약이 있는 질의 |
| Method7 Reverse Constraint Reasoning | `data/ontologies/method7_reverse_constraint_reasoning.yaml` | 후보 답 생성 후 역검증(CoVe) | Chain-of-Verification (2023) | 정답 검증이 중요한 고신뢰 질의 |
| Method8 LLM to Ontology | `data/ontologies/method8_llm_to_ontology.yaml` | 결손 속성 탐지 + 보강 제안 생성 | LLMs4OL (2023) | "어떤 속성을 더 추가할지" 설계 질의 |

## 구조적 차이 요약
- **검색 최적화형**: Method1, Method5
- **규칙/정책 최적화형**: Method2, Method6, Method7
- **관계/경로 추론형**: Method3, Method4
- **지식 확장형**: Method8

## 실험 설계 팁
1. MVP 1차: `method1` + `method2`
2. 근거/관계 강화: `method3` + `method4`
3. 품질 안정화: `method6` + `method7`
4. 운영 중 확장: `method8`

## 현재 프로젝트 기준 권장 순서
1. `method1`으로 alias/keyword 품질 점검
2. `method2`로 답변 정책 고정(가격 우선 등)
3. `method3`/`method4`로 관계형 질의 확장
4. `method6`/`method7`로 오류 억제
5. `method8`로 온톨로지 유지보수 자동화

## 논문 링크
- DBpedia Spotlight: https://doi.org/10.1145/2063518.2063519
- Constitutional AI: https://arxiv.org/abs/2212.08073
- RAG: https://arxiv.org/abs/2005.11401
- GraphRAG: https://arxiv.org/abs/2404.16130
- ReAct: https://arxiv.org/abs/2210.03629
- Think-on-Graph: https://arxiv.org/abs/2307.07697
- Sentence-BERT: https://arxiv.org/abs/1908.10084
- Dense Passage Retrieval: https://arxiv.org/abs/2004.04906
- MRKL Systems: https://arxiv.org/abs/2205.00445
- Chain-of-Verification: https://arxiv.org/abs/2309.11495
- LLMs4OL: https://arxiv.org/abs/2307.16648
