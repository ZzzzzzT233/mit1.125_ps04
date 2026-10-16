"""Generate three source-linked briefs from accepted, versioned evidence."""
import datetime as dt
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from editorial.select_items import PIECES, load_evidence, model_response, response_text, validate_decisions, validate_settings
from pipeline_io import component, digest, emit, load, records, save


def object_schema(fields):
    return {'type': 'object', 'properties': fields, 'required': list(fields), 'additionalProperties': False}


def brief_schema(items):
    string = {'type': 'string'}
    locator = {'anyOf': [object_schema({'type': {'type': 'string', 'enum': ['text']}, 'quote': string}),
                         object_schema({'type': {'type': 'string', 'enum': ['segment']}, 'segment_id': string})]}
    evidence = object_schema({'item_id': {'type': 'string', 'enum': [i['item_id'] for i in items]},
                              'version_id': {'type': 'string', 'enum': list(dict.fromkeys(i['version_id'] for i in items))},
                              'locator': locator})
    claim = object_schema({'claim_id': string, 'statement': string,
                           'type': {'type': 'string', 'enum': ['reported_fact', 'source_claim', 'inference']},
                           'evidence': {'type': 'array', 'items': evidence}})
    fields = {key: string for key in ('piece_id', 'title', 'question', 'argument', 'synthesis', 'limitations')}
    fields['piece_id'] = {'type': 'string', 'enum': list(PIECES)}
    fields['claims'] = {'type': 'array', 'items': claim}
    return object_schema({'briefs': {'type': 'array', 'items': object_schema(fields)},
                          'blocking_reasons': {'type': 'array', 'items': string}})


def english(value):
    return isinstance(value, str) and bool(value.strip()) and not re.search(r'[\u4e00-\u9fff]', value)


def validate_briefs(value, evidence):
    if not isinstance(value, dict) or set(value) != {'briefs', 'blocking_reasons'}:
        raise ValueError('Expected briefs and blocking_reasons arrays')
    if not isinstance(value['briefs'], list) or not isinstance(value['blocking_reasons'], list):
        raise ValueError('Brief output arrays are required')
    if value['blocking_reasons']:
        if value['briefs'] or not all(english(x) for x in value['blocking_reasons']):
            raise ValueError('Blocking output must contain only English reasons and no briefs')
        raise RuntimeError('Insufficient evidence: ' + '; '.join(value['blocking_reasons']))
    if len(value['briefs']) != 3:
        raise ValueError('Exactly three briefs are required')
    items = {i['item_id']: i for i in evidence}
    found, titles, arguments, kinds = {}, set(), set(), set()
    for brief in value['briefs']:
        fields = {'piece_id', 'title', 'question', 'argument', 'synthesis', 'limitations', 'claims'}
        if not isinstance(brief, dict) or set(brief) != fields or not all(english(brief[k]) for k in fields - {'claims'}):
            raise ValueError('Brief fields require nonempty English prose')
        piece = brief['piece_id']
        if piece not in PIECES or piece in found:
            raise ValueError('Unknown or duplicate piece ID')
        if brief['title'].strip().casefold() in titles or brief['argument'].strip().casefold() in arguments:
            raise ValueError('Briefs must have different titles and arguments')
        titles.add(brief['title'].strip().casefold()); arguments.add(brief['argument'].strip().casefold())
        if not isinstance(brief['claims'], list) or not brief['claims']:
            raise ValueError('Each brief requires claims')
        claim_ids, publishers, multi_source_inference = set(), set(), False
        for claim in brief['claims']:
            if not isinstance(claim, dict) or set(claim) != {'claim_id', 'statement', 'type', 'evidence'}:
                raise ValueError('Malformed claim')
            identity = claim['claim_id']
            if not isinstance(identity, str) or not re.fullmatch(piece + r'-c[1-9]\d*', identity) or identity in claim_ids:
                raise ValueError('Invalid or repeated claim identity')
            claim_ids.add(identity)
            if not english(claim['statement']) or claim['type'] not in ('reported_fact', 'source_claim', 'inference'):
                raise ValueError('Claim requires English text and a valid type')
            if not isinstance(claim['evidence'], list) or not claim['evidence']:
                raise ValueError('Every claim requires evidence')
            claim_publishers, references = set(), set()
            for ref in claim['evidence']:
                if not isinstance(ref, dict) or set(ref) != {'item_id', 'version_id', 'locator'}:
                    raise ValueError('Malformed evidence reference')
                item = items.get(ref['item_id']) if isinstance(ref['item_id'], str) else None
                if item is None or ref['version_id'] != item['version_id']:
                    raise ValueError('Evidence must reference an accepted item at its exact version')
                locator = ref['locator']
                if not isinstance(locator, dict):
                    raise ValueError('Evidence locator must be an object')
                if item['kind'] == 'feed':
                    if set(locator) != {'type', 'quote'} or locator['type'] != 'text':
                        raise ValueError('Written evidence requires an exact text locator')
                    quote = locator['quote']
                    if not isinstance(quote, str) or len(quote.strip()) < 8 or len(quote.split()) > 25 or quote not in item['text']:
                        raise ValueError('Written quote is absent, empty, or longer than 25 words')
                else:
                    if set(locator) != {'type', 'segment_id'} or locator['type'] != 'segment':
                        raise ValueError('Media evidence requires a segment locator')
                    if not isinstance(locator['segment_id'], str) or locator['segment_id'] not in {s['segment_id'] for s in item['segments']}:
                        raise ValueError('Media segment is absent from the referenced item')
                signature = digest(ref)
                if signature in references:
                    raise ValueError('Repeated evidence reference within a claim')
                references.add(signature)
                publishers.add(item['publisher_id']); claim_publishers.add(item['publisher_id']); kinds.add(item['kind'])
            if claim['type'] == 'inference' and len(claim_publishers) >= 2:
                multi_source_inference = True
        if len(publishers) < 3:
            raise ValueError('Each brief requires at least three originating producer groups')
        if not multi_source_inference:
            raise ValueError('Each brief requires a supported multi-source inference')
        found[piece] = brief
    if kinds != {'feed', 'youtube', 'podcast'}:
        raise ValueError('The series must use written, video, and podcast evidence')
    return [found[p] for p in PIECES]


def timestamp(value):
    seconds = int(value)
    return f'{seconds // 3600:02d}:{seconds // 60 % 60:02d}:{seconds % 60:02d}'


def write_briefs(directory, briefs, evidence):
    items = {i['item_id']: i for i in evidence}
    target = directory / 'briefs'
    target.mkdir(exist_ok=True)
    coverage = {}
    for brief in briefs:
        lines = [f"# {brief['piece_id']}: {brief['title']}", '',
                 'Editorial brief — AI-generated draft for student review. Not a finished article or publication approval.', '',
                 f"Evidence window: 30 days ending {load(directory / 'run.json')['as_of_date']} UTC.", '']
        if (directory / 'brief_corrections.json').exists():
            lines += ['Assistant citation and scope corrections are recorded in [brief_corrections.json](../brief_corrections.json). The original model response remains preserved.', '']
        for key, heading in (('question', 'Reader Question'), ('argument', 'Central Argument'), ('synthesis', 'Synthesis and Proposed Structure'), ('limitations', 'Limitations and Verification Before Publication')):
            lines += [f'## {heading}', '', brief[key], '']
        lines += ['## Claims and Supporting Evidence', '']
        used = set()
        for claim in brief['claims']:
            lines += [f"### {claim['claim_id']} — {claim['type']}", '', claim['statement'], '']
            for ref in claim['evidence']:
                item = items[ref['item_id']]; used.add(item['item_id'])
                locator = ref['locator']
                lines += [f"- Source: [{item['title']}]({item['url']}) — {item['publisher_id']}; published {item['published_at']}.",
                          f"  Evidence identity: `{item['item_id']}`; version `{item['version_id']}`."]
                if locator['type'] == 'text':
                    lines += [f"  Exact supporting passage: “{locator['quote']}”"]
                else:
                    segment = next(s for s in item['segments'] if s['segment_id'] == locator['segment_id'])
                    lines += [f"  Segment `{segment['segment_id']}`: {timestamp(segment['start_seconds'])}–{timestamp(segment['end_seconds'])}. Verify the full passage against the recording."]
            lines += ['']
        publishers = sorted({items[i]['publisher_id'] for i in used})
        kinds = sorted({items[i]['kind'] for i in used})
        coverage[brief['piece_id']] = {'item_ids': sorted(used), 'publisher_groups': publishers, 'input_kinds': kinds,
                                     'claim_count': len(brief['claims']), 'independence_verified': False}
        lines += ['## Source Coverage and Status', '',
                  f"{len(used)} underlying items; {len(publishers)} originating producer groups: {', '.join(publishers)}.", '',
                  f"Input types: {', '.join(kinds)}. Producer counts are proxies, not proof of independent corroboration. Vendor and interview claims remain attributed; source incentives and omitted perspectives require review.", '',
                  'This draft does not complete the required student review, final approval, full live publication runs, or publication.', '']
        (target / (brief['piece_id'] + '.md')).write_text('\n'.join(lines))
    save(directory / 'brief_coverage.json', {'pieces': coverage, 'human_approval': False,
          'checks': 'Exact versions, quotes, segment IDs, producer minimums, multi-source inference references, and series input types. Semantic support and source independence still require review.'})


def create(directory, receipt):
    settings = load(directory / 'config/editorial.json'); validate_settings(settings)
    run = load(directory / 'run.json')
    with (directory / 'eligible.jsonl').open() as stream:
        items = list(records(stream))
    decisions = list(records(sys.stdin))
    with (directory / 'decisions.jsonl').open() as stream:
        retained = list(records(stream))
    if digest(decisions) != digest(retained):
        raise ValueError('Brief input must match the retained decision stream')
    # Load all evidence to validate the selection's media references before using accepted items.
    evidence = load_evidence(items, dt.date.fromisoformat(run['as_of_date']))
    validate_decisions({'decisions': decisions}, items)
    accepted = {d['item_id'] for d in decisions if d['decision'] == 'accept'}
    evidence = [i for i in evidence if i['item_id'] in accepted]
    receipt['input_count'] = len(decisions)
    if len({i['publisher_id'] for i in evidence}) < 3 or {i['kind'] for i in evidence} != {'feed', 'youtube', 'podcast'}:
        raise ValueError('Accepted evidence lacks producer or series input coverage')
    instructions = (directory / 'prompts/create_briefs.md').read_text().strip()
    policy = (directory / 'config/editorial_policy.md').read_text().strip()
    if not instructions or not policy:
        raise ValueError('Brief prompt and editorial policy must be populated')
    payload = {'model': settings['model'], 'store': False, 'service_tier': 'default',
               'reasoning': {'effort': settings['reasoning_effort']}, 'max_output_tokens': settings['max_output_tokens'],
               'input': [{'role': 'developer', 'content': instructions + '\n\nEDITORIAL POLICY\n' + policy},
                         {'role': 'user', 'content': json.dumps({'as_of_date': run['as_of_date'], 'project': load(directory / 'config/project.json'),
                          'decisions': [d for d in decisions if d['decision'] == 'accept'], 'evidence': evidence}, ensure_ascii=False)}],
               'text': {'format': {'type': 'json_schema', 'name': 'editorial_briefs', 'strict': True, 'schema': brief_schema(evidence)}}}
    response = model_response(directory, receipt, payload, settings)
    value = response_text(response)
    corrections_path = directory / 'brief_corrections.json'
    if corrections_path.exists():
        corrections = load(corrections_path)
        if set(corrections) != {'source_output_digest', 'corrected_output', 'notes'} or corrections['source_output_digest'] != digest(value) or not english(corrections['notes']):
            raise ValueError('Assistant corrections must identify the exact original output and explain changes')
        value = corrections['corrected_output']
        receipt['assistant_corrections'] = {'file': str(corrections_path), 'notes': corrections['notes'],
                                           'source_output_digest': corrections['source_output_digest'], 'corrected_output_digest': digest(value),
                                           'human_approval': False}
    if isinstance(value, dict) and value.get('blocking_reasons'):
        save(directory / 'brief_blocking_reasons.json', value)
    try:
        briefs = validate_briefs(value, evidence)
    except ValueError as error:
        raise RuntimeError('Model brief validation failed: ' + str(error)) from None
    write_briefs(directory, briefs, evidence)
    for brief in briefs:
        emit(brief)
    receipt['output_count'] = len(briefs)


if __name__ == '__main__':
    component('create_briefs', create)
