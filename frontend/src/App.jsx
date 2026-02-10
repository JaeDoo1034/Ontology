import { useEffect, useMemo, useState } from "react";
import ReactFlow, {
  Background,
  BackgroundVariant,
  Controls,
  Handle,
  MarkerType,
  Position,
  useEdgesState,
  useNodesState
} from "reactflow";
import "reactflow/dist/style.css";

const statusLabel = {
  ready: "준비 완료",
  done: "완료",
  partial: "부분 완료",
  missing: "미구성"
};

const runStageLabel = {
  prep: "준비중",
  running: "실행중",
  done: "실행완료"
};

const runtimeStageOrder = ["received", "lookup", "compare", "generate"];
const runtimeStageTitle = {
  received: "질문 접수",
  lookup: "온톨로지 검색",
  compare: "비교/컨텍스트 구성",
  generate: "결과 생성"
};
const runtimeStageFallbackDetail = {
  received: "사용자 입력 검증 및 실행 준비",
  lookup: "질의 토큰 기반 facts/relation 조회",
  compare: "우선 사실 추출 + 컨텍스트 압축",
  generate: "LLM 호출 및 최종 응답 생성"
};

function buildRunStageTemplate(methodMeta) {
  const grouped = {
    received: [],
    lookup: [],
    compare: [],
    generate: []
  };
  const stageTitleByRuntime = Object.fromEntries(
    (methodMeta?.dag?.stages || []).map((stage) => [stage.runtime_stage, stage.title])
  );
  for (const node of methodMeta?.dag?.nodes || []) {
    const key = node.runtime_stage;
    if (key && grouped[key]) grouped[key].push(node.label);
  }
  return runtimeStageOrder.map((id) => ({
    id,
    title: stageTitleByRuntime[id] || runtimeStageTitle[id],
    detail: grouped[id].length ? grouped[id].join(" → ") : runtimeStageFallbackDetail[id],
    state: "prep",
    input: null,
    output: null
  }));
}

function Card({ title, action, children }) {
  return (
    <section className="card">
      <div className="card-head">
        <h2>{title}</h2>
        {action ? <div className="card-action">{action}</div> : null}
      </div>
      {children}
    </section>
  );
}

export default function App() {
  const [dashboard, setDashboard] = useState(null);
  const [selectedMethod, setSelectedMethod] = useState("method1");
  const [showOntologyStatus, setShowOntologyStatus] = useState(false);
  const [showTokenStatus, setShowTokenStatus] = useState(false);
  const [question, setQuestion] = useState("빠나 우유 가격이 뭐야?");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [runStages, setRunStages] = useState(buildRunStageTemplate(null));

  useEffect(() => {
    fetch("/api/dashboard")
      .then((res) => res.json())
      .then((data) => setDashboard(data))
      .catch((e) => setErr(e.message));
  }, []);

  const grouped = useMemo(() => {
    if (!dashboard?.ontology_test_status) return {};
    return dashboard.ontology_test_status.reduce((acc, row) => {
      if (!acc[row.ontology_type]) acc[row.ontology_type] = [];
      acc[row.ontology_type].push(row);
      return acc;
    }, {});
  }, [dashboard]);

  const selectedMethodMeta = useMemo(() => {
    if (!dashboard?.ontology_utilization?.length) return null;
    return (
      dashboard.ontology_utilization.find((x) => x.method_id === selectedMethod) ||
      dashboard.ontology_utilization[0]
    );
  }, [dashboard, selectedMethod]);

  const selectedMethodStatus = useMemo(() => {
    if (!dashboard?.ontology_test_status?.length) return null;
    return (
      dashboard.ontology_test_status.find((x) => x.method_id === selectedMethod) ||
      null
    );
  }, [dashboard, selectedMethod]);

  const selectedMethodExample = useMemo(() => {
    if (!dashboard?.method_examples?.length) return null;
    return (
      dashboard.method_examples.find((item) => item.method_id === selectedMethod) || null
    );
  }, [dashboard, selectedMethod]);

  const selectedMethodReflection = selectedMethodMeta?.ontology_reflection || null;

  useEffect(() => {
    setRunStages(buildRunStageTemplate(selectedMethodMeta));
  }, [selectedMethodMeta]);

  const markStage = (id, state, detail, inputData, outputData) => {
    setRunStages((prev) =>
      prev.map((item) =>
        item.id === id
          ? { ...item, state, detail: detail || item.detail }
          : item
      )
    );
    if (inputData !== undefined || outputData !== undefined) {
      setRunStages((prev) =>
        prev.map((item) =>
          item.id === id
            ? {
                ...item,
                input: inputData !== undefined ? inputData : item.input,
                output: outputData !== undefined ? outputData : item.output
              }
            : item
        )
      );
    }
  };

  async function runPipelineUntil(targetStage = "generate", questionOverride = null) {
    if (loading) return;
    const requestedQuestion = (questionOverride ?? question ?? "").trim();
    if (!requestedQuestion) {
      setErr("질문을 입력해주세요.");
      return;
    }
    setLoading(true);
    setErr("");
    setAnswer("");
    setRunStages(buildRunStageTemplate(selectedMethodMeta));
    let stopAfterTarget = false;
    const controller = new AbortController();

    try {
      const res = await fetch("/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: requestedQuestion, method_id: selectedMethod }),
        signal: controller.signal
      });
      if (!res.ok || !res.body) {
        throw new Error("스트리밍 응답을 받을 수 없습니다.");
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";
        for (const line of lines) {
          const payload = line.trim();
          if (!payload) continue;
          const evt = JSON.parse(payload);
          if (evt.event === "stage") {
            markStage(
              evt.stage,
              mapRunState(evt.status),
              evt.message,
              evt.input,
              evt.output
            );
            if (
              targetStage !== "generate" &&
              evt.stage === targetStage &&
              evt.status === "done"
            ) {
              stopAfterTarget = true;
              controller.abort();
              break;
            }
          }
          if (evt.event === "answer") {
            setAnswer(evt.answer || "");
          }
          if (evt.event === "error") {
            throw new Error(evt.message || "요청 처리 중 오류가 발생했습니다.");
          }
        }
      }
    } catch (e) {
      if (e?.name === "AbortError" && stopAfterTarget) {
        return;
      }
      setErr(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function ask() {
    await runPipelineUntil("generate");
  }

  return (
    <main className="page">
      <header className="hero">
        <p className="eyebrow">Ontology + LLM Dashboard</p>
        <h1>테스트 화면</h1>
        <p>
          CLI 없이 온톨로지 활용 흐름, 유형별 테스트 현황, 토큰 한도 대응 단계를 한
          화면에서 확인합니다.
        </p>
      </header>

      {err ? <p className="error">{err}</p> : null}

      <section className="split-layout">
        <div className="left-panel">
          <Card title="좌측: Method / 환경 정보">
            <div className="method-picker">
              <label htmlFor="method-select">DAG Method 선택</label>
              <select
                id="method-select"
                value={selectedMethod}
                onChange={(e) => setSelectedMethod(e.target.value)}
              >
                {dashboard?.ontology_utilization?.map((item) => (
                  <option key={item.method_id} value={item.method_id}>
                    {item.method_id.toUpperCase()} · {item.method_name}
                  </option>
                ))}
              </select>
            </div>
            <div className="dag-note">
              <strong>질의-온톨로지 비교 규칙:</strong>{" "}
              {selectedMethodMeta?.compare_rule || "-"}
            </div>
            <MethodDag
              dag={selectedMethodMeta?.dag}
              runStages={runStages}
              onExecuteStage={runPipelineUntil}
            />
            <KeywordTrace runStages={runStages} />
            <div className="method-detail">
              <h3>
                {selectedMethodMeta?.method_id?.toUpperCase()} ·{" "}
                {selectedMethodMeta?.method_name}
              </h3>
              <p>{selectedMethodMeta?.highlight}</p>
              <p className="detail">
                <strong>논문 근거:</strong> {selectedMethodMeta?.paper_basis || "-"}
              </p>
              <div className="method-detail-grid">
                <div>
                  <span>유형</span>
                  <strong>{selectedMethodMeta?.ontology_type || "-"}</strong>
                </div>
                <div>
                  <span>온톨로지 파일</span>
                  <strong>{selectedMethodMeta?.ontology_file || "-"}</strong>
                </div>
                <div>
                  <span>테스트 상태</span>
                  <strong>
                    {selectedMethodStatus
                      ? statusLabel[selectedMethodStatus.status]
                      : "-"}
                  </strong>
                </div>
                <div>
                  <span>구조 크기</span>
                  <strong>
                    {selectedMethodStatus
                      ? `C:${selectedMethodStatus.classes} I:${selectedMethodStatus.instances} R:${selectedMethodStatus.relations}`
                      : "-"}
                  </strong>
                </div>
              </div>
              {selectedMethodReflection ? (
                <div className="reflection-panel">
                  <h4>온톨로지 반영 요약</h4>
                  <div className="method-detail-grid">
                    <div>
                      <span>클래스/인스턴스/관계</span>
                      <strong>
                        C:{selectedMethodReflection.counts?.classes ?? 0} I:
                        {selectedMethodReflection.counts?.instances ?? 0} R:
                        {selectedMethodReflection.counts?.relations ?? 0}
                      </strong>
                    </div>
                    <div>
                      <span>검증 후보 노드</span>
                      <strong>{selectedMethodReflection.counts?.candidates ?? 0}</strong>
                    </div>
                  </div>
                  <div className="reflection-row">
                    <span>제품 엔티티</span>
                    <div className="chip-wrap">
                      {(selectedMethodReflection.product_labels || []).map((item) => (
                        <span key={`prod-${item}`} className="reflection-chip product">
                          {item}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="reflection-row">
                    <span>규칙/제약 노드</span>
                    <div className="chip-wrap">
                      {(selectedMethodReflection.rule_ids || []).map((item) => (
                        <span key={`rule-${item}`} className="reflection-chip rule">
                          {item}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="reflection-row">
                    <span>관계 타입</span>
                    <div className="chip-wrap">
                      {(selectedMethodReflection.relation_types || []).map((item) => (
                        <span key={`rel-${item}`} className="reflection-chip relation">
                          {item}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="reflection-row">
                    <span>핵심 속성</span>
                    <div className="chip-wrap">
                      {(selectedMethodReflection.focus_properties || []).map((item) => (
                        <span key={`prop-${item}`} className="reflection-chip property">
                          {item}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              ) : null}
              {(selectedMethodMeta?.references || []).length ? (
                <ul className="paper-list">
                  {selectedMethodMeta.references.map((ref) => (
                    <li key={`${ref.title}-${ref.year}`}>
                      <a href={ref.url} target="_blank" rel="noreferrer">
                        {ref.title}
                      </a>
                      <span>{ref.venue} · {ref.year}</span>
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
          </Card>

          <Card
            title="온톨로지 유형별 테스트 현황"
            action={
              <button
                className="toggle-btn"
                onClick={() => setShowOntologyStatus((prev) => !prev)}
              >
                {showOntologyStatus ? "숨기기" : "보기"}
              </button>
            }
          >
            {showOntologyStatus
              ? Object.entries(grouped).map(([type, rows]) => (
                  <div key={type} className="group-block">
                    <h3>{type}</h3>
                    <table>
                      <thead>
                        <tr>
                          <th>Method</th>
                          <th>Classes</th>
                          <th>Instances</th>
                          <th>Relations</th>
                          <th>상태</th>
                        </tr>
                      </thead>
                      <tbody>
                        {rows.map((row) => (
                          <tr key={row.method_id}>
                            <td>{row.method_name}</td>
                            <td>{row.classes}</td>
                            <td>{row.instances}</td>
                            <td>{row.relations}</td>
                            <td>
                              <span className={`status ${row.status}`}>
                                {statusLabel[row.status] || row.status}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ))
              : null}
          </Card>

          <Card
            title="환경: 토큰 한도 대응 과정 현황"
            action={
              <button
                className="toggle-btn"
                onClick={() => setShowTokenStatus((prev) => !prev)}
              >
                {showTokenStatus ? "숨기기" : "보기"}
              </button>
            }
          >
            {showTokenStatus ? (
              <ul className="timeline">
                {dashboard?.token_mitigation_status?.map((step) => (
                  <li key={step.step_id}>
                    <div className="timeline-top">
                      <strong>
                        {step.step_id} {step.title}
                      </strong>
                      <span className={`status ${step.status}`}>
                        {statusLabel[step.status] || step.status}
                      </span>
                    </div>
                    <p>{step.summary}</p>
                    <p className="detail">{step.process.join(" | ")}</p>
                  </li>
                ))}
              </ul>
            ) : null}
          </Card>
        </div>

        <div className="right-panel">
          <Card title="우측: 빠른 질문 테스트">
            {selectedMethodExample ? (
              <section className="example-panel">
                <div className="example-head">
                  <strong>대표 예시 시나리오</strong>
                  <span
                    className={`setup-badge ${
                      selectedMethodExample.setup?.overall_ready ? "ready" : "partial"
                    }`}
                  >
                    {selectedMethodExample.setup?.overall_ready ? "세팅 완료" : "추가 세팅 필요"}
                  </span>
                </div>
                <p>{selectedMethodExample.scenario}</p>
                <p className="detail">
                  <strong>기대 결과:</strong> {selectedMethodExample.expected_outcome}
                </p>
                <div className="example-question-list">
                  {(selectedMethodExample.sample_questions || []).map((sample) => (
                    <button
                      key={sample}
                      type="button"
                      className="example-question-btn"
                      onClick={() => setQuestion(sample)}
                    >
                      {sample}
                    </button>
                  ))}
                </div>
                <div className="example-actions">
                  <button
                    type="button"
                    className="example-run-btn"
                    disabled={loading || !selectedMethodExample.sample_questions?.length}
                    onClick={() => {
                      const sample = selectedMethodExample.sample_questions?.[0];
                      if (!sample) return;
                      setQuestion(sample);
                      runPipelineUntil("generate", sample);
                    }}
                  >
                    대표 예시 바로 실행
                  </button>
                </div>
                <div className="setup-block">
                  <small>필수 세팅 점검</small>
                  <div className="setup-chip-wrap">
                    <span
                      className={`setup-chip ${
                        selectedMethodExample.setup?.ontology_ready ? "ok" : "missing"
                      }`}
                    >
                      ontology:{" "}
                      {selectedMethodExample.setup?.ontology_ready ? "OK" : "MISSING"}
                    </span>
                    {(selectedMethodExample.setup?.dependencies || []).map((dep) => (
                      <span
                        key={`dep-${dep.module}`}
                        className={`setup-chip ${dep.ready ? "ok" : "missing"}`}
                      >
                        {dep.module}: {dep.ready ? "OK" : "MISSING"}
                      </span>
                    ))}
                    {(selectedMethodExample.setup?.env || []).map((envItem) => (
                      <span
                        key={`env-${envItem.key}`}
                        className={`setup-chip ${envItem.ready ? "ok" : "missing"}`}
                      >
                        {envItem.key}: {envItem.ready ? "SET" : "EMPTY"}
                      </span>
                    ))}
                  </div>
                </div>
                <pre className="example-cmd">{selectedMethodExample.quick_run}</pre>
              </section>
            ) : null}
            <div className="run-stage-panel">
              {runStages.map((step) => (
                <article
                  key={step.id}
                  className={`run-stage ${step.state} clickable`}
                  onClick={() => runPipelineUntil(step.id)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      runPipelineUntil(step.id);
                    }
                  }}
                >
                  <div className="run-stage-top">
                    <strong>{step.title}</strong>
                    <span className={`run-state ${step.state}`}>
                      {runStageLabel[step.state]}
                    </span>
                  </div>
                  <p>{step.detail}</p>
                  <div className="io-grid">
                    <div>
                      <small>Input</small>
                      <pre className="stage-io">{formatPayload(step.input)}</pre>
                    </div>
                    <div>
                      <small>Output</small>
                      <pre className="stage-io">{formatPayload(step.output)}</pre>
                    </div>
                  </div>
                </article>
              ))}
            </div>
            <div className="chat-row">
              <textarea
                className="chat-input"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="질문을 입력하세요"
              />
              <button onClick={ask} disabled={loading}>
                {loading ? "생성 중..." : "질문 실행"}
              </button>
            </div>
            <pre className="answer">{answer || "아직 답변이 없습니다."}</pre>
          </Card>
        </div>
      </section>
    </main>
  );
}

function mapRunState(status) {
  if (status === "running") return "running";
  if (status === "done") return "done";
  return "prep";
}

function formatPayload(value) {
  if (value == null) return "-";
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function MethodDag({ dag, runStages, onExecuteStage }) {
  if (!dag?.nodes?.length) {
    return <p className="detail">Method DAG 데이터가 없습니다.</p>;
  }
  const graph = useMemo(() => {
    const runtime = Object.fromEntries(runStages.map((s) => [s.id, s.state]));
    const taskState = (key) => runtime[key] || "prep";
    const runtimeX = {
      received: 80,
      lookup: 620,
      compare: 1160,
      generate: 1700
    };
    const baseY = 120;
    const rowGap = 120;

    const groupedByRuntime = {
      received: [],
      lookup: [],
      compare: [],
      generate: []
    };
    for (const node of dag.nodes) {
      const key = node.runtime_stage || "received";
      if (!groupedByRuntime[key]) groupedByRuntime[key] = [];
      groupedByRuntime[key].push(node);
    }

    const layout = {};
    runtimeStageOrder.forEach((runtimeKey) => {
      const rows = (groupedByRuntime[runtimeKey] || []).slice().sort((a, b) => {
        return (a.lane ?? 0) - (b.lane ?? 0);
      });
      rows.forEach((node, idx) => {
        layout[node.id] = {
          x: runtimeX[runtimeKey],
          y: baseY + rowGap * idx
        };
      });
    });

    const nodes = dag.nodes.map((node, idx) => {
      const key = node.runtime_stage || "received";
      const pos = layout[node.id] || { x: 80, y: baseY + idx * rowGap };
      const isDecision = node.label.includes("?");
      return (isDecision ? decisionNode : cardNode)(
        node.id,
        `${String(idx + 1).padStart(2, "0")}. ${node.label}`,
        pos.x,
        pos.y,
        taskState(key),
        key
      );
    });

    const edges = (dag.edges || []).map((edge, idx) => {
      const src = dag.nodes.find((x) => x.id === edge.source);
      const dst = dag.nodes.find((x) => x.id === edge.target);
      const sameRuntime =
        (src?.runtime_stage || "received") === (dst?.runtime_stage || "received");
      const sequence = edge.order || idx + 1;
      return dataFlow(
        `e${sequence}`,
        edge.source,
        edge.target,
        sameRuntime ? "v" : "h",
        `${sequence}`
      );
    });
    return { nodes, edges };
  }, [dag, runStages]);

  const [nodes, setNodes, onNodesChange] = useNodesState(graph.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(graph.edges);

  useEffect(() => {
    setNodes((prevNodes) => {
      const prevMap = new Map(prevNodes.map((n) => [n.id, n]));
      return graph.nodes.map((next) => {
        const prev = prevMap.get(next.id);
        if (!prev) return next;
        return { ...next, position: prev.position };
      });
    });
  }, [graph.nodes, setNodes]);

  useEffect(() => {
    setEdges(graph.edges);
  }, [graph.edges, setEdges]);

  return (
    <div className="dag-wrap">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={(_, node) => {
          const stageId = node?.data?.runtimeStage;
          if (stageId && onExecuteStage) onExecuteStage(stageId);
        }}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.1 }}
        nodesDraggable
        nodesConnectable={false}
        elementsSelectable
        panOnDrag={false}
        zoomOnScroll={false}
        minZoom={0.35}
      >
        <Background variant={BackgroundVariant.Dots} color="#E5E7EB" gap={20} size={1} />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}

const nodeTypes = {
  card: CardNode,
  decision: DecisionNode,
  artifact: ArtifactNode
};

function CardNode({ data }) {
  return (
    <div className={`arch-card state-${data.state}`}>
      <FourWayHandles />
      <div className="arch-node-head">
        <span className={`arch-status ${data.state}`}>{runStageLabel[data.state]}</span>
      </div>
      <div className="arch-title">{data.label}</div>
    </div>
  );
}

function ArtifactNode({ data }) {
  return (
    <div className={`arch-artifact state-${data.state}`}>
      <FourWayHandles />
      <span className={`arch-status ${data.state}`}>{runStageLabel[data.state]}</span>
      <span>{data.label}</span>
    </div>
  );
}

function DecisionNode({ data }) {
  return (
    <div className="arch-decision-wrap">
      <FourWayHandles />
      <div className={`arch-decision state-${data.state}`}>
        <span className="arch-decision-text">{data.label}</span>
      </div>
      <span className={`arch-status ${data.state}`}>{runStageLabel[data.state]}</span>
    </div>
  );
}

function FourWayHandles() {
  return (
    <>
      <Handle type="target" position={Position.Left} id="left" />
      <Handle type="source" position={Position.Right} id="right" />
      <Handle type="target" position={Position.Top} id="top" />
      <Handle type="source" position={Position.Bottom} id="bottom" />
    </>
  );
}

function cardNode(id, label, x, y, state, runtimeStage) {
  return {
    id,
    type: "card",
    position: { x, y },
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
    data: { label, state, runtimeStage }
  };
}

function artifactNode(id, label, x, y, state) {
  return {
    id,
    type: "artifact",
    position: { x, y },
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
    data: { label, state }
  };
}

function dataFlow(id, source, target, direction, label) {
  return buildEdge(id, source, target, direction, "dataFlow", label);
}

function controlFlow(id, source, target, direction, label) {
  return buildEdge(id, source, target, direction, "controlFlow", label);
}

function buildEdge(id, source, target, direction, edgeType, label) {
  const directionMap = {
    h: { sourceHandle: "right", targetHandle: "left" },
    v: { sourceHandle: "bottom", targetHandle: "top" },
    up: { sourceHandle: "top", targetHandle: "bottom" },
    down: { sourceHandle: "bottom", targetHandle: "top" }
  };
  return {
    id,
    source,
    target,
    type: "smoothstep",
    markerEnd: { type: MarkerType.ArrowClosed, color: "#9CA3AF" },
    ...directionMap[direction],
    label,
    labelStyle: { fill: "#6B7280", fontSize: 11, fontWeight: 600 },
    labelBgPadding: [4, 2],
    labelBgBorderRadius: 6,
    labelBgStyle: { fill: "#FFFFFF", fillOpacity: 0.95, stroke: "#E5E7EB" },
    style:
      edgeType === "controlFlow"
        ? { stroke: "#9CA3AF", strokeWidth: 1.5, strokeDasharray: "6 4" }
        : { stroke: "#6B7280", strokeWidth: 1.8 }
  };
}

function KeywordTrace({ runStages }) {
  const lookupOutput = runStages.find((s) => s.id === "lookup")?.output;
  const trace = lookupOutput?.lookup_debug;
  if (!trace) {
    return (
      <div className="keyword-trace">
        <h4>키워드 탐색 추적</h4>
        <p className="detail">질문 실행 후, 온톨로지 검색 단계에서 키워드 우선순위가 표시됩니다.</p>
      </div>
    );
  }
  return (
    <div className="keyword-trace">
      <h4>키워드 탐색 추적</h4>
      <div className="trace-row">
        <span>질문 키워드</span>
        <div className="chip-wrap">
          {(trace.query_terms || []).map((term) => (
            <span key={`q-${term}`} className="kw-chip base">{term}</span>
          ))}
        </div>
      </div>
      <div className="trace-row">
        <span>우선 탐색 키워드</span>
        <div className="chip-wrap">
          {(trace.prioritized_terms || []).map((term) => (
            <span key={`p-${term}`} className="kw-chip priority">{term}</span>
          ))}
        </div>
      </div>
      <div className="trace-candidates">
        {(trace.candidates || []).slice(0, 5).map((c) => (
          <article key={c.id} className="candidate-item">
            <strong>{c.label || c.id}</strong>
            <p className="detail">
              matched_terms: {(c.matched_terms || []).join(", ") || "-"} | fields:{" "}
              {(c.matched_fields || []).join(", ") || "-"} | score: {c.score}
            </p>
          </article>
        ))}
      </div>
    </div>
  );
}
