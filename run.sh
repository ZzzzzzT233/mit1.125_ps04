#!/usr/bin/env bash
set -uo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
PYTHON="${PIPELINE_PYTHON:-$ROOT/.venv/bin/python}"
if [[ $# -ne 0 && ( $# -ne 2 || "$1" != '--package' ) ]]; then
  echo 'Usage: run.sh [--package RUN_DIR]' >&2
  exit 2
fi
started_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
status=0
if [[ $# -eq 2 ]]; then
  RUN_DIR="$2"
  "$PYTHON" - "$RUN_DIR" <<'PY'
import sys
from pipeline_io import run_dir
run_dir(sys.argv[1])
PY
  code=$?
  if (( code != 0 )); then exit 2; fi
  temporary="$RUN_DIR/review.json.pending-$$"
  if bash review/check_content.sh "$RUN_DIR" > "$temporary"; then
    mv "$temporary" "$RUN_DIR/review.json" || status=1
    if (( status == 0 )); then
      temporary="$RUN_DIR/package-manifest.json.pending-$$"
      if bash publishing/prepare_package.sh "$RUN_DIR" > "$temporary"; then
        mv "$temporary" "$RUN_DIR/package-manifest.json" || status=1
      else
        status=$?
      fi
    fi
  else
    status=$?
  fi
  stage_name=run_package
else
  RUN_DIR="$("$PYTHON" - <<'PY'
import datetime as dt, shutil, uuid
from pathlib import Path
from urllib.parse import urlsplit
from editorial.select_items import validate_settings
from pipeline_io import load, now, save
project = load('config/project.json')
if not all(isinstance(project.get(k), str) and project[k].strip() for k in ('publication_name', 'topic', 'audience', 'central_question')):
    raise SystemExit('Project configuration requires four nonempty strings')
sources = load('config/sources.json')
if not isinstance(sources, list) or not sources:
    raise SystemExit('Sources must be a nonempty array')
seen = set()
for source in sources:
    if not isinstance(source, dict) or not all(isinstance(source.get(k), str) and source[k].strip() for k in ('source_id', 'publisher_id', 'url')) or source.get('kind') not in ('feed', 'youtube', 'podcast'):
        raise SystemExit('Invalid source definition')
    if source['source_id'] in seen or type(source.get('limit', 20)) is not int or source.get('limit', 20) < 1:
        raise SystemExit('Source IDs must be unique and limits positive integers')
    seen.add(source['source_id'])
    for url in (source['url'], source.get('discovery_feed_url', source['url'])):
        parts = urlsplit(url)
        if parts.scheme not in ('https', 'http') or not parts.hostname or parts.username or parts.password:
            raise SystemExit('Source URLs must be public HTTP(S) URLs without credentials')
if {s['kind'] for s in sources} != {'feed', 'youtube', 'podcast'}:
    raise SystemExit('Configure all three required input kinds')
validate_settings(load('config/editorial.json'))
for name in ('config/editorial_policy.md', 'prompts/select_items.md', 'prompts/create_briefs.md', 'prompts/write_articles.md', 'prompts/write_video_scripts.md'):
    if not Path(name).read_text().strip():
        raise SystemExit('Policy and all four prompts must be populated')
stamp = now()
previous = []
if Path('runs').exists():
    for path in Path('runs').glob('*/run.json'):
        value = load(path)
        if value.get('mode') == 'live': previous.append((value.get('started_at', ''), path.parent.name))
directory = Path('runs') / (dt.datetime.fromisoformat(stamp.replace('Z', '+00:00')).strftime('%Y%m%dT%H%M%SZ') + '-full-' + uuid.uuid4().hex[:6])
directory.mkdir(parents=True)
shutil.copytree('config', directory / 'config'); shutil.copytree('prompts', directory / 'prompts')
save(directory / 'run.json', {'run_id': directory.name, 'started_at': stamp, 'as_of_date': stamp[:10], 'mode': 'live',
    'scope': 'full_pipeline', 'previous_run_id': max(previous)[1] if previous else None,
    'note': 'Full collection-to-draft execution, ending with content checks and student review. Video production and publication remain manual.'})
print(directory)
PY
)"
  code=$?
  if (( code != 0 )); then exit 2; fi
  echo "Run artifacts: $RUN_DIR" >&2
  if bash data/store.sh init; then
    if bash workflows/collect_sources.sh "$RUN_DIR"; then :; else status=$?; fi
    if [[ -f "$RUN_DIR/eligible.jsonl" ]]; then
      if bash workflows/create_series.sh "$RUN_DIR"; then :; else
        code=$?
        if (( code > status )); then status=$code; fi
      fi
    fi
  else
    status=$?
  fi
  stage_name=run_pipeline
fi
"$PYTHON" pipeline_io.py workflow_receipt "$RUN_DIR" "$stage_name" "$started_at" "$status" eligible.jsonl video_scripts.jsonl || status=1
temporary="$RUN_DIR/summary.json.pending-$$"
if bash reporting/summarize_run.sh "$RUN_DIR" > "$temporary"; then
  mv "$temporary" "$RUN_DIR/summary.json" || status=1
  cat "$RUN_DIR/summary.json"
else
  code=$?
  if (( code > status )); then status=$code; fi
fi
exit "$status"
