"""OpenAI timestamped transcription; cached chunks avoid repeated API fees."""
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile

from pipeline_io import ROOT, digest, load, save


def api_key():
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key and (ROOT / ".env").is_file():
        for line in (ROOT / ".env").read_text().splitlines():
            name, separator, value = line.partition("=")
            if separator and name.strip() == "OPENAI_API_KEY":
                key = value.strip().strip('"\'')
                break
    if not key:
        raise RuntimeError("OpenAI API calls require OPENAI_API_KEY in the local environment or ignored .env file; see COLLECTION.md")
    if "\n" in key or "\r" in key:
        raise ValueError("API key must be a single line")
    return key


def request_transcription(path, key, settings):
    # Supply the secret through stdin, never command arguments or a retained file.
    command = ["curl", "--ipv4", "--silent", "--show-error", "--connect-timeout", "15", "--max-time", "300",
               "--header", "@-", "--form", "file=@" + str(path), "--form", "model=" + settings["model"],
               "--form", "language=" + settings["language"], "--form", "response_format=verbose_json",
               "--form", "timestamp_granularities[]=segment", "--write-out", "\n%{http_code}",
               "https://api.openai.com/v1/audio/transcriptions"]
    try:
        result = subprocess.run(command, input="Authorization: Bearer " + key + "\n", capture_output=True, text=True, timeout=310)
    except (OSError, subprocess.TimeoutExpired):
        raise RuntimeError("OpenAI transcription transport failed; request cost is unconfirmed") from None
    if result.returncode:
        raise RuntimeError(f"OpenAI transcription transport failed (curl exit {result.returncode}); request cost is unconfirmed")
    body, _, status = result.stdout.rpartition("\n")
    if status != "200":
        # Provider error bodies may echo credential fragments; never print them.
        raise RuntimeError(f"OpenAI transcription failed with HTTP {status if status.isdigit() else 'unknown'}; check account access, billing, or rate limits")
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        raise RuntimeError("OpenAI transcription request failed or returned invalid JSON") from None


def response_segments(payload, offset, chunk_duration, start_id=0):
    if not isinstance(payload, dict) or not isinstance(payload.get("segments"), list):
        raise RuntimeError("Transcription response is missing timestamped segments")
    result = []
    previous = -1.0
    for entry in payload["segments"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("text"), str):
            raise RuntimeError("Malformed transcript segment")
        start, end = entry.get("start"), entry.get("end")
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) for value in (start, end)):
            raise RuntimeError("Transcript timestamps must be finite numbers")
        # Clip at most one second of end padding; larger or unordered timestamps remain invalid.
        if start < 0 or start >= chunk_duration or start < previous or end <= start or end > chunk_duration + 1:
            raise RuntimeError("Transcript timestamps are unordered or outside the audio chunk")
        previous = start
        if entry["text"].strip():
            result.append({"segment_id": f"a-{start_id + len(result) + 1:04}", "start_seconds": offset + start,
                           "end_seconds": offset + min(end, chunk_duration), "text": entry["text"].strip()})
    return result


def transcribe(audio, directory, receipt, duration):
    settings = load(directory / "config/transcription.json")
    if settings.get("provider") != "openai" or settings.get("model") != "whisper-1":
        raise ValueError("This transcription component supports OpenAI whisper-1 with segment timestamps")
    chunk_seconds = settings.get("chunk_seconds")
    rate = settings.get("estimated_usd_per_minute")
    if isinstance(chunk_seconds, bool) or not isinstance(chunk_seconds, int) or not 1 <= chunk_seconds <= 1200:
        raise ValueError("chunk_seconds must be an integer between 1 and 1200")
    if isinstance(rate, bool) or not isinstance(rate, (int, float)) or not math.isfinite(rate) or rate < 0 or settings.get("language") != "en":
        raise ValueError("Expected English transcription and a nonnegative estimated rate")
    if not isinstance(settings.get("price_checked_on"), str) or not settings["price_checked_on"]:
        raise ValueError("A price verification date is required before paid requests")
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("Audio duration must be positive and finite")
    receipt.setdefault("transcription_requests", [])
    segments = []
    cache = ROOT / "data/assets/transcriptions" / audio.stem
    cache.mkdir(parents=True, exist_ok=True)
    key = None
    # ponytail: fixed chunks may cut utterances; add silence-aware boundaries if review finds errors.
    for offset in range(0, math.ceil(duration), chunk_seconds):
        length = min(chunk_seconds, duration - offset)
        identity = digest({"provider": "openai", "model": settings["model"], "language": settings["language"], "offset": offset, "duration": length, "format": "verbose_json:segment"})
        cached = cache / (identity + ".json")
        if cached.exists():
            payload = load(cached)
            receipt["transcription_requests"].append({"offset_seconds": offset, "status": "cached", "estimated_cost_usd": 0})
        else:
            receipt["tools"] = sorted(set(receipt["tools"] + ["ffmpeg", "curl"]))
            key = key or api_key()
            with tempfile.TemporaryDirectory(dir=ROOT / "data/media") as temporary:
                chunk = Path(temporary) / "audio.mp3"
                command = ["ffmpeg", "-v", "error", "-ss", str(offset), "-i", str(audio), "-t", str(length),
                           "-map", "0:a:0", "-ac", "1", "-ar", "16000", "-codec:a", "libmp3lame", "-b:a", "48k", str(chunk)]
                result = subprocess.run(command, capture_output=True, timeout=180)
                if result.returncode:
                    raise RuntimeError("FFmpeg could not prepare the transcription chunk")
                if chunk.stat().st_size > 24_000_000:
                    raise RuntimeError("Prepared audio chunk exceeds the API upload limit")
                receipt["models"] = sorted(set(receipt["models"] + [settings["model"]]))
                request_receipt = {"offset_seconds": offset, "status": "requested", "estimated_cost_usd": None}
                receipt["transcription_requests"].append(request_receipt)
                try:
                    payload = request_transcription(chunk, key, settings)
                except Exception:
                    request_receipt["status"] = "failed_cost_unconfirmed"
                    receipt["cost_note"] = "Successful request fees are estimated; a failed request may also have been billed. Check provider usage. Local costs are unmeasured."
                    raise
                save(cached, payload)  # Preserve successful responses even if later validation fails.
                usage = payload.get("usage") if isinstance(payload, dict) else None
                billed = usage.get("seconds", length) if isinstance(usage, dict) else length
                if isinstance(billed, bool) or not isinstance(billed, (int, float)) or not math.isfinite(billed) or billed < 0:
                    billed = length
                cost = round(billed / 60 * rate, 6)
                request_receipt.update(status="completed", estimated_cost_usd=cost, billed_or_estimated_seconds=billed)
                receipt["cost_usd"] = round((receipt["cost_usd"] or 0) + cost, 6)
                receipt["cost_is_estimate"] = True
                receipt["cost_note"] = "Estimated API transcription fees only; local compute/transfer not measured. Rate checked " + settings["price_checked_on"]
        segments.extend(response_segments(payload, offset, length, len(segments)))
    if not segments:
        raise RuntimeError("Transcription contained no speech segments")
    return segments
