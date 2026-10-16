"""One offline drafting/review check: no real evidence updates or paid requests."""
import contextlib
import copy
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import content.drafts as writer
import editorial.select_items as selection
from pipeline_io import digest, load, records, save, stage
from review.check_content import assess


def main():
    with (ROOT / 'examples/briefs.jsonl').open() as stream:
        original = next(records(stream))
    briefs = []
    for piece in ('01', '02', '03'):
        b = copy.deepcopy(original); b['piece_id'] = piece
        b['title'] += ' ' + piece; b['argument'] += ' ' + piece
        for c in b['claims']: c['claim_id'] = piece + '-c' + c['claim_id'].split('-c')[1]
        briefs.append(b)
    articles, videos = [], []
    for b in briefs:
        p = b['piece_id']; ids = [c['claim_id'] for c in b['claims']]
        body = ('This is fictional prose for an offline interface check. ' * 75) + f'[^1]<!-- claim:{ids[0]} --> [^2]<!-- claim:{ids[1]} -->'
        articles.append({'piece_id': p, 'markdown': body, 'claim_ids': ids})
        scenes = [{'narration': 'Fictional narration for this offline check only. ' * 18,
                   'visual': 'Illustrative test card only; no real claims or assets.', 'claim_ids': [ids[k]] if k < 2 else []} for k in range(4)]
        videos.append({'piece_id': p, 'scenes': scenes})
    writer.validate_drafts({'drafts': articles}, 'articles', briefs)
    writer.validate_drafts({'drafts': videos}, 'video_scripts', briefs)
    numbered = {'drafts': copy.deepcopy(articles)}
    numbered['drafts'][0]['markdown'] = numbered['drafts'][0]['markdown'].replace('[^2]', '[^8]')
    events = writer.normalize_article_citations(numbered, briefs)
    assert events == [{'piece_id': '01', 'claim_id': '01-c2', 'old_footnote': '8', 'new_footnote': '2'}]
    assert numbered['drafts'] == articles
    for bad in (dict(articles[0], claim_ids=['02-c1']), dict(articles[0], markdown=articles[0]['markdown'].replace('claim:01-c1', 'claim:01-c99')), dict(articles[0], markdown='Too short.')):
        try:
            writer.validate_drafts({'drafts': [bad, *articles[1:]]}, 'articles', briefs)
            raise AssertionError('Invalid draft accepted')
        except ValueError:
            pass
    with tempfile.TemporaryDirectory(prefix='offline-draft-', dir=ROOT / 'runs') as temporary:
        directory = Path(temporary)
        shutil.copytree(ROOT / 'config', directory / 'config'); shutil.copytree(ROOT / 'prompts', directory / 'prompts')
        save(directory / 'run.json', {'run_id': directory.name, 'as_of_date': '2026-10-08', 'mode': 'example'})
        with (ROOT / 'examples/items.jsonl').open() as stream: items = list(records(stream))
        decisions = [{'item_id': i['item_id'], 'version_id': i['version_id'], 'decision': 'accept', 'reason': 'Fictional interface evidence for an offline check only.', 'piece_ids': ['01', '02', '03']} for i in items]
        for name, rows in (('eligible', items), ('decisions', decisions), ('briefs', briefs)):
            (directory / (name + '.jsonl')).write_text(''.join(json.dumps(x) + '\n' for x in rows))
        text = (directory / 'briefs.jsonl').read_text()
        def response(path, key):
            kind = load(path)['text']['format']['name']
            value = {'drafts': articles if kind == 'articles_drafts' else videos}
            return {'status': 'completed', 'model': 'simulated-offline-model', 'usage': {'input_tokens': 1000, 'output_tokens': 200},
                    'output': [{'content': [{'type': 'output_text', 'text': json.dumps(value)}]}]}
        def invoke(kind):
            output = io.StringIO()
            with patch.object(sys, 'stdin', io.StringIO(text)), contextlib.redirect_stdout(output):
                with stage('write_' + kind, directory) as receipt: writer.generate(kind, directory, receipt)
            (directory / (kind + '.jsonl')).write_text(output.getvalue())
            return receipt
        with patch.object(selection, 'api_key', return_value='test-placeholder'), patch.object(selection, 'request_response', side_effect=response) as api:
            invoke('articles'); invoke('video_scripts')
            first = assess(directory); assert first['passed'], first
            replay = invoke('articles'); assert api.call_count == 2 and replay['model_requests'][0]['status'] == 'cached'
            assert assess(directory)['review_id'] == first['review_id']
            correction = {'source_output_digest': 'stale', 'corrected_output': {'drafts': copy.deepcopy(articles)}, 'notes': 'Assistant offline test correction; no student judgment.'}
            save(directory / 'articles_corrections.json', correction)
            try:
                invoke('articles'); raise AssertionError('Stale correction accepted')
            except SystemExit as error:
                assert error.code == 2
            correction['source_output_digest'] = digest({'drafts': articles})
            save(directory / 'articles_corrections.json', correction)
            repaired = invoke('articles')
            assert repaired['assistant_corrections']['human_approval'] is False and api.call_count == 2
            path = directory / 'articles/01.md'; path.write_text(path.read_text().replace('claim:01-c1', 'claim:01-c99'))
            changed = assess(directory); assert not changed['passed'] and changed['review_id'] != first['review_id']
            (directory / 'video_scripts/03.md').unlink()
            assert not assess(directory)['passed']
    print('Draft checks passed: claim/footnote binding, length, scene references, source notes, cache replay, stable review fingerprint, stale edits, and missing files. No paid API calls.')


if __name__ == '__main__':
    main()
