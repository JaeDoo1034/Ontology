# Method별 권장 온톨로지 맵

아래 파일들은 `src/ontology_llm/exp/method1..8` 실험에 맞춰 구성된 샘플 온톨로지입니다.

## 파일 매핑
1. `method1` Keyword Grounding
- 온톨로지: `data/ontologies/method1_keyword_grounding.yaml`
- 특징: alias/keyword 중심 매칭

2. `method2` Ontology-Grounded Prompting
- 온톨로지: `data/ontologies/method2_ontology_prompting.yaml`
- 특징: 규칙 노드(`Constraint`)로 프롬프트 제약 강조

3. `method3` Ontology/Graph RAG
- 온톨로지: `data/ontologies/method3_og_rag.yaml`
- 특징: Product-Brand-Store-Region-Policy 관계 강화

4. `method4` KG Reasoning Agent
- 온톨로지: `data/ontologies/method4_kg_reasoning_agent.yaml`
- 특징: 멀티홉 경로 추론용 그래프

5. `method5` Ontology-Enhanced Embedding
- 온톨로지: `data/ontologies/method5_ontology_enhanced_embedding.yaml`
- 특징: descriptor/동의어 텍스트 확장

6. `method6` Neuro-Symbolic Hybrid
- 온톨로지: `data/ontologies/method6_neuro_symbolic_hybrid.yaml`
- 특징: Rule 노드 + 제약 관계

7. `method7` Reverse Constraint Reasoning
- 온톨로지: `data/ontologies/method7_reverse_constraint_reasoning.yaml`
- 특징: 후보 답 + 검증 제약 노드

8. `method8` LLM -> Ontology Enrichment
- 온톨로지: `data/ontologies/method8_llm_to_ontology.yaml`
- 특징: 결손 속성(`missing_property`) 기반 보강 실험

## 사용 예시

```bash
# 자동 적재 사용(권장): method에 맞는 ontology를 자동 ingest
uv run ontology-llm exp "빠나 우유 가격이 뭐야" --method method3 --auto-ingest

# 전체 8개 순차 실험 + method별 ontology 자동 교체
uv run ontology-llm exp "빠나 우유 가격이 뭐야" --method all --auto-ingest

# 수동 적재가 필요하면 기존 방식도 가능
uv run ontology-llm init-db
uv run ontology-llm ingest --yaml data/ontologies/method3_og_rag.yaml
uv run ontology-llm exp "빠나 우유 가격이 뭐야" --method method3
```
