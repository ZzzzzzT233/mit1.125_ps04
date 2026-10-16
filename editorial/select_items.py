"""Apply the snapshotted editorial policy with one bounded, auditable model call."""
from collections import Counter
import datetime as dt
import html
import json
import math
from pathlib import Path
import re
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data.store import validate as validate_item
from pipeline_io import component, date_reason, digest, emit, load, local_path, records, save
from processing.transcribe import api_key

PIECES = {
    '01': 'Consequential releases and actual access',
    '02': 'Technical differences and scrutiny of performance claims',
    '03': 'Broader directions, implications, and tradeoffs',
}


def decision_schema(items):
    fields = {
        'item_id': {'type': 'string', 'enum': [i['item_id'] for i in items]},
        'version_id': {'type': 'string', 'enum': list(dict.fromkeys(i['version_id'] for i in items))},
        'decision': {'type': 'string', 'enum': ['accept', 'reject', 'defer']},
        'reason': {'type': 'string'},
        'piece_ids': {'type': 'array', 'items': {'type': 'string', 'enum': list(PIECES)}},
    }
    return {'type': 'object', 'properties': {'decisions': {'type': 'array', 'items': {
        'type': 'object', 'properties': fields, 'required': list(fields), 'additionalProperties': False}}},
        'required': ['decisions'], 'additionalProperties': False}


def validate_decisions(value, items):
    if not isinstance(value, dict) or set(value) != {'decisions'} or not isinstance(value['decisions'], list):
        raise ValueError('Expected an object containing only a decisions array')
    expected = {i['item_id']: i for i in items}
    found = {}
    for row in value['decisions']:
        if not isinstance(row, dict) or set(row) != {'item_id', 'version_id', 'decision', 'reason', 'piece_ids'}:
            raise ValueError('Decision has missing or unexpected fields')
        identity = row['item_id']
        if not isinstance(identity, str) or identity not in expected or identity in found:
            raise ValueError('Unknown or duplicate decision identity')
        if row['version_id'] != expected[identity]['version_id']:
            raise ValueError('Decision references the wrong evidence version')
        if row['decision'] not in ('accept', 'reject', 'defer'):
            raise ValueError('Invalid decision value')
        reason = row['reason']
        if not isinstance(reason, str) or len(reason.strip()) < 20 or re.search(r'[\u4e00-\u9fff]', reason):
            raise ValueError('A substantive English reason is required')
        pieces = row['piece_ids']
        if not isinstance(pieces, list) or any(not isinstance(p, str) or p not in PIECES for p in pieces) or len(set(pieces)) != len(pieces):
            raise ValueError('Invalid or repeated piece IDs')
        if bool(pieces) != (row['decision'] == 'accept'):
            raise ValueError('Only accepted items must have nonempty piece assignments')
        available = {s['segment_id'] for s in expected[identity].get('segments', [])}
        if any(segment not in available for segment in re.findall(r'\b[pa]-\d{4}\b', reason)):
            raise ValueError('Reason cites a segment absent from its evidence item')
        found[identity] = row
    if set(found) != set(expected):
        raise ValueError('Every eligible item requires exactly one decision')
    return [found[i['item_id']] for i in items]


def response_text(payload):
    if not isinstance(payload, dict) or payload.get('status') != 'completed':
        raise RuntimeError('Model response did not complete; inspect retained response status')
    chunks = []
    for entry in payload.get('output', []):
        for content in entry.get('content', []) if isinstance(entry, dict) else []:
            if content.get('type') == 'refusal':
                raise RuntimeError('Model refused the editorial request')
            if content.get('type') == 'output_text' and isinstance(content.get('text'), str):
                chunks.append(content['text'])
    if not chunks:
        raise RuntimeError('Model returned no editorial text')
    try:
        return json.loads(''.join(chunks))
    except json.JSONDecodeError:
        raise RuntimeError('Model returned invalid editorial JSON') from None


def request_response(path, key):
    # curl configuration arrives on stdin; the retained request file has no secret.
    escaped = key.replace('\\', '\\\\').replace('"', '\\"')
    command = ['curl', '--ipv4', '--silent', '--show-error', '--connect-timeout', '15', '--max-time', '300',
               '--config', '-', '--header', 'Content-Type: application/json', '--data-binary', '@' + str(path),
               '--max-filesize', '16777216', '--write-out', '\n%{http_code}', 'https://api.openai.com/v1/responses']
    try:
        result = subprocess.run(command, input='header = "Authorization: Bearer ' + escaped + '"\n',
                                capture_output=True, text=True, timeout=310)
    except (OSError, subprocess.TimeoutExpired):
        raise RuntimeError('Editorial transport failed; request cost is unconfirmed') from None
    if result.returncode:
        raise RuntimeError(f'Editorial transport failed (curl exit {result.returncode}); cost is unconfirmed')
    body, _, status = result.stdout.rpartition('\n')
    if status != '200':
        raise RuntimeError(f'Editorial API failed with HTTP {status if status.isdigit() else "unknown"}; check account/model access or billing')
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        raise RuntimeError('Editorial API returned invalid JSON; cost is unconfirmed') from None


def validate_settings(settings):
    if settings.get('provider') != 'openai' or not isinstance(settings.get('model'), str) or not settings['model'].strip():
        raise ValueError('Selection requires an OpenAI model')
    if settings.get('reasoning_effort') not in ('none', 'low', 'medium', 'high', 'xhigh', 'max'):
        raise ValueError('Invalid reasoning effort')
    for key, maximum in (('max_output_tokens', 128000), ('max_request_bytes', 900000)):
        if type(settings.get(key)) is not int or not 1 <= settings[key] <= maximum:
            raise ValueError(f'Invalid {key}')
    for key in ('request_budget_usd', 'input_usd_per_million', 'cached_input_usd_per_million', 'cache_write_usd_per_million', 'output_usd_per_million'):
        value = settings.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError(f'Invalid {key}')
    dt.date.fromisoformat(settings['price_checked_on'])


def write_report(directory, decisions, items, receipt):
    by_id = {i['item_id']: i for i in items}
    counts = Counter(d['decision'] for d in decisions)
    accepted = [by_id[d['item_id']] for d in decisions if d['decision'] == 'accept']
    coverage = {}
    lines = ['# AI Editorial Selection', '', 'These are model decisions, not student approval or final briefs.', '',
             f"As of: {load(directory / 'run.json')['as_of_date']} UTC. Model: {receipt.get('resolved_model', 'Not called')}. "
             f"Accepted: {counts['accept']}; rejected: {counts['reject']}; deferred: {counts['defer']}.", '',
             '| Item | Decision | Intended pieces | Model reason |', '| --- | --- | --- | --- |']
    for row in decisions:
        item = by_id[row['item_id']]
        reason = html.escape(row['reason']).replace('|', '\\|').replace('\n', ' ')
        title = html.escape(item['title']).replace('|', '\\|')
        lines.append(f"| [{title}]({item['url']}) | {row['decision']} | {', '.join(row['piece_ids']) or 'None'} | {reason} |")
    lines += ['', '## Provisional Piece Coverage', '', 'These roles are starting points, not completed editorial briefs.', '']
    for piece, label in PIECES.items():
        selected = [by_id[d['item_id']] for d in decisions if piece in d['piece_ids']]
        publishers = sorted({i['publisher_id'] for i in selected})
        coverage[piece] = {'item_count': len(selected), 'publisher_groups': publishers,
                           'by_kind': dict(Counter(i['kind'] for i in selected))}
        lines += [f'### {piece}: {label}', '', f"{len(selected)} items; {len(publishers)} producer groups: {', '.join(publishers) or 'None'}.", '']
        if len(publishers) < 3:
            lines += ['**Coverage gap:** fewer than three producer groups; repair before writing a brief.', '']
    lines += ['## Required Student Review', '',
              'Review at least three accepted and three rejected/deferred items. Compare these model reasons with your own judgment, record corrections, revise the policy, and rerun the affected stage. No student judgment or approval has been supplied by this report.', '',
              'The structured stream is `decisions.jsonl`; exact IDs and versions resolve to `eligible.jsonl` and retained source assets. Requests, raw responses, and fingerprints are under `model_calls/`. Individual invocation receipts are under `logs/`.', '',
              'Complete editorial briefs, draft generation, content checks, human approval, two full live runs on different days, and publication remain outstanding.', '']
    (directory / 'selection_report.md').write_text('\n'.join(lines))
    save(directory / 'selection_coverage.json', {'counts': dict(counts), 'accepted_by_kind': dict(Counter(i['kind'] for i in accepted)),
         'accepted_publisher_groups': sorted({i['publisher_id'] for i in accepted}), 'pieces': coverage,
         'independence_verified': False, 'human_approval': False})


def load_evidence(items, as_of):
    seen = set()
    evidence = []
    for item in items:
        validate_item(item)  # Pure record validation; no evidence index is opened.
        if item['item_id'] in seen or not isinstance(item.get('publisher_id'), str) or not item['publisher_id']:
            raise ValueError('Duplicate identity or missing originating producer')
        seen.add(item['item_id'])
        if date_reason(item['published_at'], as_of):
            raise ValueError('Selection input contains date-ineligible evidence')
        source = {key: item.get(key) for key in ('item_id', 'version_id', 'source_id', 'publisher_id', 'kind', 'title', 'url', 'published_at', 'equivalent_item_ids', 'transcript_source')}
        text = local_path(item['text_path']).read_text()
        if not text.strip():
            raise ValueError('Evidence text is empty')
        if item['kind'] == 'feed':
            source['text'] = text
        else:
            segments = load(local_path(item['segments_path']))
            if not isinstance(segments, list) or not segments:
                raise ValueError('Media evidence requires nonempty segments')
            previous = -1
            for segment in segments:
                if not isinstance(segment, dict) or not isinstance(segment.get('segment_id'), str) or not isinstance(segment.get('text'), str):
                    raise ValueError('Malformed transcript segment')
                start, end = segment.get('start_seconds'), segment.get('end_seconds')
                if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in (start, end)) or start < previous or start < 0 or end <= start:
                    raise ValueError('Invalid transcript timestamps')
                previous = start
            if len({s['segment_id'] for s in segments}) != len(segments):
                raise ValueError('Repeated transcript segment identities')
            item['segments'] = segments
            source['segments'] = segments  # Full media content once; no duplicated transcript text.
        evidence.append(source)
    return evidence


def model_response(directory, receipt, payload, settings):
    size = len(json.dumps(payload, ensure_ascii=False).encode())
    # ponytail: byte-based conservative token bound, add token counting if large corpora hit this ceiling.
    bound = ((size + 2000) * settings['cache_write_usd_per_million'] * 2 + settings['max_output_tokens'] * settings['output_usd_per_million'] * 1.5) / 1_000_000
    if size > settings['max_request_bytes'] or bound > settings['request_budget_usd']:
        raise ValueError('Full editorial request exceeds the configured size or conservative fee ceiling; split the corpus explicitly')
    fingerprint = digest(payload)
    request_path = directory / 'model_calls' / (fingerprint + '.request.json')
    response_path = directory / 'model_calls' / (fingerprint + '.response.json')
    receipt.update(request_fingerprint=fingerprint, request_bytes=size, request_fee_upper_bound_usd=round(bound, 6), model_requests=[])
    # ponytail: sequential invocations; add a per-request lock if the same run is launched concurrently.
    if response_path.exists():
        response = load(response_path)
        receipt['model_requests'].append({'status': 'cached', 'estimated_cost_usd': 0})
    else:
        key = api_key()
        save(request_path, payload)
        receipt['models'] = [settings['model']]
        receipt['tools'].append('curl')
        request = {'status': 'requested', 'estimated_cost_usd': None}
        receipt['model_requests'].append(request)
        try:
            response = request_response(request_path, key)
        except Exception:
            request['status'] = 'failed_cost_unconfirmed'
            receipt['cost_note'] = 'The failed model request may have been billed; check provider usage.'
            raise
        save(response_path, response)
        usage = response.get('usage') if isinstance(response, dict) else None
        if isinstance(usage, dict) and all(type(usage.get(k)) is int and usage[k] >= 0 for k in ('input_tokens', 'output_tokens')):
            long = usage['input_tokens'] > 272000
            # Conservative estimate: price all input as cache writes; ignore cached-input discounts.
            cost = round((usage['input_tokens'] * settings['cache_write_usd_per_million'] * (2 if long else 1) + usage['output_tokens'] * settings['output_usd_per_million'] * (1.5 if long else 1)) / 1_000_000, 6)
            receipt.update(cost_usd=cost, cost_is_estimate=True, usage=usage,
                           cost_note='Conservative token-fee estimate at cache-write input rates, without cached-input discounts; local costs unmeasured. Prices checked ' + settings['price_checked_on'])
            request.update(status='completed', estimated_cost_usd=cost)
        else:
            request['status'] = 'completed_cost_unknown'
            receipt['cost_note'] = 'Model response retained, but token usage or fees are unavailable.'
    receipt['resolved_model'] = response.get('model', settings['model']) if isinstance(response, dict) else settings['model']
    return response


def select(directory, receipt):
    settings = load(directory / 'config/editorial.json')
    validate_settings(settings)
    run = load(directory / 'run.json')
    as_of = dt.date.fromisoformat(run['as_of_date'])
    project = load(directory / 'config/project.json')
    if not all(isinstance(project.get(k), str) and project[k].strip() for k in ('publication_name', 'topic', 'audience', 'central_question')):
        raise ValueError('Project brief requires four nonempty strings')
    items = list(records(sys.stdin))
    with (directory / 'eligible.jsonl').open() as stream:
        eligible = list(records(stream))
    if digest(items) != digest(eligible):
        raise ValueError('Selection input must match this run\'s complete eligible stream')
    evidence = load_evidence(items, as_of)
    receipt['input_count'] = len(items)
    if not items:
        write_report(directory, [], [], receipt)
        return
    instructions = (directory / 'prompts/select_items.md').read_text().strip()
    policy = (directory / 'config/editorial_policy.md').read_text().strip()
    if not instructions or not policy:
        raise ValueError('Selection prompt and editorial policy must be populated')
    payload = {'model': settings['model'], 'store': False, 'service_tier': 'default',
               'reasoning': {'effort': settings['reasoning_effort']}, 'max_output_tokens': settings['max_output_tokens'],
               'input': [{'role': 'developer', 'content': instructions + '\n\nEDITORIAL POLICY\n' + policy},
                         {'role': 'user', 'content': json.dumps({'as_of_date': run['as_of_date'], 'project': project, 'evidence': evidence}, ensure_ascii=False)}],
               'text': {'format': {'type': 'json_schema', 'name': 'editorial_selection', 'strict': True, 'schema': decision_schema(items)}}}
    response = model_response(directory, receipt, payload, settings)
    try:
        decisions = validate_decisions(response_text(response), items)
    except ValueError as error:
        raise RuntimeError('Model decision validation failed: ' + str(error)) from None
    write_report(directory, decisions, items, receipt)
    for decision in decisions:
        emit(decision)
    receipt['output_count'] = len(decisions)


if __name__ == '__main__':
    component('select_items', select)
