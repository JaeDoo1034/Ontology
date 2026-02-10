#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

if [[ -f "${ROOT_DIR}/set.env" ]]; then
  # shellcheck disable=SC1091
  source "${ROOT_DIR}/set.env" >/dev/null 2>&1 || true
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "[setup_method_examples] uv is required. Install uv first."
  exit 1
fi

DB_PATH="${SQLITE_PATH:-./data/ontology_memori.db}"

echo "[setup_method_examples] Syncing base + research extras..."
uv sync --extra research-all

echo "[setup_method_examples] Initializing DB: ${DB_PATH}"
uv run ontology-llm init-db --db "${DB_PATH}"

echo "[setup_method_examples] Ingesting method ontologies..."
for yaml_path in data/ontologies/method*.yaml; do
  echo "  - ${yaml_path}"
  uv run ontology-llm ingest --db "${DB_PATH}" --yaml "${yaml_path}"
done

echo "[setup_method_examples] Done."
echo "[setup_method_examples] Example run:"
echo "  uv run ontology-llm chat \"빠나 우유 가격 알려줘\" --db \"${DB_PATH}\" --method method1"
echo "  uv run ontology-llm exp \"빠나 우유가 왜 3000원인지 관계 근거까지 설명해줘\" --method method3 --auto-ingest --db \"${DB_PATH}\""
