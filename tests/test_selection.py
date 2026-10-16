"""One offline check for selection boundaries, private credentials, and cached replay."""
import contextlib
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import editorial.select_items as selection
from pipeline_io import load, records, save, stage


def main():
    items = list(records((ROOT / 'examples/items.jsonl').open()))
    decisions = [{'item_id': i['item_id'], 'version_id': i['version_id'], 'decision': 'accept',
                  'reason': 'Fictional evidence supports a bounded claim with limitations for student review.',
                  'piece_ids': ['01']} for i in items]
    assert selection.validate_decisions({'decisions': list(reversed(decisions))}, items) == decisions
    for bad in (decisions[:-1], decisions + [decisions[0]], [dict(decisions[0], version_id='wrong'), *decisions[1:]],
                [dict(decisions[0], decision='reject'), *decisions[1:]],
                [dict(decisions[0], reason='This cites an invented transcript segment a-9999.'), *decisions[1:]]):
        try:
            selection.validate_decisions({'decisions': bad}, items)
            raise AssertionError('Invalid model decisions were accepted')
        except ValueError:
            pass
    for bad in ({'status': 'incomplete'}, {'status': 'completed', 'output': [{'content': [{'type': 'refusal'}]}]}):
        try:
            selection.response_text(bad)
            raise AssertionError('Incomplete/refused response was accepted')
        except RuntimeError:
            pass
    response = {'status': 'completed', 'model': 'simulated-test-model', 'usage': {'input_tokens': 1000, 'output_tokens': 200},
                'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': json.dumps({'decisions': decisions})}]}]}
    with patch.object(selection.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout=json.dumps(response) + '\n200')) as curl:
        assert selection.request_response(Path('/tmp/public-request.json'), 'test-placeholder') == response
        assert 'test-placeholder' not in ' '.join(curl.call_args.args[0])
        assert 'Authorization: Bearer test-placeholder' in curl.call_args.kwargs['input']
    with patch.object(selection.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout='{"error":"test-placeholder"}\n401')):
        try:
            selection.request_response(Path('/tmp/public-request.json'), 'test-placeholder')
            raise AssertionError('HTTP error was accepted')
        except RuntimeError as error:
            assert '401' in str(error) and 'test-placeholder' not in str(error)
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        shutil.copytree(ROOT / 'config', directory / 'config')
        shutil.copytree(ROOT / 'prompts', directory / 'prompts')
        save(directory / 'run.json', {'run_id': 'offline-selection-check', 'as_of_date': '2026-10-08', 'mode': 'example'})
        text = '\n'.join(json.dumps(item) for item in items) + '\n'
        (directory / 'eligible.jsonl').write_text(text)

        def invoke():
            output = io.StringIO()
            with patch.object(sys, 'stdin', io.StringIO(text)), contextlib.redirect_stdout(output):
                with stage('select_items', directory) as receipt:
                    selection.select(directory, receipt)
            assert list(records(io.StringIO(output.getvalue()))) == decisions
            return receipt

        with patch.object(selection, 'api_key', return_value='test-placeholder'), patch.object(selection, 'request_response', return_value=response) as api:
            first = invoke()
            assert api.call_count == 1 and first['cost_usd'] == 0.000225
            assert first['input_count'] == first['output_count'] == 3
            assert all('test-placeholder' not in p.read_text() for p in (directory / 'model_calls').glob('*'))
            replay = invoke()
            assert api.call_count == 1 and replay['model_requests'][0]['status'] == 'cached' and replay['models'] == []
        settings = load(directory / 'config/editorial.json')
        settings['request_budget_usd'] = 0
        save(directory / 'config/editorial.json', settings)
        with patch.object(selection, 'api_key', side_effect=AssertionError('Credential read before budget gate')):
            try:
                invoke()
                raise AssertionError('Over-budget request was attempted')
            except SystemExit as error:
                assert error.code == 2
        assert len(list((directory / 'logs').glob('*.json'))) == 3
    print('Selection checks passed: complete coverage, identities/versions, decision invariants, segment references, refusal handling, protected credentials, fee ceiling, and cached replay. No paid API calls.')


if __name__ == '__main__':
    main()
