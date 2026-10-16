"""Assess current drafts and fingerprint exact reviewed inputs; never approve them."""
import io
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from content.drafts import WPM, check_ids, inspect_article, inspect_scenes, load_inputs, render_script, source_footer, source_notes
from pipeline_io import ROOT, component, digest, emit, load, records


def assess(directory):
    directory = Path(directory).resolve()
    issues, inputs, metrics = [], {}, {}
    def issue(artifact, explanation, piece=None, severity='error'):
        issues.append({'piece_id': piece, 'artifact': artifact, 'severity': severity, 'explanation': explanation})
    def read(path):
        key = str(path.relative_to(ROOT))
        try:
            value = path.read_text(); inputs[key] = value; return value
        except OSError:
            inputs[key] = None; issue(key, 'Required artifact is missing or unreadable.'); return None
    run_text = read(directory / 'run.json')
    for name in ('briefs.jsonl', 'eligible.jsonl', 'decisions.jsonl'):
        read(directory / name)
    try:
        run = json.loads(run_text)
        briefs, evidence = load_inputs(directory)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
        issue('briefs/evidence', 'Cannot validate retained briefs and evidence: ' + str(error))
        return {'review_id': digest(inputs), 'passed': False, 'issues': issues, 'metrics': metrics}
    inputs['as_of_date'] = run['as_of_date']
    inputs['referenced_evidence'] = evidence  # Includes full passages/segments: changed assets invalidate approval.
    manifests = {}
    for kind in ('articles', 'video_scripts'):
        raw = read(directory / (kind + '.jsonl'))
        try:
            rows = list(records(io.StringIO(raw)))
            if len(rows) != 3 or {r.get('piece_id') for r in rows} != {'01', '02', '03'}:
                raise ValueError('Exactly three unique piece records are required')
            manifests[kind] = {r['piece_id']: r for r in rows}
        except (ValueError, TypeError) as error:
            issue(kind + '.jsonl', 'Invalid manifest: ' + str(error)); manifests[kind] = {}
    for brief in briefs:
        piece = brief['piece_id']; allowed = {c['claim_id'] for c in brief['claims']}
        notes = source_notes(brief, evidence, run['as_of_date'])
        raw_notes = read(directory / 'source_notes' / (piece + '.json'))
        try:
            if digest(json.loads(raw_notes)) != digest(notes):
                raise ValueError('Source notes differ from exact brief evidence')
        except (ValueError, TypeError) as error:
            issue('source_notes/' + piece + '.json', str(error), piece)
        metrics[piece] = {}
        for kind in ('articles', 'video_scripts'):
            path = directory / kind / (piece + '.md'); text = read(path)
            row = manifests[kind].get(piece)
            try:
                if not isinstance(row, dict) or set(row) != {'piece_id', 'path', 'claim_ids'} or row['path'] != str(path.relative_to(ROOT)):
                    raise ValueError('Manifest must point to this run and its matching piece')
                check_ids(row['claim_ids'], allowed, complete=True)
                if not isinstance(text, str) or not text.startswith('# ' + brief['title'] + '\n') or source_footer(notes).strip() not in text:
                    raise ValueError('Draft title or readable source notes are missing or inconsistent')
                if kind == 'articles':
                    body = text.split('\n', 1)[1].split('## Sources', 1)[0].strip()
                    words = inspect_article(body, brief, enforce_length=False)
                    metrics[piece]['article_words'] = words
                    if not 600 <= words <= 900:
                        issue(kind, f'Approximate article target is 600–900 words; found {words}.', piece, 'warning')
                else:
                    raw_scenes = read(directory / 'video_scenes' / (piece + '.json'))
                    scenes = json.loads(raw_scenes)
                    if set(scenes) != {'piece_id', 'scenes'} or scenes['piece_id'] != piece:
                        raise ValueError('Scene record belongs to the wrong piece')
                    words = inspect_scenes(scenes['scenes'], brief, enforce_length=False)
                    if not text.startswith(render_script(scenes, brief, enforce_length=False)):
                        raise ValueError('Video Markdown differs from its retained scene record')
                    metrics[piece].update(spoken_words=words, estimated_minutes=round(words / WPM, 2))
                    if not 3 <= words / WPM <= 5:
                        issue(kind, 'Estimated narration falls outside the 3–5 minute target.', piece, 'warning')
            except (ValueError, KeyError, TypeError) as error:
                issue(kind + '/' + piece + '.md', str(error), piece)
        issue('human_review', 'Confirm semantic support, independent sources, novelty, counterarguments, sponsorship disclosures, and fidelity between article and narration; mechanical claim coverage does not prove factual consistency.', piece, 'warning')
    issue('media', 'Verify cited recordings and transcript accuracy; estimated video timing excludes production pauses and transitions.', severity='warning')
    return {'review_id': digest(inputs), 'passed': not any(i['severity'] == 'error' for i in issues),
            'issues': issues, 'metrics': metrics, 'human_approval': False,
            'artifact_digests': {key: digest(value) for key, value in inputs.items() if isinstance(value, str)},
            'scope': 'Mechanical assessment of three article/script pairs and their exact evidence. Student editorial review is required.'}


def check(directory, receipt):
    result = assess(directory)
    emit(result); receipt['input_count'] = 3; receipt['output_count'] = 1


if __name__ == '__main__':
    component('check_content', check)
