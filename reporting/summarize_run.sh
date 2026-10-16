#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
exec "${PIPELINE_PYTHON:-$ROOT/.venv/bin/python}" reporting/summarize_run.py "$@"
