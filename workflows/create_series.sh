#!/usr/bin/env bash
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [[ $# -ne 1 || ! -f "$1/run.json" ]]; then
  echo 'Usage: create_series.sh RUN_DIR' >&2
  exit 2
fi
RUN_DIR="$1"
if [[ -f "$RUN_DIR/approval.json" ]]; then
  echo 'Preserve reviewed content: create a new run to regenerate, or use run.sh --package to recheck and package.' >&2
  exit 2
fi
started_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
status=0
for spec in 'editorial/select_items eligible decisions' 'editorial/create_briefs decisions briefs' 'content/write_articles briefs articles' 'content/write_video_scripts briefs video_scripts'; do
  read -r script input output <<< "$spec"
  temporary="$RUN_DIR/$output.jsonl.pending-$$"
  cat "$RUN_DIR/$input.jsonl" | bash "$script.sh" "$RUN_DIR" > "$temporary"
  code=$?
  if (( code != 0 )); then
    status=$code
    echo "Series stopped at $script; partial stream retained at $temporary" >&2
    break
  fi
  mv "$temporary" "$RUN_DIR/$output.jsonl" || { status=1; break; }
done
if (( status == 0 )); then
  temporary="$RUN_DIR/review.json.pending-$$"
  bash review/check_content.sh "$RUN_DIR" > "$temporary"
  status=$?
  if (( status == 0 )); then
    mv "$temporary" "$RUN_DIR/review.json" || status=1
    if (( status == 0 )); then
      "${PIPELINE_PYTHON:-$ROOT/.venv/bin/python}" - "$RUN_DIR/review.json" <<'PY'
import json, sys
with open(sys.argv[1]) as stream:
    review = json.load(stream)
if review.get('passed') is not True:
    print('Content assessment completed with blocking issues; inspect review.json.', file=sys.stderr)
    raise SystemExit(1)
PY
      status=$?
    fi
  fi
fi
"${PIPELINE_PYTHON:-$ROOT/.venv/bin/python}" pipeline_io.py workflow_receipt "$RUN_DIR" create_series "$started_at" "$status" eligible.jsonl video_scripts.jsonl
receipt_status=$?
if (( receipt_status != 0 )); then status=$receipt_status; fi
exit "$status"
