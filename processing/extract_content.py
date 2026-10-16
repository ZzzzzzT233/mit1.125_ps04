"""Retain written content, source media, and timestamped evidence."""
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline_io import ROOT, component, digest, emit, fetch, local_path, records, save
from processing.transcribe import transcribe


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ignored = []
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "nav", "header", "footer", "form", "button", "noscript", "svg"):
            self.ignored.append(tag)
        if not self.ignored and tag in ("p", "div", "br", "li", "h1", "h2", "h3", "section"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if self.ignored and tag == self.ignored[-1]:
            self.ignored.pop()
        if not self.ignored and tag in ("p", "div", "li", "h1", "h2", "h3", "section"):
            self.parts.append("\n")

    def handle_data(self, value):
        if not self.ignored:
            self.parts.append(value)


def visible_text(html):
    # ponytail: HTML article heuristic; replace with a dedicated extractor if layout noise persists.
    articles = re.findall(r"<article\b[^>]*>(.*?)</article>", html, re.S | re.I)
    mains = re.findall(r"<main\b[^>]*>(.*?)</main>", html, re.S | re.I)
    # Embedded model cards can be the only article elements on a full blog page.
    for blocks in (articles, mains, [html]):
        if not blocks:
            continue
        parser = VisibleText()
        parser.feed(max(blocks, key=len))
        text = "\n".join(re.sub(r"\s+", " ", line).strip() for line in "".join(parser.parts).splitlines() if line.strip())
        if len(text.split()) >= 120 or blocks == [html]:
            return text


def file_hash(path):
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def retain_media(path, suffix):
    destination = ROOT / "data/media" / (file_hash(path) + suffix)
    if not destination.exists():
        path.replace(destination)
    return str(destination.relative_to(ROOT))


def media_duration(path):
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)], capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise RuntimeError("Unable to determine media duration")
    return float(result.stdout.strip())


def timestamped_transcript(text, duration):
    matches = list(re.finditer(r"(?m)^[^\n\[]{0,100}\[(\d{1,2}):(\d{2}):(\d{2})\]\s*:?", text))
    segments = []
    for index, match in enumerate(matches):
        hours, minutes, seconds = map(int, match.groups())
        start = hours * 3600 + minutes * 60 + seconds
        passage = text[match.end():matches[index + 1].start() if index + 1 < len(matches) else len(text)].strip()
        if not passage:
            continue
        if minutes >= 60 or seconds >= 60 or start >= duration:
            raise RuntimeError("Transcript timestamp is outside the media duration")
        if segments and start < segments[-1]["start_seconds"]:
            raise RuntimeError("Transcript timestamps are not ordered")
        if segments and start == segments[-1]["start_seconds"]:
            segments[-1]["text"] += "\n" + passage
        else:
            segments.append({"segment_id": f"p-{len(segments) + 1:04}", "start_seconds": float(start), "end_seconds": duration, "text": passage})
    for current, following in zip(segments, segments[1:]):
        current["end_seconds"] = following["start_seconds"]
    if len(segments) < 3 or segments[-1]["start_seconds"] < duration * 0.7:
        raise RuntimeError("No sufficiently complete source-provided timestamped transcript; transcription is required")
    return segments


def get_previous(item_id):
    result = subprocess.run(["bash", "data/store.sh", "get", item_id], cwd=ROOT, capture_output=True, text=True)
    if result.returncode == 0:
        return json.loads(result.stdout)
    if result.returncode != 1:
        raise RuntimeError("Evidence store lookup failed")
    return None


def extract_one(item, receipt, directory):
    previous = get_previous(item["item_id"])
    segments = None
    extra = {}
    media_directory = ROOT / "data/media"
    media_directory.mkdir(parents=True, exist_ok=True)
    if item["kind"] == "youtube":
        # Native upload IDs are stable; metadata changes invalidate this cache.
        if previous and all(previous.get(key) == item.get(key) for key in ("title", "url", "published_at")) and previous.get("media_path") and local_path(previous["media_path"]).is_file():
            if local_path(previous["text_path"]).is_file() and local_path(previous["segments_path"]).is_file():
                receipt["reused_count"] += 1
                return {**previous, "retrieved_at": item["retrieved_at"]}
        download_record = ROOT / "data/assets/downloads" / (digest([item["item_id"], item["url"], item["published_at"]]) + ".json")
        downloaded = json.loads(download_record.read_text()) if download_record.exists() else None
        if downloaded and local_path(downloaded["media_path"]).is_file():
            extra["media_path"] = downloaded["media_path"]
        else:
            receipt["tools"].append("yt-dlp")
            with tempfile.TemporaryDirectory(dir=media_directory) as temporary:
                template = str(Path(temporary) / "source.%(ext)s")
                command = [sys.executable, "-m", "yt_dlp", "--ignore-config", "--no-playlist", "--no-progress", "--force-ipv4", "--js-runtimes", "node",
                           "--socket-timeout", "20", "--retries", "1", "--format", "bestaudio[ext=m4a]/bestaudio",
                           "--output", template, item["url"]]
                result = subprocess.run(command, capture_output=True, text=True, timeout=240)
                if result.returncode:
                    raise RuntimeError("yt-dlp could not retrieve public audio: " + result.stderr[-1000:].strip())
                audio = next((path for path in Path(temporary).iterdir() if path.suffix in (".m4a", ".webm", ".mp3", ".opus")), None)
                if audio is None:
                    raise RuntimeError("Video audio was not downloaded")
                extra["media_path"] = retain_media(audio, audio.suffix)
                save(download_record, extra)
        receipt["tools"].append("ffprobe")
        duration = media_duration(local_path(extra["media_path"]))
        segments = transcribe(local_path(extra["media_path"]), directory, receipt, duration)
        extra["transcript_source"] = "OpenAI whisper-1 API transcription; human verification required"
        text = "\n".join(segment["text"] for segment in segments)
    else:
        receipt["tools"].append("curl")
        html = fetch(item["url"]).decode("utf-8", errors="replace")
        raw = ROOT / "data/assets/original" / (digest(html) + ".html")
        raw.parent.mkdir(parents=True, exist_ok=True)
        if not raw.exists():
            raw.write_text(html)
        extra["source_html_path"] = str(raw.relative_to(ROOT))
        text = visible_text(html)
        if item["kind"] == "podcast":
            if not item["media_url"]:
                raise RuntimeError("Podcast candidate has no audio enclosure")
            # ponytail: reuse audio at an unchanged enclosure URL; add ETag checks for mutable media URLs.
            if previous and previous.get("media_url") == item["media_url"] and previous.get("media_path") and local_path(previous["media_path"]).is_file():
                extra["media_path"] = previous["media_path"]
            else:
                with tempfile.TemporaryDirectory(dir=media_directory) as temporary:
                    audio = Path(temporary) / "source.mp3"
                    fetch(item["media_url"], audio)
                    extra["media_path"] = retain_media(audio, ".mp3")
            receipt["tools"].append("ffprobe")
            duration = media_duration(local_path(extra["media_path"]))
            if item.get("discovery_content_path"):
                feed_text = visible_text(local_path(item["discovery_content_path"]).read_text())
                try:
                    segments = timestamped_transcript(feed_text, duration)
                except RuntimeError:
                    pass
            if segments is None:
                try:
                    segments = timestamped_transcript(text, duration)
                except RuntimeError:
                    segments = transcribe(local_path(extra["media_path"]), directory, receipt, duration)
                    extra["transcript_source"] = "OpenAI whisper-1 API transcription; human verification required"
            text = "\n".join(segment["text"] for segment in segments)
            extra.setdefault("transcript_source", "Publisher-provided timestamped transcript; human verification required")
        elif len(text.split()) < 120:
            raise RuntimeError("Retrieved page has insufficient substantive text")
    version = digest({"title": item["title"], "url": item["url"], "published_at": item["published_at"], "text": text, "segments": segments})
    folder = ROOT / "data/assets" / digest(item["item_id"]) / version
    folder.mkdir(parents=True, exist_ok=True)
    text_path = folder / "text.txt"
    if not text_path.exists():
        text_path.write_text(text + "\n")
    segments_path = folder / "segments.json" if segments is not None else None
    if segments_path and not segments_path.exists():
        save(segments_path, segments)
    return {**item, **extra, "version_id": version, "text_path": str(text_path.relative_to(ROOT)),
            "segments_path": str(segments_path.relative_to(ROOT)) if segments_path else None}


def extract(directory, receipt):
    candidates = list(records(sys.stdin))
    for item in candidates:
        for key in ("item_id", "source_id", "publisher_id", "kind", "title", "url", "retrieved_at"):
            if not isinstance(item.get(key), str) or not item[key]:
                raise ValueError(f"Candidate requires nonempty {key}")
        if item["kind"] not in ("feed", "youtube", "podcast") or "published_at" not in item or "media_url" not in item:
            raise ValueError("Candidate has invalid kind or missing metadata")
    receipt["input_count"] = len(candidates)
    receipt["reused_count"] = 0
    receipt["item_results"] = []
    for item in candidates:
        print(f"Extracting {item['kind']}: {item['title']}", file=sys.stderr, flush=True)
        try:
            record = extract_one(item, receipt, directory)
            emit(record)
            receipt["output_count"] += 1
            receipt["item_results"].append({"item_id": item["item_id"], "status": "completed"})
        except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
            receipt["errors"].append(f"{item['item_id']}: {error}")
            receipt["item_results"].append({"item_id": item["item_id"], "status": "incomplete", "error": str(error)})
    receipt["tools"] = sorted(set(receipt["tools"]))


if __name__ == "__main__":
    component("extract_content", extract)
