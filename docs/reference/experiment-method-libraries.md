# 8개 실험 방법별 라이브러리 정리

## 공통(현재 프로젝트 기본)
- `openai`
- `python-dotenv`
- `PyYAML`
- `sqlalchemy`

## 공통(선택)
- `memori` (`MEMORI_ENABLED=1`일 때만 사용)

## 방법별 필요 라이브러리
1. `method1_keyword_grounding.py`
- 추가 라이브러리 없음 (공통만 사용)

2. `method2_ontology_prompting.py`
- 추가 라이브러리 없음 (공통만 사용)

3. `method3_og_rag.py`
- 추가 라이브러리 없음 (공통만 사용)
- 참고: 본 구현은 경량 OG-RAG 형태(관계 조회 기반)

4. `method4_kg_reasoning_agent.py`
- 추가 라이브러리 없음 (공통만 사용)
- 참고: 본 구현은 경량 경로 추론 프롬프트 방식

5. `method5_ontology_enhanced_embedding.py`
- 추가 라이브러리 없음 (공통만 사용)
- 참고: 본 구현은 토큰 점수 기반 프록시(실제 임베딩 모델 미사용)

6. `method6_neuro_symbolic_hybrid.py`
- 추가 라이브러리 없음 (공통만 사용)

7. `method7_reverse_constraint_reasoning.py`
- 추가 라이브러리 없음 (공통만 사용)

8. `method8_llm_to_ontology.py`
- 추가 라이브러리 없음 (공통만 사용)

## 고급 확장 시 고려 가능한 선택 라이브러리(옵션)
- Graph DB: `neo4j`
- RDF/SPARQL: `rdflib`
- GraphRAG/KG utilities: `networkx`
- 임베딩 로컬 모델: `sentence-transformers`

## Memori 초기화 동작
- 기본값은 `MEMORI_ENABLED=0`으로 비활성입니다.
- `MEMORI_ENABLED=1`일 때에만 `attach_memori()`를 시도합니다.
- 컨트롤러(`controller.py`)로 여러 방법을 한 번에 실행하면,
  공통 베이스 모듈 전역 상태로 memori attach 시도가 최초 1회 수행됩니다.
