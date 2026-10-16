#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [[ $# -ne 0 ]]; then
  echo 'Usage: start_selection.sh' >&2
  exit 2
fi
RUN_DIR="$("${PIPELINE_PYTHON:-$ROOT/.venv/bin/python}" - <<'PY'
import datetime as dt, shutil, uuid
from pathlib import Path
from pipeline_io import now, save
stamp = now()
previous = sorted(p for p in Path('runs').iterdir() if (p / 'run.json').is_file()) if Path('runs').exists() else []
directory = Path('runs') / (dt.datetime.fromisoformat(stamp.replace('Z', '+00:00')).strftime('%Y%m%dT%H%M%SZ') + '-selection-' + uuid.uuid4().hex[:6])
directory.mkdir(parents=True)
shutil.copytree('config', directory / 'config')
shutil.copytree('prompts', directory / 'prompts')
save(directory / 'run.json', {'run_id': directory.name, 'started_at': stamp, 'as_of_date': stamp[:10],
    'mode': 'live', 'previous_run_id': previous[-1].name if previous else None, 'scope': 'selection_only',
    'note': 'Live editorial model execution on retained evidence exported through data/store.sh and re-filtered for this UTC date. Sources are not recollected. This is not a complete publication-pipeline run.'})
print(directory)
PY
)"
echo "Selection artifacts: $RUN_DIR" >&2
status=0
bash data/store.sh list > "$RUN_DIR/corpus.jsonl" || status=$?
if (( status == 0 )); then
  bash processing/filter_items.sh "$RUN_DIR" < "$RUN_DIR/corpus.jsonl" > "$RUN_DIR/eligible.jsonl" || status=$?
fi
if (( status == 0 )); then
  bash editorial/select_items.sh "$RUN_DIR" < "$RUN_DIR/eligible.jsonl" > "$RUN_DIR/decisions.jsonl" || status=$?
fi
bash reporting/summarize_run.sh "$RUN_DIR" > "$RUN_DIR/summary.json"
cat "$RUN_DIR/summary.json"
exit "$status"
