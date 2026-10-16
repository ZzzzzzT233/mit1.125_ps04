"""RSS/Atom discovery shared by the three collector entry points."""
import datetime as dt
from email.utils import parsedate_to_datetime
import json
import re
import subprocess
import sys
from urllib.parse import urljoin, urlsplit
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline_io import ROOT, component, digest, emit, fetch, load, now, save


def field(element, name):
    return next((child.text for child in element if child.tag.split("}")[-1] == name and child.text), None)


def timestamp(value):
    if not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(value)
        except (ValueError, TypeError):
            return value  # Preserve malformed dates for the mechanical filter.
    if parsed.tzinfo is None:
        return value
    return parsed.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def parse_feed(data, source):
    try:
        tree = ET.fromstring(data)
    except ET.ParseError as error:
        raise ValueError("Malformed XML feed") from error
    if tree.tag.split("}")[-1] not in ("rss", "feed", "RDF"):
        raise ValueError("Response is not an RSS or Atom feed")
    for entry in tree.iter():
        if entry.tag.split("}")[-1] not in ("item", "entry"):
            continue
        links = [child for child in entry if child.tag.split("}")[-1] == "link"]
        link = next((child.get("href") or child.text for child in links if child.get("rel", "alternate") == "alternate"), None)
        if not link:
            continue
        link = urljoin(source["url"], link.strip())
        media = next((child.get("url") or child.get("href") for child in entry
                      if (child.tag.split("}")[-1] == "enclosure" or child.get("rel") == "enclosure")
                      and child.get("type", "").startswith("audio/")), None)
        if source["kind"] == "podcast" and not media:
            continue
        if source["kind"] == "youtube" and "/shorts/" in link:
            continue
        native = field(entry, "videoId") if source["kind"] == "youtube" else field(entry, "guid") or field(entry, "id") or link
        item_id = f"youtube:{native}" if source["kind"] == "youtube" else f"{source['kind']}:{digest([source['publisher_id'], native])}"
        publisher = source["publisher_id"]
        if source["source_id"] == "huggingface-blog":
            parts = urlsplit(link).path.strip("/").split("/")
            if len(parts) >= 3 and parts[0] == "blog":
                publisher = parts[1].lower()
        result = {"item_id": item_id, "source_id": source["source_id"], "publisher_id": publisher,
                  "kind": source["kind"], "title": field(entry, "title") or "Untitled item", "url": link,
                  "published_at": timestamp(field(entry, "pubDate") or field(entry, "published")),
                  "retrieved_at": now(), "media_url": urljoin(source["url"], media) if media else None}
        encoded = field(entry, "encoded") or field(entry, "content")
        if encoded:
            path = ROOT / "data/assets/discovery" / (digest(encoded) + ".html")
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                path.write_text(encoded)
            result["discovery_content_path"] = str(path.relative_to(ROOT))
            # Embedded episode players establish a cross-platform identity link.
            video = re.search(r"youtube(?:-nocookie)?\.com/embed/([\w-]{11})", encoded)
            if video and source["kind"] == "podcast":
                result["equivalent_item_ids"] = ["youtube:" + video[1]]
        yield result


def youtube_page(directory, source, limit):
    url = source.get('homepage', source['url']).rstrip('/') + '/videos'
    parts = urlsplit(url)
    if parts.scheme != 'https' or parts.hostname not in ('www.youtube.com', 'youtube.com') or parts.username or parts.password:
        raise ValueError('YouTube fallback requires a public YouTube channel URL')
    command = [sys.executable, '-m', 'yt_dlp', '--ignore-config', '--skip-download', '--dump-single-json',
               '--playlist-end', str(limit), '--force-ipv4', '--js-runtimes', 'node',
               '--socket-timeout', '20', '--retries', '1', url]
    result = subprocess.run(command, capture_output=True, text=True, timeout=240)
    if result.returncode:
        raise RuntimeError('YouTube channel-page discovery failed: ' + result.stderr[-1000:].strip())
    entries = json.loads(result.stdout).get('entries', [])
    retained, records = [], []
    for entry in entries:
        if not entry or not re.fullmatch(r'[\w-]{11}', entry.get('id', '')):
            raise ValueError('YouTube discovery returned an invalid video identity')
        seconds = entry.get('release_timestamp') or entry.get('timestamp')
        if type(seconds) in (int, float):
            published = dt.datetime.fromtimestamp(seconds, dt.timezone.utc).isoformat().replace('+00:00', 'Z')
            precision = 'timestamp'
        else:
            day = entry.get('upload_date')
            if not isinstance(day, str) or not re.fullmatch(r'\d{8}', day):
                raise ValueError('YouTube discovery requires a publication date')
            published = dt.datetime.strptime(day, '%Y%m%d').date().isoformat() + 'T00:00:00Z'
            precision = 'publisher_day; UTC midnight used for mechanical date filtering'
        retained.append({k: entry.get(k) for k in ('id', 'title', 'webpage_url', 'upload_date', 'timestamp', 'release_timestamp', 'channel_id')})
        records.append({'item_id': 'youtube:' + entry['id'], 'source_id': source['source_id'],
                        'publisher_id': source['publisher_id'], 'kind': 'youtube', 'title': entry['title'],
                        'url': 'https://www.youtube.com/watch?v=' + entry['id'], 'published_at': published,
                        'publication_date_precision': precision, 'retrieved_at': now(), 'media_url': None,
                        'discovery_method': 'yt-dlp public channel page after RSS failure'})
    if not records:
        raise RuntimeError('YouTube channel-page discovery returned no videos')
    save(directory / 'discovery' / (digest(source['source_id']) + '.channel.json'), retained)
    return records


def discover(directory, receipt, kind):
    sources = load(directory / "config/sources.json")
    receipt["tools"].append("curl")
    receipt["source_results"] = []
    for source in sources:
        if source.get("kind") != kind:
            continue
        for key in ("source_id", "publisher_id", "url"):
            if not isinstance(source.get(key), str) or not source[key]:
                raise ValueError(f"Source requires nonempty {key}")
        receipt["input_count"] += 1
        count = 0
        try:
            excluded = source.get('exclude_item_ids', [])
            if not isinstance(excluded, list) or not all(isinstance(x, str) and x for x in excluded):
                raise ValueError('Source exclusions must be an array of item IDs')
            skipped = []
            limit = source.get("limit", 20)
            if type(limit) is not int or limit < 1:
                raise ValueError("Source limit must be a positive integer")
            url = source.get("discovery_feed_url", source["url"])
            recovery = {}
            try:
                data = fetch(url)
            except RuntimeError as error:
                if kind != 'youtube':
                    raise
                candidates = youtube_page(directory, source, limit)
                receipt['tools'].append('yt-dlp')
                recovery = {'feed_error': str(error), 'discovery_method': 'yt-dlp channel-page recovery'}
            else:
                raw = directory / "discovery" / f"{digest(source['source_id'])}.xml"
                raw.parent.mkdir(parents=True, exist_ok=True)
                raw.write_bytes(data)
                candidates = parse_feed(data, source)
            # ponytail: bounded feed snapshots, add archive pagination if coverage needs it.
            for record in candidates:
                if record['item_id'] in excluded:
                    skipped.append(record['item_id'])
                    continue
                emit(record)
                count += 1
                receipt["output_count"] += 1
                if count == limit:
                    break
            receipt["source_results"].append({"source_id": source["source_id"], "status": "completed", "count": count, "limit": limit, 'excluded_item_ids': skipped, **recovery})
        except (OSError, RuntimeError, ValueError) as error:
            receipt["errors"].append(f"{source['source_id']}: {error}")
            receipt["source_results"].append({"source_id": source["source_id"], "status": "incomplete", "count": count, "error": str(error)})


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("feed", "youtube", "podcast"):
        print("Usage: discover.py feed|youtube|podcast RUN_DIR", file=sys.stderr)
        raise SystemExit(2)
    kind = sys.argv.pop(1)
    component({"feed": "fetch_feeds", "youtube": "fetch_youtube", "podcast": "fetch_podcasts"}[kind], lambda directory, receipt: discover(directory, receipt, kind))
