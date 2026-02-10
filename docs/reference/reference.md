# Ontology-LLM Method References

프로젝트의 `method1`~`method8` 설계에 사용한 근거 논문/문서를 정리합니다.  
Method별 상세 설명은 `docs/reference/method-ontology-characteristics.md`를 함께 참고합니다.

## Method별 근거 매핑
| Method | 접근 방식 | 핵심 근거 |
|---|---|---|
| method1 | Keyword Grounding / Surface-form Entity Linking | DBpedia Spotlight (2011) |
| method2 | Ontology Prompting / Rule-guarded Generation | Constitutional AI (2022) |
| method3 | OG-RAG / Graph-aware Retrieval | RAG (2020), GraphRAG (2024) |
| method4 | KG Reasoning Agent / Multi-hop Path Reasoning | ReAct (2023), Think-on-Graph (2023) |
| method5 | Ontology-Enhanced Embedding | Sentence-BERT (2019), DPR (2020) |
| method6 | Neuro-Symbolic Hybrid | MRKL Systems (2022) |
| method7 | Reverse Constraint Reasoning / Self-verification | Chain-of-Verification (2023) |
| method8 | LLM-to-Ontology Enrichment | LLMs4OL (2023) |

## Reference List
1. DBpedia Spotlight: Shedding Light on the Web of Documents  
   Venue: I-Semantics (2011)  
   URL: https://doi.org/10.1145/2063518.2063519

2. Constitutional AI: Harmlessness from AI Feedback  
   Venue: arXiv (2022)  
   URL: https://arxiv.org/abs/2212.08073

3. Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks  
   Venue: NeurIPS (2020)  
   URL: https://arxiv.org/abs/2005.11401

4. From Local to Global: A GraphRAG Approach to Query-Focused Summarization  
   Venue: arXiv (2024)  
   URL: https://arxiv.org/abs/2404.16130

5. ReAct: Synergizing Reasoning and Acting in Language Models  
   Venue: ICLR (2023)  
   URL: https://arxiv.org/abs/2210.03629

6. Think-on-Graph: Deep and Responsible Reasoning of Large Language Model on Knowledge Graph  
   Venue: arXiv (2023)  
   URL: https://arxiv.org/abs/2307.07697

7. Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks  
   Venue: EMNLP (2019)  
   URL: https://arxiv.org/abs/1908.10084

8. Dense Passage Retrieval for Open-Domain Question Answering  
   Venue: EMNLP (2020)  
   URL: https://arxiv.org/abs/2004.04906

9. MRKL Systems: A modular, neuro-symbolic architecture  
   Venue: arXiv (2022)  
   URL: https://arxiv.org/abs/2205.00445

10. Chain-of-Verification Reduces Hallucination in Large Language Models  
    Venue: arXiv (2023)  
    URL: https://arxiv.org/abs/2309.11495

11. LLMs4OL: Large Language Models for Ontology Learning  
    Venue: arXiv (2023)  
    URL: https://arxiv.org/abs/2307.16648
