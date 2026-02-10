from __future__ import annotations

import importlib.util
import os
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ontology_llm.tools import prompt_tools


@dataclass(frozen=True)
class PaperRef:
    title: str
    venue: str
    year: int
    url: str


@dataclass(frozen=True)
class MethodMeta:
    method_id: str
    name: str
    ontology_file: str
    highlight: str
    ontology_type: str
    compare_rule: str
    paper_basis: str
    references: tuple[PaperRef, ...]


@dataclass(frozen=True)
class OntologySnapshot:
    class_count: int = 0
    instance_count: int = 0
    relation_count: int = 0
    candidate_count: int = 0
    product_labels: tuple[str, ...] = ()
    rule_ids: tuple[str, ...] = ()
    relation_types: tuple[str, ...] = ()
    property_keys: tuple[str, ...] = ()


METHODS: tuple[MethodMeta, ...] = (
    MethodMeta(
        method_id="method1",
        name="Keyword Grounding",
        ontology_file="data/ontologies/method1_keyword_grounding.yaml",
        highlight="표면형(alias) 기반 엔티티 링크 + lexical grounding",
        ontology_type="검색 최적화형",
        compare_rule="질의 표면형과 alias/label을 lexical matching으로 정합",
        paper_basis="DBpedia Spotlight 방식의 surface-form entity linking",
        references=(
            PaperRef(
                title="DBpedia Spotlight: Shedding Light on the Web of Documents",
                venue="I-Semantics",
                year=2011,
                url="https://doi.org/10.1145/2063518.2063519",
            ),
        ),
    ),
    MethodMeta(
        method_id="method2",
        name="Ontology Prompting",
        ontology_file="data/ontologies/method2_ontology_prompting.yaml",
        highlight="Constraint/Policy 노드를 프롬프트 규칙으로 주입",
        ontology_type="규칙/정책 최적화형",
        compare_rule="질의 의도 분류 후 policy/constraint 규칙 만족 여부 검증",
        paper_basis="Constitutional AI 기반 규칙 주도 생성",
        references=(
            PaperRef(
                title="Constitutional AI: Harmlessness from AI Feedback",
                venue="arXiv",
                year=2022,
                url="https://arxiv.org/abs/2212.08073",
            ),
        ),
    ),
    MethodMeta(
        method_id="method3",
        name="OG-RAG",
        ontology_file="data/ontologies/method3_og_rag.yaml",
        highlight="그래프 관계를 포함한 retrieval-augmented generation",
        ontology_type="관계/경로 추론형",
        compare_rule="노드 검색 + 그래프 relation evidence를 결합해 근거 선택",
        paper_basis="RAG + GraphRAG 구조 결합",
        references=(
            PaperRef(
                title="Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks",
                venue="NeurIPS",
                year=2020,
                url="https://arxiv.org/abs/2005.11401",
            ),
            PaperRef(
                title="From Local to Global: A GraphRAG Approach to Query-Focused Summarization",
                venue="arXiv",
                year=2024,
                url="https://arxiv.org/abs/2404.16130",
            ),
        ),
    ),
    MethodMeta(
        method_id="method4",
        name="KG Reasoning Agent",
        ontology_file="data/ontologies/method4_kg_reasoning_agent.yaml",
        highlight="도구 호출 + 멀티홉 KG 경로 추론",
        ontology_type="관계/경로 추론형",
        compare_rule="관계 경로를 생성하고 action/observation 루프로 유효 경로를 검증",
        paper_basis="ReAct + Think-on-Graph 멀티홉 추론",
        references=(
            PaperRef(
                title="ReAct: Synergizing Reasoning and Acting in Language Models",
                venue="ICLR",
                year=2023,
                url="https://arxiv.org/abs/2210.03629",
            ),
            PaperRef(
                title="Think-on-Graph: Deep and Responsible Reasoning of Large Language Model on Knowledge Graph",
                venue="arXiv",
                year=2023,
                url="https://arxiv.org/abs/2307.07697",
            ),
        ),
    ),
    MethodMeta(
        method_id="method5",
        name="Ontology Enhanced Embedding",
        ontology_file="data/ontologies/method5_ontology_enhanced_embedding.yaml",
        highlight="descriptor/동의어 확장 + dense retrieval 점수화",
        ontology_type="검색 최적화형",
        compare_rule="질의 임베딩과 확장 텍스트 임베딩 유사도 기반 재정렬",
        paper_basis="Sentence-BERT + Dense Passage Retrieval 기반",
        references=(
            PaperRef(
                title="Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks",
                venue="EMNLP",
                year=2019,
                url="https://arxiv.org/abs/1908.10084",
            ),
            PaperRef(
                title="Dense Passage Retrieval for Open-Domain Question Answering",
                venue="EMNLP",
                year=2020,
                url="https://arxiv.org/abs/2004.04906",
            ),
        ),
    ),
    MethodMeta(
        method_id="method6",
        name="Neuro-Symbolic Hybrid",
        ontology_file="data/ontologies/method6_neuro_symbolic_hybrid.yaml",
        highlight="신경망 생성 + symbolic rule executor 결합",
        ontology_type="규칙/정책 최적화형",
        compare_rule="LLM 생성 후보를 symbolic rule로 검증/수정",
        paper_basis="MRKL형 neuro-symbolic routing",
        references=(
            PaperRef(
                title="MRKL Systems: A modular, neuro-symbolic architecture",
                venue="arXiv",
                year=2022,
                url="https://arxiv.org/abs/2205.00445",
            ),
        ),
    ),
    MethodMeta(
        method_id="method7",
        name="Reverse Constraint Reasoning",
        ontology_file="data/ontologies/method7_reverse_constraint_reasoning.yaml",
        highlight="후보 답 생성 후 역검증(CoVe)으로 필터링",
        ontology_type="규칙/정책 최적화형",
        compare_rule="후보 답안 생성 후 evidence/constraint 질문으로 검증",
        paper_basis="Chain-of-Verification 기반 self-check",
        references=(
            PaperRef(
                title="Chain-of-Verification Reduces Hallucination in Large Language Models",
                venue="arXiv",
                year=2023,
                url="https://arxiv.org/abs/2309.11495",
            ),
        ),
    ),
    MethodMeta(
        method_id="method8",
        name="LLM -> Ontology Enrichment",
        ontology_file="data/ontologies/method8_llm_to_ontology.yaml",
        highlight="결손 속성 탐지 후 ontology 보강 제안",
        ontology_type="지식 확장형",
        compare_rule="질의 로그와 결손 속성 신호를 결합해 보강 후보 도출",
        paper_basis="LLM 기반 ontology learning/augmentation",
        references=(
            PaperRef(
                title="LLMs4OL: Large Language Models for Ontology Learning",
                venue="arXiv",
                year=2023,
                url="https://arxiv.org/abs/2307.16648",
            ),
        ),
    ),
)


METHOD_EXAMPLE_CATALOG: dict[str, dict[str, Any]] = {
    "method1": {
        "scenario": "별칭/표면형으로 제품을 찾는 기본 질의",
        "sample_questions": [
            "빠나 우유 가격 알려줘",
            "banana milk 가격이 얼마야?",
        ],
        "expected_outcome": "alias/label lexical 매칭으로 price_krw 사실을 우선 반환",
        "extra_group": "core",
        "dependencies": [],
        "env_keys": [
            "M1_KEYWORD_MIN_TOKEN_LEN",
            "M1_KEYWORD_LIMIT",
        ],
    },
    "method2": {
        "scenario": "정책/규칙(가격 우선 문장)을 강제하는 질의",
        "sample_questions": [
            "바나나우유 가격을 규칙에 맞는 문장으로 답해줘",
            "가격 질문이니까 템플릿대로 말해줘",
        ],
        "expected_outcome": "Constraint/Policy 규칙을 적용해 첫 문장에 가격을 배치",
        "extra_group": "core",
        "dependencies": [],
        "env_keys": [
            "M2_POLICY_STRICT_MODE",
            "M2_POLICY_MAX_RULES",
        ],
    },
    "method3": {
        "scenario": "제품-매장-지역-정책 관계 근거를 포함한 질의",
        "sample_questions": [
            "빠나 우유가 왜 3000원인지 관계 근거까지 설명해줘",
            "어느 매장에서 팔고 어떤 정책이 연결되는지 알려줘",
        ],
        "expected_outcome": "node facts + graph relations를 함께 사용해 근거형 응답 생성",
        "extra_group": "method34",
        "dependencies": ["networkx", "neo4j"],
        "env_keys": [
            "GRAPH_BACKEND",
            "GRAPH_TOP_K",
            "GRAPH_MAX_HOPS",
            "NEO4J_URI",
        ],
    },
    "method4": {
        "scenario": "멀티홉 경로(생산-물류-매장)를 따라 설명하는 질의",
        "sample_questions": [
            "빠나 우유가 생산부터 강남 매장까지 오는 경로를 설명해줘",
            "브랜드에서 매장까지 다단계 경로로 추론해줘",
        ],
        "expected_outcome": "1-hop/2-hop 경로를 확장하며 선택 경로를 trace로 제시",
        "extra_group": "method34",
        "dependencies": ["networkx", "langgraph", "neo4j"],
        "env_keys": [
            "GRAPH_BACKEND",
            "GRAPH_MAX_HOPS",
            "NEO4J_URI",
        ],
    },
    "method5": {
        "scenario": "표현이 달라도 의미 유사도로 제품을 찾는 질의",
        "sample_questions": [
            "노란 용기 달콤한 바나나 향 우유 가격 알려줘",
            "cold drink convenience store bestseller 가격 알려줘",
        ],
        "expected_outcome": "descriptor/동의어 확장 + dense score로 후보 재정렬",
        "extra_group": "method5",
        "dependencies": ["sentence_transformers", "chromadb", "rank_bm25"],
        "env_keys": [
            "EMBEDDING_PROVIDER",
            "EMBEDDING_MODEL",
            "VECTOR_DB_PROVIDER",
            "VECTOR_TOP_K",
            "HYBRID_ALPHA",
        ],
    },
    "method6": {
        "scenario": "자유 생성과 규칙 제약을 동시에 만족해야 하는 질의",
        "sample_questions": [
            "빠나 우유 가격과 재고를 규칙 위반 없이 자연스럽게 답해줘",
            "재고가 없으면 품절로 안내하는 규칙을 지켜 답해줘",
        ],
        "expected_outcome": "LLM 초안 후 symbolic rule 검증을 거쳐 제약 위반을 수정",
        "extra_group": "method678",
        "dependencies": ["z3"],
        "env_keys": [
            "RULE_ENGINE",
            "RULE_STRICT_MODE",
        ],
    },
    "method7": {
        "scenario": "후보 답안 생성 후 역검증으로 신뢰도 높은 답을 선택",
        "sample_questions": [
            "후보 답을 검증해서 빠나 우유 가격을 가장 확실하게 알려줘",
            "근거가 약한 후보는 버리고 검증된 답만 줘",
        ],
        "expected_outcome": "candidate 생성 -> evidence 검증 -> low-confidence 후보 탈락",
        "extra_group": "method678",
        "dependencies": ["z3", "sklearn"],
        "env_keys": [
            "VERIFICATION_CANDIDATES",
            "CONFIDENCE_THRESHOLD",
        ],
    },
    "method8": {
        "scenario": "답변과 함께 온톨로지 보강 제안을 도출하는 질의",
        "sample_questions": [
            "빠나 우유에 누락된 속성이 뭐고 어떻게 보강하면 좋아?",
            "현재 온톨로지 기준으로 추가해야 할 속성/관계를 제안해줘",
        ],
        "expected_outcome": "missing_property 신호 기반으로 enrichment 후보를 제안",
        "extra_group": "method678",
        "dependencies": ["rdflib", "owlready2"],
        "env_keys": [
            "ENRICHMENT_MAX_PROPOSALS",
            "ENRICHMENT_ALLOW_NEW_RELATIONS",
            "ENRICHMENT_AUTO_APPLY",
            "ONTOLOGY_EXPORT_PATH",
        ],
    },
}


def _is_dependency_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def build_method_examples(root_dir: Path) -> list[dict[str, Any]]:
    method_by_id = {item.method_id: item for item in METHODS}
    rows: list[dict[str, Any]] = []
    for method_id in sorted(METHOD_EXAMPLE_CATALOG):
        catalog = METHOD_EXAMPLE_CATALOG[method_id]
        meta = method_by_id.get(method_id)
        if not meta:
            continue

        ontology_path = root_dir / meta.ontology_file
        dependencies = [
            {
                "module": module_name,
                "ready": _is_dependency_available(module_name),
            }
            for module_name in catalog.get("dependencies", [])
        ]
        envs = [
            {
                "key": env_key,
                "value": os.getenv(env_key, ""),
                "ready": bool(os.getenv(env_key)),
            }
            for env_key in catalog.get("env_keys", [])
        ]
        setup_ready = (
            ontology_path.exists()
            and all(dep["ready"] for dep in dependencies)
            and all(item["ready"] for item in envs)
        )
        rows.append(
            {
                "method_id": method_id,
                "method_name": meta.name,
                "scenario": catalog["scenario"],
                "sample_questions": catalog["sample_questions"],
                "expected_outcome": catalog["expected_outcome"],
                "quick_run": f"uv run ontology-llm chat \"{catalog['sample_questions'][0]}\" --method {method_id}",
                "quick_exp": f"uv run ontology-llm exp \"{catalog['sample_questions'][0]}\" --method {method_id} --auto-ingest",
                "setup": {
                    "extra_group": catalog.get("extra_group", "core"),
                    "ontology_file": meta.ontology_file,
                    "ontology_ready": ontology_path.exists(),
                    "dependencies": dependencies,
                    "env": envs,
                    "overall_ready": setup_ready,
                },
            }
        )
    return rows


def _load_yaml_counts(path: Path) -> dict[str, int]:
    if not path.exists():
        return {"classes": 0, "instances": 0, "relations": 0}
    with path.open("r", encoding="utf-8") as fp:
        payload = yaml.safe_load(fp) or {}
    return {
        "classes": len(payload.get("classes", [])),
        "instances": len(payload.get("instances", [])),
        "relations": len(payload.get("relations", [])),
    }


def _unique_keep_order(items: list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(item for item in items if item))


def _preview(items: tuple[str, ...], max_items: int = 3) -> str:
    if not items:
        return "-"
    head = list(items[:max_items])
    suffix = f" 외 {len(items) - max_items}개" if len(items) > max_items else ""
    return ", ".join(head) + suffix


def _load_method_ontology_snapshot(root_dir: Path, ontology_file: str) -> OntologySnapshot:
    path = root_dir / ontology_file
    if not path.exists():
        return OntologySnapshot()

    with path.open("r", encoding="utf-8") as fp:
        payload = yaml.safe_load(fp) or {}

    classes = payload.get("classes", []) or []
    instances = payload.get("instances", []) or []
    relations = payload.get("relations", []) or []

    product_labels: list[str] = []
    rule_ids: list[str] = []
    relation_types: list[str] = []
    property_keys: list[str] = []
    candidate_count = 0

    for inst in instances:
        inst_id = str(inst.get("id", "")).strip()
        class_name = str(inst.get("class", "")).strip().lower()
        label = str(inst.get("label", "")).strip()

        if (
            class_name in {"product", "beverage"}
            or inst_id.endswith("_MILK")
            or "우유" in label
        ):
            product_labels.append(label or inst_id)

        if (
            class_name in {"constraint", "rule", "policy", "guardrail"}
            or inst_id.startswith(("RULE_", "CONS_", "POLICY_"))
        ):
            rule_ids.append(inst_id or label)

        if class_name == "candidateanswer" or inst_id.startswith("CAND_"):
            candidate_count += 1

        for prop in inst.get("properties", []) or []:
            key = str(prop.get("key", "")).strip()
            if key:
                property_keys.append(key)

    for rel in relations:
        rel_type = str(rel.get("type", "")).strip()
        if rel_type:
            relation_types.append(rel_type)

    return OntologySnapshot(
        class_count=len(classes),
        instance_count=len(instances),
        relation_count=len(relations),
        candidate_count=candidate_count,
        product_labels=_unique_keep_order(product_labels),
        rule_ids=_unique_keep_order(rule_ids),
        relation_types=_unique_keep_order(relation_types),
        property_keys=_unique_keep_order(property_keys),
    )


def _build_method_blueprint(
    method_id: str,
    snapshot: OntologySnapshot,
) -> dict[str, list[str]]:
    product_preview = _preview(snapshot.product_labels, max_items=4)
    rule_preview = _preview(snapshot.rule_ids, max_items=3)
    relation_preview = _preview(snapshot.relation_types, max_items=4)
    property_preview = _preview(snapshot.property_keys, max_items=5)

    blueprints: dict[str, dict[str, list[str]]] = {
        "method1": {
            "received": [
                "질문 정규화 및 alias 토큰 추출",
                "표면형 질의어를 제품 엔티티 후보로 변환",
            ],
            "lookup": [
                f"alias/keyword 매칭으로 제품 후보 조회 ({product_preview})",
                "price_krw/category/stock 핵심 속성 로드",
            ],
            "compare": [
                "matched_terms/field 기반 후보 점수 계산",
                "질문 의도와 정합되는 사실 우선 선택",
            ],
            "generate": [
                "근거 사실 우선 답변 생성",
                "근거 부족 시 안전 문장으로 마무리",
            ],
        },
        "method2": {
            "received": [
                "질문 의도 분류 및 규칙 슬롯 추출",
                "정책 적용 대상 엔티티 식별",
            ],
            "lookup": [
                f"Constraint/Policy 노드 로드 ({rule_preview})",
                "규칙 applies_to 대상 제품 fact 로드",
            ],
            "compare": [
                "규칙 충돌 검사 및 우선순위 결정",
                "규칙 준수 여부를 컨텍스트에 명시",
            ],
            "generate": [
                "규칙 준수 답변 생성",
                "적용된 규칙/템플릿 로그 기록",
            ],
        },
        "method3": {
            "received": [
                "질문에서 핵심 엔티티/관계 힌트 추출",
                "근거형 답변 모드 설정",
            ],
            "lookup": [
                "제품 + 공급사/프로모션 노드 조회",
                f"관계 evidence 수집 ({relation_preview})",
            ],
            "compare": [
                "node fact + relation evidence 병합",
                "근거 점수 기반 후보 재정렬",
            ],
            "generate": [
                "근거 인용형 답변 생성",
                "근거 부족 시 fallback 안내",
            ],
        },
        "method4": {
            "received": [
                "질문 정규화 및 seed entity 선정",
                "경로 탐색 파라미터 초기화",
            ],
            "lookup": [
                "1-hop 경로 탐색 후 multi-hop 확장",
                f"경로 후보 수집 ({relation_preview})",
            ],
            "compare": [
                "경로 제약 검증 및 추론 가능성 확인",
                "경로 신뢰도 기반 우선순위화",
            ],
            "generate": [
                "선택 경로를 설명형 답변으로 생성",
                "사용 경로 trace 로그 저장",
            ],
        },
        "method5": {
            "received": [
                "질문 정규화 및 임베딩 입력 구성",
                "descriptor/동의어 확장 후보 생성",
            ],
            "lookup": [
                "dense similarity top-k 후보 조회",
                f"유사도 근거 속성 로드 ({property_preview})",
            ],
            "compare": [
                "dense score + lexical score 결합",
                "하이브리드 재정렬로 최종 후보 선택",
            ],
            "generate": [
                "유사도 근거 포함 답변 생성",
                "top-k 근거 로그 출력",
            ],
        },
        "method6": {
            "received": [
                "질문 정규화 및 symbolic constraint 탐지",
                "신경망 생성 모드 준비",
            ],
            "lookup": [
                "dense/lexical 후보 fact 로드",
                f"Rule/Constraint 세트 로드 ({rule_preview})",
            ],
            "compare": [
                "LLM 초안 후보와 symbolic rule 대조",
                "위반 항목 자동 수정 및 재검증",
            ],
            "generate": [
                "검증 통과 답변 생성",
                "rule enforcement 로그 기록",
            ],
        },
        "method7": {
            "received": [
                "질문 정규화 및 검증 전략 선택",
                "후보 생성/검증 파이프라인 준비",
            ],
            "lookup": [
                f"후보 답안 생성 ({snapshot.candidate_count}개 패턴)",
                "검증 근거 relation/fact 조회",
            ],
            "compare": [
                f"제약 검증 수행 ({rule_preview})",
                "저신뢰 후보 탈락 후 재평가",
            ],
            "generate": [
                "검증 통과 답변 생성",
                "confidence score 및 검증 로그 기록",
            ],
        },
        "method8": {
            "received": [
                "질문 정규화 및 결손 시그널 탐지",
                "보강 제안 모드 활성화",
            ],
            "lookup": [
                "missing_property/질의 로그 근거 조회",
                f"현재 제품/속성 스냅샷 로드 ({product_preview})",
            ],
            "compare": [
                "보강 후보 충돌/중복 검증",
                "보강 우선순위 큐 생성",
            ],
            "generate": [
                "안전 답변 + 온톨로지 보강 제안 생성",
                "ontology update draft 기록",
            ],
        },
    }
    return blueprints.get(method_id, blueprints["method1"])


def _build_method_reflection(snapshot: OntologySnapshot) -> dict[str, Any]:
    preferred_order = [
        "alias",
        "keyword",
        "category",
        "price_krw",
        "stock",
        "descriptor",
        "rule",
        "template",
        "missing_property",
    ]
    prop_set = set(snapshot.property_keys)
    ordered_focus = [key for key in preferred_order if key in prop_set]
    tail = [key for key in snapshot.property_keys if key not in ordered_focus]
    focus_properties = (ordered_focus + tail)[:8]
    return {
        "counts": {
            "classes": snapshot.class_count,
            "instances": snapshot.instance_count,
            "relations": snapshot.relation_count,
            "candidates": snapshot.candidate_count,
        },
        "product_labels": list(snapshot.product_labels[:8]),
        "rule_ids": list(snapshot.rule_ids[:8]),
        "relation_types": list(snapshot.relation_types[:8]),
        "focus_properties": focus_properties,
    }


def build_ontology_utilization_view(root_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in METHODS:
        snapshot = _load_method_ontology_snapshot(root_dir, item.ontology_file)
        rows.append(
            {
                "method_id": item.method_id,
                "method_name": item.name,
                "ontology_type": item.ontology_type,
                "highlight": item.highlight,
                "ontology_file": item.ontology_file,
                "compare_rule": item.compare_rule,
                "paper_basis": item.paper_basis,
                "references": [
                    {
                        "title": ref.title,
                        "venue": ref.venue,
                        "year": ref.year,
                        "url": ref.url,
                    }
                    for ref in item.references
                ],
                "ontology_reflection": _build_method_reflection(snapshot),
                "dag": build_method_dag(item.method_id, snapshot),
            }
        )
    return rows


def build_method_dag(
    method_id: str,
    snapshot: OntologySnapshot | None = None,
) -> dict[str, Any]:
    loaded_snapshot = snapshot or OntologySnapshot()
    stage_title = {
        "received": "1) Query Understanding",
        "lookup": "2) Ontology Retrieval",
        "compare": "3) Validation / Context",
        "generate": "4) LLM Generation",
    }
    stage_id = {
        "received": "s1",
        "lookup": "s2",
        "compare": "s3",
        "generate": "s4",
    }

    selected = _build_method_blueprint(method_id, loaded_snapshot)

    stages = [
        {"id": stage_id[key], "title": stage_title[key], "runtime_stage": key}
        for key in ("received", "lookup", "compare", "generate")
    ]

    lane_map: dict[str, int] = defaultdict(int)
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    prev_node_id: str | None = None
    node_idx = 1

    for runtime_key in ("received", "lookup", "compare", "generate"):
        for label in selected[runtime_key]:
            node_id = f"n{node_idx:02d}"
            nodes.append(
                {
                    "id": node_id,
                    "label": label,
                    "stage": stage_id[runtime_key],
                    "lane": lane_map[runtime_key],
                    "runtime_stage": runtime_key,
                }
            )
            lane_map[runtime_key] += 1
            if prev_node_id:
                edges.append(
                    {
                        "source": prev_node_id,
                        "target": node_id,
                        "order": len(edges) + 1,
                    }
                )
            prev_node_id = node_id
            node_idx += 1

    return {"stages": stages, "nodes": nodes, "edges": edges}


def build_ontology_test_status(root_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in METHODS:
        ontology_path = root_dir / item.ontology_file
        counts = _load_yaml_counts(ontology_path)
        ready = counts["instances"] > 0 and counts["classes"] > 0
        rows.append(
            {
                "method_id": item.method_id,
                "method_name": item.name,
                "ontology_type": item.ontology_type,
                "ontology_file": item.ontology_file,
                "classes": counts["classes"],
                "instances": counts["instances"],
                "relations": counts["relations"],
                "status": "ready" if ready else "missing",
            }
        )
    return rows


def build_token_mitigation_status() -> list[dict[str, Any]]:
    env_keys = (
        "MAX_ONTOLOGY_FACTS",
        "MAX_RELATIONS",
        "MAX_CONTEXT_CHARS",
        "PROMPT_BUDGET_MODE",
        "PROMPT_TOKEN_WARN_THRESHOLD",
    )
    configured_env = [name for name in env_keys if os.getenv(name)]

    return [
        {
            "step_id": "D-1",
            "title": "길이 분리 측정",
            "summary": "question/context/prompt 길이와 토큰을 분리 측정",
            "status": "done"
            if all(
                hasattr(prompt_tools, f)
                for f in ("estimate_prompt_budget", "log_prompt_budget")
            )
            else "missing",
            "process": [
                "estimate_prompt_budget() 구현",
                "log_prompt_budget() 경고 로깅",
            ],
        },
        {
            "step_id": "D-2",
            "title": "컨텍스트 예산 압축",
            "summary": "핵심 사실/관계를 우선 보존하며 온톨로지 컨텍스트 압축",
            "status": "done"
            if hasattr(prompt_tools, "compress_ontology_context")
            else "missing",
            "process": [
                "price_krw/alias 우선 정렬",
                "max_facts/max_relations/max_chars 컷오프",
            ],
        },
        {
            "step_id": "D-3",
            "title": "설정 기반 운영 제어",
            "summary": "환경변수로 운영 파라미터 조정",
            "status": "done" if len(configured_env) >= 3 else "partial",
            "process": [
                "환경변수 키 연결",
                f"현재 설정된 키: {', '.join(configured_env) if configured_env else '없음'}",
            ],
        },
    ]


def build_dashboard_payload(root_dir: Path) -> dict[str, Any]:
    return {
        "ontology_utilization": build_ontology_utilization_view(root_dir),
        "ontology_test_status": build_ontology_test_status(root_dir),
        "token_mitigation_status": build_token_mitigation_status(),
        "method_examples": build_method_examples(root_dir),
    }
