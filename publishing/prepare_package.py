"""Assemble approved, unchanged material; never render, publish, or approve it."""
import datetime as dt
from pathlib import Path
import shutil
import sys
from urllib.parse import urlsplit
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline_io import ROOT, component, digest, emit, load, local_path, now, save
from review.check_content import assess


def approved_review(directory, current=None):
    current = current or assess(directory)
    if current.get('passed') is not True:
        raise RuntimeError('Content checks have blocking issues; repair them before packaging')
    if not (directory / 'review.json').is_file():
        raise RuntimeError('Missing retained review.json; run content checks')
    recorded = load(directory / 'review.json')
    if not isinstance(recorded, dict) or recorded.get('passed') is not True or recorded.get('review_id') != current['review_id']:
        raise RuntimeError('Review is stale; rerun content checks on the current inputs')
    if not (directory / 'approval.json').is_file():
        raise RuntimeError('Student approval is missing; review the actual content and supply approval.json')
    approval = load(directory / 'approval.json')
    required = ('review_id', 'decision', 'reviewer', 'reviewed_at', 'notes')
    if not isinstance(approval, dict) or not all(isinstance(approval.get(k), str) for k in required) or not all(approval[k].strip() for k in required if k != 'notes'):
        raise RuntimeError('Approval requires review_id, decision, reviewer, reviewed_at, and notes')
    if approval['decision'] != 'approve' or approval['review_id'] != current['review_id']:
        raise RuntimeError('Student approval is stale or requests revision; no package may be produced')
    if approval['reviewer'].strip().casefold() in ('assistant', 'codex', 'ai'):
        raise RuntimeError('Only the student supplies human approval')
    try:
        when = dt.datetime.fromisoformat(approval['reviewed_at'].replace('Z', '+00:00'))
        if when.tzinfo is None or when.utcoffset() != dt.timedelta(0) or when > dt.datetime.now(dt.timezone.utc):
            raise ValueError('Approval time must be a non-future UTC timestamp')
    except ValueError:
        raise RuntimeError('reviewed_at must be a valid non-future UTC timestamp') from None
    return current, approval


def package_current(directory, current=None):
    current, approval = approved_review(directory, current)
    manifest = load(directory / 'package/manifest.json')
    if not isinstance(manifest, dict) or manifest.get('review_id') != current['review_id'] or manifest.get('approval_digest') != digest(approval):
        raise RuntimeError('Package does not match the current review and approval')
    expected = {str((directory / 'package' / kind / (p + suffix)).relative_to(ROOT)) for p in ('01', '02', '03')
                for kind, suffix in (('articles', '.md'), ('video_scripts', '.md'), ('source_notes', '.json'))}
    assets = manifest.get('assets')
    if not isinstance(assets, list) or len(assets) != 9 or not all(isinstance(a, dict) and isinstance(a.get('path'), str) for a in assets) or {a['path'] for a in assets} != expected:
        raise RuntimeError('Package is missing required assets')
    for asset in assets:
        if asset.get('piece_id') not in ('01', '02', '03') or asset.get('kind') not in ('articles', 'video_scripts', 'source_notes'):
            raise RuntimeError('Invalid packaged piece or asset kind')
        suffix = '.json' if asset['kind'] == 'source_notes' else '.md'
        source = directory / asset['kind'] / (asset['piece_id'] + suffix)
        expected_path = str((directory / 'package' / asset['kind'] / source.name).relative_to(ROOT))
        if asset['path'] != expected_path or asset.get('content_digest') != current['artifact_digests'].get(str(source.relative_to(ROOT))):
            raise RuntimeError('Packaged content is not the approved source snapshot')
        if digest(local_path(asset['path']).read_text()) != asset.get('content_digest'):
            raise RuntimeError('A packaged asset changed; recheck and repackage')
    return manifest


def publication_links(directory):
    path = directory / 'package/publication_links.json'
    if not path.exists():
        return [{'piece_id': p, 'substack_url': None, 'youtube_url': None} for p in ('01', '02', '03')]
    value = load(path)
    if not isinstance(value, list) or len(value) != 3 or not all(isinstance(x, dict) for x in value) or {x.get('piece_id') for x in value} != {'01', '02', '03'}:
        raise RuntimeError('Existing publication links are malformed; preserve and repair them')
    for row in value:
        for key in ('substack_url', 'youtube_url'):
            url = row.get(key)
            if key not in row or (url is not None and not isinstance(url, str)):
                raise RuntimeError('Publication URLs must be strings or null')
            if url is not None:
                parts = urlsplit(url)
                if parts.scheme not in ('http', 'https') or not parts.hostname or parts.username or parts.password:
                    raise RuntimeError('Publication URLs must be public HTTP(S) links without credentials')
    return value


def prepare(directory, receipt):
    current, approval = approved_review(directory)
    links = publication_links(directory)
    target = directory / 'package'
    staging = directory / ('package-staging-' + uuid.uuid4().hex)
    staging.mkdir()
    assets = []
    # ponytail: sequential publication handoff; serialize callers if concurrent packaging is needed.
    for piece in ('01', '02', '03'):
        for kind, suffix in (('articles', '.md'), ('video_scripts', '.md'), ('source_notes', '.json')):
            source = directory / kind / (piece + suffix)
            destination = staging / kind / source.name
            destination.parent.mkdir(exist_ok=True)
            shutil.copyfile(source, destination)
            content_digest = digest(destination.read_text())
            if content_digest != current['artifact_digests'].get(str(source.relative_to(ROOT))):
                raise RuntimeError('Content changed during packaging; staging retained for inspection')
            assets.append({'piece_id': piece, 'kind': kind, 'path': str((target / kind / source.name).relative_to(ROOT)), 'content_digest': content_digest})
    if assess(directory)['review_id'] != current['review_id'] or digest(load(directory / 'approval.json')) != digest(approval):
        raise RuntimeError('Reviewed inputs or approval changed during packaging; staging retained')
    save(staging / 'publication_links.json', links)
    save(staging / 'review.json', current); save(staging / 'approval.json', approval)
    (staging / 'MANUAL_STEPS.md').write_text('''# Production and Publication Handoff

This package contains approved drafts and source notes. Videos have not been
rendered and content has not been published by this pipeline.

1. Produce each 3–5 minute video in Google Vids or HeyGen using its script.
   Verify pacing, spoken claims, source captions, and planned visuals. Label
   AI-generated presentation where used.
2. Publish the three articles on Substack with shareable, unpaid access.
3. Upload the corresponding videos to YouTube, public or unlisted. Include
   the article URL and source references in each description.
4. Link each article to its video. Fill publication_links.json with real URLs
   and verify that course staff can open them.
5. Complete the student review record, two full runs on different days,
   the separate 4–6 minute technical demonstration, and submission documentation.

Repackaging archives the previous package instead of deleting it, and preserves
entered publication links. Manually rendered assets in an older package remain
in that archive; use the current approved scripts for production.
''')
    manifest = {'run_id': load(directory / 'run.json')['run_id'], 'review_id': current['review_id'],
                'approval_digest': digest(approval), 'prepared_at': now(), 'assets': assets,
                'publication_links_path': str((target / 'publication_links.json').relative_to(ROOT)),
                'manual_actions': ['Produce videos in Google Vids or HeyGen.', 'Publish Substack/YouTube pairs and cross-links.', 'Record real publication links and verify access.']}
    save(staging / 'manifest.json', manifest)
    backup = None
    if target.exists():
        backup = directory / ('package-backup-' + uuid.uuid4().hex)
        target.rename(backup)
    try:
        staging.rename(target)
    except OSError:
        if backup: backup.rename(target)
        raise
    receipt.update(input_count=3, output_count=1, review_id=current['review_id'], archived_package=str(backup) if backup else None)
    emit(manifest)


if __name__ == '__main__':
    component('prepare_package', prepare)
