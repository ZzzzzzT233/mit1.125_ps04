"""One offline check for dates, parsing, duplicate replay, and version retention."""
import datetime as dt
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from collectors.discover import parse_feed, youtube_page, discover
import collectors.discover as discovery
from pipeline_io import date_reason
from processing.extract_content import timestamped_transcript, visible_text
import processing.transcribe as transcription


def main():
    article = " ".join(["Substantive technical evidence."] * 45)
    assert visible_text(f'<nav>Navigation noise</nav><main><h1>Release</h1><p>{article}</p><article>Model card</article></main>') == "Release\n" + article + "\nModel card"
    as_of = dt.date(2026, 10, 8)
    assert date_reason("2026-09-09T00:00:00Z", as_of) is None
    assert date_reason("2026-09-08T23:30:00-02:00", as_of) is None
    assert date_reason("2026-09-08T23:59:59Z", as_of) == "outside_window"
    assert date_reason("2026-10-09", as_of) == "future_date"
    assert date_reason(None, as_of) == "unknown_date"
    assert date_reason("2026-02-30", as_of) == "invalid_date"
    source = {"source_id": "test", "publisher_id": "test", "kind": "podcast", "url": "https://example.test/feed"}
    rss = b'<rss><channel><item><title>Written</title><link>https://example.test/text</link></item><item><title>Episode</title><guid>episode-1</guid><link>/episode</link><pubDate>Thu, 08 Oct 2026 12:00:00 GMT</pubDate><enclosure url="https://example.test/audio.mp3" type="audio/mpeg"/></item></channel></rss>'
    episodes = list(parse_feed(rss, source))
    assert len(episodes) == 1 and episodes[0]["url"] == "https://example.test/episode"
    assert episodes[0]["published_at"] == "2026-10-08T12:00:00Z"
    with tempfile.TemporaryDirectory() as temporary:
        p = Path(temporary)
        (p / 'config').mkdir()
        (p / 'config/sources.json').write_text(json.dumps([dict(source, exclude_item_ids=[episodes[0]['item_id']])]))
        receipt = {'tools': [], 'input_count': 0, 'output_count': 0, 'errors': []}
        with patch.object(discovery, 'fetch', return_value=rss), patch.object(discovery, 'emit') as emitted:
            discover(p, receipt, 'podcast')
            assert not emitted.called and not receipt['errors']
            assert receipt['source_results'][0]['excluded_item_ids'] == [episodes[0]['item_id']]
    atom = b'<feed xmlns="http://www.w3.org/2005/Atom" xmlns:yt="http://www.youtube.com/xml/schemas/2015"><entry><yt:videoId>abcdefghijk</yt:videoId><title>Video</title><link rel="alternate" href="https://youtube.com/watch?v=abcdefghijk"/><published>2026-10-08T12:00:00Z</published></entry></feed>'
    videos = list(parse_feed(atom, dict(source, kind="youtube")))
    assert videos[0]["item_id"] == "youtube:abcdefghijk"
    with tempfile.TemporaryDirectory() as temporary:
        channel = dict(source, kind='youtube', homepage='https://www.youtube.com/@example')
        payload = {'entries': [{'id': 'abcdefghijk', 'title': 'Fictional video', 'timestamp': 1791460800}]}
        with patch.object(discovery.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout=json.dumps(payload))) as command:
            recovered = youtube_page(Path(temporary), channel, 1)
            assert recovered[0]['item_id'] == 'youtube:abcdefghijk' and recovered[0]['publication_date_precision'] == 'timestamp'
            assert '--skip-download' in command.call_args.args[0] and '--playlist-end' in command.call_args.args[0]
        with patch.object(discovery.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout='{"entries":[]}')):
            try:
                youtube_page(Path(temporary), channel, 1)
                raise AssertionError('Empty channel discovery was accepted')
            except RuntimeError:
                pass
    try:
        list(parse_feed(b"<html>Not a feed</html>", source))
        raise AssertionError("Non-feed XML was accepted")
    except ValueError:
        pass
    segments = transcription.response_segments({"segments": [{"start": 1, "end": 3, "text": "Evidence"}]}, 1200, 10)
    assert segments[0]["start_seconds"] == 1201 and segments[0]["end_seconds"] == 1203
    padded = transcription.response_segments({'segments': [{'start': 9, 'end': 10.8, 'text': 'Final words.'}]}, 1200, 10)
    assert padded[0]['end_seconds'] == 1210
    for bad in ({"segments": [{"start": 2, "end": 1, "text": "Bad"}]}, {"segments": [{"start": 9, "end": 12, "text": "Bad"}]}, {"segments": [{"start": float('nan'), "end": 3, "text": "Bad"}]}, {}):
        try:
            transcription.response_segments(bad, 0, 10)
            raise AssertionError("Malformed API timestamps were accepted")
        except RuntimeError:
            pass
    settings = {'model': 'whisper-1', 'language': 'en'}
    with patch.object(transcription.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout='{"segments":[]}\n200')) as curl:
        assert transcription.request_transcription(Path('/tmp/test.mp3'), 'test-placeholder', settings) == {'segments': []}
        assert 'test-placeholder' not in ' '.join(curl.call_args.args[0])
        assert curl.call_args.kwargs['input'] == 'Authorization: Bearer test-placeholder\n'
    with patch.object(transcription.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout='{"error":"test-placeholder"}\n401')):
        try:
            transcription.request_transcription(Path('/tmp/test.mp3'), 'test-placeholder', settings)
            raise AssertionError('An HTTP failure was accepted')
        except RuntimeError as error:
            assert '401' in str(error) and 'test-placeholder' not in str(error)
    transcript = timestamped_transcript("Host [00:00:00]: First.\nGuest [00:00:30]: Second.\nHost [00:01:20]: Third.", 100)
    assert transcript[-1]["end_seconds"] == 100 and transcript[0]["end_seconds"] == 30
    try:
        timestamped_transcript("Show notes without a transcript", 100)
        raise AssertionError("Untimestamped text was accepted")
    except RuntimeError:
        pass
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        (root / 'data/media').mkdir(parents=True)
        (root / 'api-run/config').mkdir(parents=True)
        shutil.copy(ROOT / 'config/transcription.json', root / 'api-run/config/transcription.json')
        audio = root / 'data/media/test.wav'
        with wave.open(str(audio), 'wb') as stream:
            stream.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
            stream.writeframes(b'\x00\x00' * 32000)
        response = {'segments': [{'start': 0, 'end': 1, 'text': 'Fictional test utterance.'}], 'usage': {'seconds': 2}}
        with patch.object(transcription, 'ROOT', root), patch.dict(os.environ, {'OPENAI_API_KEY': ''}):
            try:
                transcription.api_key()
                raise AssertionError('Missing API key was accepted')
            except RuntimeError:
                pass
            (root / '.env').write_text('OPENAI_API_KEY=test-placeholder\n')
            with patch.object(transcription, 'request_transcription', return_value=response) as api:
                receipt = {'tools': [], 'models': [], 'cost_usd': None}
                first = transcription.transcribe(audio, root / 'api-run', receipt, 2)
                assert api.call_count == 1 and receipt['cost_usd'] == 0.0002
                cached_receipt = {'tools': [], 'models': [], 'cost_usd': None}
                second = transcription.transcribe(audio, root / 'api-run', cached_receipt, 2)
                assert first == second and api.call_count == 1
                assert cached_receipt['transcription_requests'][0]['status'] == 'cached'
            failed_audio = root / 'data/media/failed.wav'
            shutil.copy(audio, failed_audio)
            with patch.object(transcription, 'request_transcription', side_effect=TimeoutError('Simulated timeout')):
                failed_receipt = {'tools': [], 'models': [], 'cost_usd': None}
                try:
                    transcription.transcribe(failed_audio, root / 'api-run', failed_receipt, 2)
                    raise AssertionError('A timed-out request was treated as successful')
                except TimeoutError:
                    pass
                assert failed_receipt['cost_usd'] is None
                assert failed_receipt['transcription_requests'][0]['status'] == 'failed_cost_unconfirmed'
        shutil.copy(ROOT / "pipeline_io.py", root)
        for folder, filename in (("data", "store.py"), ("processing", "filter_items.py")):
            (root / folder).mkdir(exist_ok=True)
            shutil.copy(ROOT / folder / filename, root / folder / filename)
        shutil.copytree(ROOT / "examples", root / "examples")
        run = root / "runs/fixture"
        run.mkdir(parents=True)
        shutil.copy(root / "examples/run.json", run / "run.json")

        def call(script, args, text="", expected=0):
            result = subprocess.run([sys.executable, str(root / script), *args], input=text, capture_output=True, text=True, cwd=root)
            assert result.returncode == expected, result.stderr
            return [json.loads(line) for line in result.stdout.splitlines() if line.strip()]

        fixtures = root / "examples"
        call("data/store.py", ["init"])
        first = call("data/store.py", ["upsert", "runs/fixture"], (fixtures / "items.jsonl").read_text())
        assert first == [json.loads(line) for line in (fixtures / "initial_changes_expected.jsonl").read_text().splitlines()]
        replay = call("data/store.py", ["upsert", "runs/fixture"], (fixtures / "replay_items.jsonl").read_text())
        assert replay == [json.loads(line) for line in (fixtures / "replay_changes_expected.jsonl").read_text().splitlines()]
        assert len(call("data/store.py", ["list"])) == 3
        original = [json.loads(line) for line in (fixtures / "items.jsonl").read_text().splitlines()][2]
        assert call("data/store.py", ["get", original["item_id"], original["version_id"]])[0]["version_id"] == original["version_id"]
        call("data/store.py", ["get", "missing"], expected=1)
        before = call("data/store.py", ["list"])
        call("data/store.py", ["upsert", "runs/fixture"], '{}\n', expected=2)
        assert call("data/store.py", ["list"]) == before
        collision = dict(original, text_path="examples/text/lab.txt")
        call("data/store.py", ["upsert", "runs/fixture"], json.dumps(collision) + '\n', expected=2)
        assert call("data/store.py", ["list"]) == before
        eligible = call("processing/filter_items.py", ["runs/fixture"], (fixtures / "filter_input.jsonl").read_text())
        expected = json.loads((fixtures / "filter_expected.json").read_text())
        assert sorted(item["item_id"] for item in eligible) == sorted(expected["eligible_item_ids"])
        excluded = [json.loads(line) for line in (run / "exclusions.jsonl").read_text().splitlines()]
        assert {(item["item_id"], item["reason"]) for item in excluded} == {(item["item_id"], item["reason"]) for item in expected["exclusions"]}
        assert len(list((run / "logs").glob("*.json"))) >= 4
    print("Collection checks passed: parsing, dates, duplicate replay, retained versions, API timestamp validation, missing-key handling, and cached transcription without repeated requests.")


if __name__ == "__main__":
    main()
