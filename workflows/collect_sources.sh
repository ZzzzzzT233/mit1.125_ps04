#!/usr/bin/env bash
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [[ $# -ne 1 || ! -f "$1/run.json" ]]; then
  echo 'Usage: collect_sources.sh RUN_DIR' >&2
  exit 2
fi
RUN_DIR="$1"
mkdir -p "$RUN_DIR/candidates"
status=0
started_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
for pair in 'feeds fetch_feeds' 'youtube fetch_youtube' 'podcasts fetch_podcasts'; do
  read -r stream collector <<< "$pair"
  bash "collectors/$collector.sh" "$RUN_DIR" > "$RUN_DIR/candidates/$stream.jsonl"
  code=$?
  if (( code > status )); then status=$code; fi
done
cat "$RUN_DIR/candidates/feeds.jsonl" "$RUN_DIR/candidates/youtube.jsonl" "$RUN_DIR/candidates/podcasts.jsonl" > "$RUN_DIR/candidates.jsonl"
cat "$RUN_DIR/candidates.jsonl" | bash processing/extract_content.sh "$RUN_DIR" > "$RUN_DIR/items.jsonl"
code=$?
if (( code > status )); then status=$code; fi
bash data/store.sh upsert "$RUN_DIR" < "$RUN_DIR/items.jsonl" > "$RUN_DIR/changes.jsonl"
code=$?
if (( code > status )); then status=$code; fi
bash data/store.sh list > "$RUN_DIR/corpus.jsonl"
code=$?
if (( code > status )); then status=$code; fi
bash processing/filter_items.sh "$RUN_DIR" < "$RUN_DIR/corpus.jsonl" > "$RUN_DIR/eligible.jsonl"
code=$?
if (( code > status )); then status=$code; fi
"${PIPELINE_PYTHON:-$ROOT/.venv/bin/python}" - "$RUN_DIR" "$started_at" "$status" <<'PY'
import sys, uuid
from pathlib import Path
from pipeline_io import now, save
directory = Path(sys.argv[1])
count = lambda path: sum(bool(line.strip()) for line in path.read_text().splitlines())
code = int(sys.argv[3])
save(directory / 'logs' / f'collect_sources-{uuid.uuid4().hex}.json', {
    'stage': 'collect_sources', 'status': 'completed' if code == 0 else 'incomplete',
    'exit_code': code, 'started_at': sys.argv[2], 'finished_at': now(),
    'input_count': count(directory / 'candidates.jsonl'),
    'output_count': count(directory / 'eligible.jsonl'), 'tools': ['Bash'], 'models': [],
    'cost_usd': None, 'errors': [] if code == 0 else ['One or more collection components failed; inspect their receipts.']})
PY
exit "$status"
