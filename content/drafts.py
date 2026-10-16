"""Two focused drafting modes share evidence loading, transport, and source notes."""
import datetime as dt
import json
import math
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from editorial.create_briefs import english, object_schema, timestamp, validate_briefs
from editorial.select_items import PIECES, load_evidence, model_response, response_text, validate_decisions, validate_settings
from pipeline_io import ROOT, component, digest, emit, load, records, save

WPM = 135


def word_count(text):
    text = re.sub(r'<!--.*?-->', '', text, flags=re.S)
    text = re.sub(r'\[\^\d+\]', '', text)
    return len(re.findall(r"\b\w+(?:['’.-]\w+)*\b", text))


def load_inputs(directory, supplied=None):
    with (directory / 'briefs.jsonl').open() as stream:
        briefs = list(records(stream))
    if supplied is not None and digest(supplied) != digest(briefs):
        raise ValueError('Draft input must match the retained brief stream')
    with (directory / 'eligible.jsonl').open() as stream:
        items = list(records(stream))
    with (directory / 'decisions.jsonl').open() as stream:
        decisions = list(records(stream))
    run = load(directory / 'run.json')
    evidence = load_evidence(items, dt.date.fromisoformat(run['as_of_date']))
    validate_decisions({'decisions': decisions}, items)
    accepted = {d['item_id'] for d in decisions if d['decision'] == 'accept'}
    evidence = [i for i in evidence if i['item_id'] in accepted]
    briefs = validate_briefs({'briefs': briefs, 'blocking_reasons': []}, evidence)
    used = {ref['item_id'] for b in briefs for c in b['claims'] for ref in c['evidence']}
    return briefs, [i for i in evidence if i['item_id'] in used]


def draft_schema(kind, briefs):
    string = {'type': 'string'}
    ids = {'type': 'array', 'items': {'type': 'string', 'enum': [c['claim_id'] for b in briefs for c in b['claims']]}}
    fields = {'piece_id': {'type': 'string', 'enum': list(PIECES)}}
    if kind == 'articles':
        fields.update(markdown=string, claim_ids=ids)
    else:
        fields['scenes'] = {'type': 'array', 'items': object_schema({'narration': string, 'visual': string, 'claim_ids': ids})}
    return object_schema({'drafts': {'type': 'array', 'items': object_schema(fields)}})


def check_ids(value, allowed, complete=False):
    if not isinstance(value, list) or any(not isinstance(x, str) or x not in allowed for x in value) or len(value) != len(set(value)):
        raise ValueError('Unknown, wrong-piece, or repeated claim ID')
    if complete and set(value) != allowed:
        raise ValueError('Every brief claim must be covered')


def inspect_article(body, brief, enforce_length=True):
    if not english(body) or re.search(r'https?://|\]\(|^# |^\[\^\d+\]:|^## Sources', body, flags=re.M | re.I):
        raise ValueError('Article body must be English prose without a title, URLs, or source definitions')
    expected = {c['claim_id'] for c in brief['claims']}
    markers = set(re.findall(r'<!--\s*claim:([^\s>]+)\s*-->', body))
    pairs = re.findall(r'\[\^(\d+)\]\s*<!--\s*claim:([^\s>]+)\s*-->', body)
    if markers != expected or {identity for _, identity in pairs} != expected or any(identity != brief['piece_id'] + '-c' + number for number, identity in pairs):
        raise ValueError('Each article claim needs its matching readable footnote and hidden marker')
    if set(re.findall(r'\[\^(\d+)\]', body)) != {c.split('-c')[1] for c in expected}:
        raise ValueError('Unexpected or missing article footnote')
    words = word_count(body)
    if enforce_length and not 600 <= words <= 900:
        raise ValueError(f"Article {brief['piece_id']} has {words} words; expected 600–900")
    return words


def inspect_scenes(scenes, brief, enforce_length=True):
    if not isinstance(scenes, list) or not 4 <= len(scenes) <= 7:
        raise ValueError('A video needs four to seven scenes')
    allowed = {c['claim_id'] for c in brief['claims']}
    used = set(); words = 0
    for scene in scenes:
        if not isinstance(scene, dict) or set(scene) != {'narration', 'visual', 'claim_ids'} or not english(scene['narration']) or not english(scene['visual']):
            raise ValueError('Scene needs English narration, visual directions, and claim IDs')
        if re.search(r'https?://|<!--|\[\^', scene['narration']):
            raise ValueError('Narration must not contain source metadata or URLs')
        check_ids(scene['claim_ids'], allowed)
        used.update(scene['claim_ids']); words += word_count(scene['narration'])
    if used != allowed:
        raise ValueError('Video must cover the same material claims as its article')
    if enforce_length and not 3 <= words / WPM <= 5:
        raise ValueError(f"Video {brief['piece_id']} has {words} spoken words; expected 3–5 minutes at {WPM} words/minute")
    return words


def validate_drafts(value, kind, briefs):
    if not isinstance(value, dict) or set(value) != {'drafts'} or not isinstance(value['drafts'], list) or len(value['drafts']) != 3:
        raise ValueError('Exactly three draft records are required')
    by_piece = {b['piece_id']: b for b in briefs}; found = {}
    for draft in value['drafts']:
        keys = {'piece_id', 'markdown', 'claim_ids'} if kind == 'articles' else {'piece_id', 'scenes'}
        if not isinstance(draft, dict) or set(draft) != keys or not isinstance(draft['piece_id'], str) or draft['piece_id'] not in by_piece or draft['piece_id'] in found:
            raise ValueError('Malformed, unknown, or duplicate draft piece')
        brief = by_piece[draft['piece_id']]
        if kind == 'articles':
            check_ids(draft['claim_ids'], {c['claim_id'] for c in brief['claims']}, complete=True)
            inspect_article(draft['markdown'], brief)
        else:
            inspect_scenes(draft['scenes'], brief)
        found[draft['piece_id']] = draft
    return [found[p] for p in PIECES]


def normalize_article_citations(value, briefs):
    """Canonical footnote numbers follow explicit claim markers, not appearance order."""
    allowed = {b['piece_id']: {c['claim_id'] for c in b['claims']} for b in briefs}
    events = []
    for draft in value.get('drafts', []) if isinstance(value, dict) else []:
        if not isinstance(draft, dict) or not isinstance(draft.get('markdown'), str) or draft.get('piece_id') not in allowed:
            continue
        def replace(match):
            number, identity = match.groups()
            if identity not in allowed[draft['piece_id']]:
                return match.group(0)
            canonical = identity.split('-c')[1]
            if number != canonical:
                events.append({'piece_id': draft['piece_id'], 'claim_id': identity, 'old_footnote': number, 'new_footnote': canonical})
            return '[^' + canonical + ']<!-- claim:' + identity + ' -->'
        draft['markdown'] = re.sub(r'\[\^(\d+)\]\s*<!--\s*claim:([^\s>]+)\s*-->', replace, draft['markdown'])
    return events


def source_notes(brief, evidence, as_of):
    items = {i['item_id']: i for i in evidence}
    notes = {'piece_id': brief['piece_id'], 'as_of_date': as_of, 'claims': []}
    for claim in brief['claims']:
        refs = []
        for ref in claim['evidence']:
            item = items[ref['item_id']]
            entry = dict(ref, title=item['title'], url=item['url'], publisher_id=item['publisher_id'], published_at=item['published_at'])
            if ref['locator']['type'] == 'segment':
                s = next(s for s in item['segments'] if s['segment_id'] == ref['locator']['segment_id'])
                entry.update(start_seconds=s['start_seconds'], end_seconds=s['end_seconds'])
            refs.append(entry)
        notes['claims'].append({'claim_id': claim['claim_id'], 'statement': claim['statement'], 'type': claim['type'], 'evidence': refs})
    return notes


def source_footer(notes):
    lines = ['## Sources', '', f"Evidence as of {notes['as_of_date']} UTC. Access conditions may change after publication.", '']
    for claim in notes['claims']:
        refs = []
        for ref in claim['evidence']:
            text = f"[{ref['title']}]({ref['url']})"
            if ref['locator']['type'] == 'segment':
                text += f" ({timestamp(ref['start_seconds'])}–{timestamp(ref['end_seconds'])})"
            if text not in refs:
                refs.append(text)
        number = claim['claim_id'].split('-c')[1]
        lines += [f"[^{number}]: " + '; '.join(refs) + '.', '']
    lines += [f"<!-- source_notes_sha256:{digest(notes)} -->", '']
    return '\n'.join(lines)


def render_script(draft, brief, enforce_length=True):
    lines = [f"# {brief['title']}", '', 'Production draft for Google Vids or HeyGen. Planned visuals have not been generated. Student review and final approval are pending.', '',
             f"Estimated narration: {inspect_scenes(draft['scenes'], brief, enforce_length=enforce_length) / WPM:.2f} minutes at {WPM} words/minute; check pacing, pauses, and transitions during production.", '']
    elapsed = 0
    for number, scene in enumerate(draft['scenes'], 1):
        end = elapsed + math.ceil(word_count(scene['narration']) / WPM * 60)
        lines += [f'## Scene {number} — {timestamp(elapsed)}–{timestamp(end)}', '', '**Narration**', '']
        lines += ['<!-- claim:' + claim + ' -->' for claim in scene['claim_ids']]
        lines += [scene['narration'], '', '**Visual direction**', '', scene['visual'], '']
        if scene['claim_ids']:
            lines += ['**Sources for this scene:** ' + ', '.join('[^' + c.split('-c')[1] + ']' for c in scene['claim_ids']), '']
        elapsed = end
    return '\n'.join(lines)


def generate(kind, directory, receipt):
    briefs, evidence = load_inputs(directory, list(records(sys.stdin)))
    run = load(directory / 'run.json')
    settings = load(directory / 'config/editorial.json'); validate_settings(settings)
    prompt_name = 'write_articles.md' if kind == 'articles' else 'write_video_scripts.md'
    prompt = (directory / 'prompts' / prompt_name).read_text().strip()
    policy = (directory / 'config/editorial_policy.md').read_text().strip()
    if not prompt or not policy:
        raise ValueError('Draft prompt and policy must be populated')
    context = {'as_of_date': run['as_of_date'], 'project': load(directory / 'config/project.json'), 'briefs': briefs, 'evidence': evidence}
    if kind == 'video_scripts':
        context['matching_articles'] = []
        for b in briefs:
            path = directory / 'articles' / (b['piece_id'] + '.md')
            text = path.read_text(); inspect_article(text.split('\n', 1)[1].split('## Sources', 1)[0].strip(), b)
            context['matching_articles'].append({'piece_id': b['piece_id'], 'markdown': text})
    payload = {'model': settings['model'], 'store': False, 'service_tier': 'default',
               'reasoning': {'effort': settings['reasoning_effort']}, 'max_output_tokens': settings['max_output_tokens'],
               'input': [{'role': 'developer', 'content': prompt + '\n\nEDITORIAL POLICY\n' + policy},
                         {'role': 'user', 'content': json.dumps(context, ensure_ascii=False)}],
               'text': {'format': {'type': 'json_schema', 'name': kind + '_drafts', 'strict': True, 'schema': draft_schema(kind, briefs)}}}
    receipt['input_count'] = len(briefs)
    value = response_text(model_response(directory, receipt, payload, settings))
    original_digest = digest(value)
    if kind == 'articles':
        receipt['citation_number_normalizations'] = normalize_article_citations(value, briefs)
    corrections_path = directory / (kind + '_corrections.json')
    if corrections_path.exists():
        correction = load(corrections_path)
        if not isinstance(correction, dict) or set(correction) != {'source_output_digest', 'corrected_output', 'notes'} or correction['source_output_digest'] != original_digest or not english(correction['notes']):
            raise ValueError('Assistant draft corrections must match the original output and explain changes')
        value = correction['corrected_output']
        receipt['assistant_corrections'] = {'file': str(corrections_path), 'source_output_digest': original_digest,
                                           'corrected_output_digest': digest(value), 'notes': correction['notes'], 'human_approval': False}
    try:
        drafts = validate_drafts(value, kind, briefs)
    except ValueError as error:
        raise RuntimeError('Model draft validation failed: ' + str(error)) from None
    by_piece = {b['piece_id']: b for b in briefs}; manifests = []
    (directory / kind).mkdir(exist_ok=True)
    for draft in drafts:
        brief = by_piece[draft['piece_id']]
        notes = source_notes(brief, evidence, run['as_of_date'])
        save(directory / 'source_notes' / (brief['piece_id'] + '.json'), notes)
        if kind == 'articles':
            body = '# ' + brief['title'] + '\n\n' + draft['markdown'].strip()
        else:
            body = render_script(draft, brief)
        text = body + '\n\n' + source_footer(notes)
        if kind == 'video_scripts':
            urls = list(dict.fromkeys(ref['url'] for c in notes['claims'] for ref in c['evidence']))
            text += '\n## Description and Production Notes\n\nMatching article: [add the Substack URL after publication].\n\n'
            text += 'Source links for the description:\n\n' + '\n'.join('- ' + url for url in urls) + '\n\n'
            text += 'Use the timestamped citations above for relevant passages. Label AI-generated presentation where used; verify transcripts and planned visuals before publication.\n'
            save(directory / 'video_scenes' / (brief['piece_id'] + '.json'), draft)
        path = directory / kind / (brief['piece_id'] + '.md')
        path.write_text(text.rstrip() + '\n')
        manifests.append({'piece_id': brief['piece_id'], 'path': str(path.relative_to(ROOT)), 'claim_ids': [c['claim_id'] for c in brief['claims']]})
    for manifest in manifests:
        emit(manifest)
    receipt['output_count'] = len(manifests)


if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] not in ('articles', 'video_scripts'):
        print('Expected drafting mode: articles or video_scripts', file=sys.stderr); raise SystemExit(2)
    mode = sys.argv.pop(1)
    component('write_' + mode, lambda directory, receipt: generate(mode, directory, receipt))
