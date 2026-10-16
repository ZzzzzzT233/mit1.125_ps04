"""One offline check for grounded brief references, failure boundaries, and replay."""
import contextlib
import copy
import datetime as dt
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import editorial.create_briefs as generator
import editorial.select_items as selection
from pipeline_io import digest, records, save, stage


def main():
    with (ROOT / 'examples/items.jsonl').open() as stream:
        items = list(records(stream))
    evidence = selection.load_evidence(items, dt.date(2026, 10, 8))
    refs = [{'item_id': i['item_id'], 'version_id': i['version_id'],
             'locator': {'type': 'text', 'quote': 'The report does not measure on-site setup time.'} if i['kind'] == 'feed'
             else {'type': 'segment', 'segment_id': i['segments'][0]['segment_id']}} for i in evidence]
    value = {'blocking_reasons': [], 'briefs': [
        {'piece_id': p, 'title': 'Fictional example ' + p, 'question': 'What does the fictional evidence establish?',
         'argument': 'Fictional argument ' + p, 'synthesis': 'These invented snippets illustrate references, not real findings.',
         'limitations': 'Fictional example evidence only; no actual experiment or publication.',
         'claims': [{'claim_id': p + '-c1', 'statement': 'The invented records illustrate a multi-source inference.',
                     'type': 'inference', 'evidence': copy.deepcopy(refs)}]} for p in ('01', '02', '03')]}
    assert generator.validate_briefs(value, evidence) == value['briefs']
    changes = [lambda v: v['briefs'].pop(),
               lambda v: v['briefs'][0]['claims'][0]['evidence'][0].update(version_id='wrong'),
               lambda v: v['briefs'][0]['claims'][0]['evidence'][0]['locator'].update(quote='An invented supporting quotation.'),
               lambda v: v['briefs'][0]['claims'][0]['evidence'][1]['locator'].update(segment_id='missing'),
               lambda v: v['briefs'][0]['claims'][0]['evidence'].pop(),
               lambda v: v['briefs'][0]['claims'][0].update(type='reported_fact'),
               lambda v: v['briefs'][1].update(argument=v['briefs'][0]['argument'])]
    for change in changes:
        bad = copy.deepcopy(value); change(bad)
        try:
            generator.validate_briefs(bad, evidence)
            raise AssertionError('Invalid brief passed')
        except ValueError:
            pass
    try:
        generator.validate_briefs({'briefs': [], 'blocking_reasons': ['Missing independent evidence.']}, evidence)
        raise AssertionError('Insufficient evidence accepted')
    except RuntimeError:
        pass
    decisions = [{'item_id': i['item_id'], 'version_id': i['version_id'], 'decision': 'accept',
                  'reason': 'Fictional evidence retained solely to verify the interface.', 'piece_ids': ['01', '02', '03']} for i in items]
    response = {'status': 'completed', 'model': 'simulated-test-model', 'usage': {'input_tokens': 1000, 'output_tokens': 200},
                'output': [{'content': [{'type': 'output_text', 'text': json.dumps(value)}]}]}
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        shutil.copytree(ROOT / 'config', directory / 'config'); shutil.copytree(ROOT / 'prompts', directory / 'prompts')
        save(directory / 'run.json', {'run_id': 'offline-brief-check', 'as_of_date': '2026-10-08', 'mode': 'example'})
        (directory / 'eligible.jsonl').write_text(''.join(json.dumps(i) + '\n' for i in items))
        text = ''.join(json.dumps(d) + '\n' for d in decisions)
        (directory / 'decisions.jsonl').write_text(text)
        def invoke(expected=None):
            output = io.StringIO()
            with patch.object(sys, 'stdin', io.StringIO(text)), contextlib.redirect_stdout(output):
                with stage('create_briefs', directory) as receipt:
                    generator.create(directory, receipt)
            assert list(records(io.StringIO(output.getvalue()))) == (expected if expected is not None else value['briefs'])
            return receipt
        with patch.object(selection, 'api_key', return_value='test-placeholder'), patch.object(selection, 'request_response', return_value=response) as api:
            first = invoke(); replay = invoke()
            assert api.call_count == 1 and first['output_count'] == 3
            assert replay['model_requests'][0]['status'] == 'cached'
            assert all((directory / 'briefs' / (p + '.md')).is_file() for p in ('01', '02', '03'))
            corrected = copy.deepcopy(value)
            corrected['briefs'][0]['title'] = 'Corrected fictional example 01'
            correction = {'source_output_digest': 'stale', 'corrected_output': corrected, 'notes': 'Assistant test correction only; not student review.'}
            save(directory / 'brief_corrections.json', correction)
            try:
                invoke()
                raise AssertionError('Stale correction accepted')
            except SystemExit as error:
                assert error.code == 2
            correction['source_output_digest'] = digest(value)
            save(directory / 'brief_corrections.json', correction)
            repaired = invoke(corrected['briefs'])
            assert api.call_count == 1 and repaired['assistant_corrections']['human_approval'] is False
    print('Brief checks passed: exact evidence, versions, segments, source groups, synthesis references, blocking output, rendered files, and cached replay. No paid API calls.')


if __name__ == '__main__':
    main()
