#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [[ $# -gt 1 || ( $# -eq 1 && "$1" != '--sample' ) ]]; then
  echo 'Usage: start_collection.sh [--sample]' >&2
  exit 2
fi
RUN_DIR="$("${PIPELINE_PYTHON:-$ROOT/.venv/bin/python}" - "${1:-}" <<'PY'
import datetime as dt, shutil, sys, uuid
from pathlib import Path
from pipeline_io import load, now, save
project = load('config/project.json')
if not all(isinstance(project.get(key), str) and project[key].strip() for key in ('publication_name', 'topic', 'audience', 'central_question')):
    raise SystemExit('Project configuration requires four nonempty strings')
sources = load('config/sources.json')
if not isinstance(sources, list) or not sources:
    raise SystemExit('Source configuration must be a nonempty array')
stamp = now()
directory = Path('runs') / (dt.datetime.fromisoformat(stamp.replace('Z','+00:00')).strftime('%Y%m%dT%H%M%SZ') + '-collection-' + uuid.uuid4().hex[:6])
directory.mkdir(parents=True)
shutil.copytree('config', directory / 'config')
shutil.copytree('prompts', directory / 'prompts')
sample = sys.argv[1] == '--sample'
if sample:
    shutil.copyfile(directory / 'config/sources.json', directory / 'config/sources.full.json')
    selected = [dict(source, limit=1) for source in sources if source['source_id'] in ('google-ai', 'matt-wolfe-youtube', 'latent-space-podcast')]
    if {source['kind'] for source in selected} != {'feed', 'youtube', 'podcast'}:
        raise SystemExit('Sample configuration requires Google AI, Matt Wolfe, and Latent Space')
    save(directory / 'config/sources.json', selected)
previous = sorted(path for path in Path('runs').iterdir() if path != directory and (path / 'run.json').is_file())
save(directory / 'run.json', {'run_id': directory.name, 'started_at': stamp, 'as_of_date': stamp[:10],
    'mode': 'live', 'previous_run_id': previous[-1].name if previous else None,
    'scope': 'collection_sample' if sample else 'collection_only',
    'note': 'Collection-stage execution only; does not demonstrate a completed publication pipeline.'})
print(directory)
PY
)"
bash data/store.sh init
echo "Collection artifacts: $RUN_DIR" >&2
status=0
bash workflows/collect_sources.sh "$RUN_DIR" || status=$?
bash reporting/summarize_run.sh "$RUN_DIR" > "$RUN_DIR/summary.json"
cat "$RUN_DIR/summary.json"
exit "$status"
