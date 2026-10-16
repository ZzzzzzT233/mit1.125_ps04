"""Only this component accesses the canonical SQLite evidence index."""
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline_io import ROOT, emit, load, local_path, records, run_dir, stage


def validate(item):
    for key in ("item_id", "source_id", "publisher_id", "kind", "title", "url", "retrieved_at", "version_id", "text_path"):
        if not isinstance(item.get(key), str) or not item[key]:
            raise ValueError(f"Item requires nonempty {key}")
    if item["kind"] not in ("feed", "youtube", "podcast"):
        raise ValueError("Invalid item kind")
    for key in ("published_at", "media_url", "segments_path"):
        if key not in item or (item[key] is not None and not isinstance(item[key], str)):
            raise ValueError(f"Item requires string or null {key}")
    for key in ("text_path", "segments_path"):
        if item[key] is not None and not local_path(item[key]).is_file():
            raise ValueError(f"Missing evidence asset: {item[key]}")
    if item["kind"] != "feed" and item["segments_path"] is None:
        raise ValueError("Media evidence requires timestamped segments")


def connect():
    directory = ROOT / "data/evidence"
    directory.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(directory / "evidence.sqlite3")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS versions (
            item_id TEXT NOT NULL, version_id TEXT NOT NULL, record TEXT NOT NULL,
            PRIMARY KEY(item_id, version_id));
        CREATE TABLE IF NOT EXISTS latest (
            item_id TEXT PRIMARY KEY, version_id TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS observations (
            item_id TEXT NOT NULL, version_id TEXT NOT NULL, run_id TEXT NOT NULL,
            retrieved_at TEXT NOT NULL, PRIMARY KEY(item_id, version_id, run_id));
    """)
    return db


def upsert(directory, receipt):
    items = list(records(sys.stdin))
    for item in items:
        validate(item)
    receipt["input_count"] = len(items)
    db = connect()
    changes = []
    with db:
        for item in items:
            identity, version = item["item_id"], item["version_id"]
            old = db.execute("SELECT record FROM versions WHERE item_id=? AND version_id=?", (identity, version)).fetchone()
            exists = db.execute("SELECT 1 FROM latest WHERE item_id=?", (identity,)).fetchone()
            if old:
                retained = json.loads(old[0])
                different_text = local_path(retained["text_path"]).read_text() != local_path(item["text_path"]).read_text()
                old_segments = load(local_path(retained["segments_path"])) if retained["segments_path"] else None
                new_segments = load(local_path(item["segments_path"])) if item["segments_path"] else None
                if different_text or old_segments != new_segments or any(retained[key] != item[key] for key in ("title", "url", "published_at")):
                    raise ValueError("Evidence changed without a new version_id")
                retained["retrieved_at"] = item["retrieved_at"]
                db.execute("UPDATE versions SET record=? WHERE item_id=? AND version_id=?", (json.dumps(retained), identity, version))
                change = "unchanged"
            else:
                change = "changed" if exists else "new"
                db.execute("INSERT INTO versions VALUES (?,?,?)", (identity, version, json.dumps(item)))
                db.execute("INSERT INTO latest VALUES (?,?) ON CONFLICT(item_id) DO UPDATE SET version_id=excluded.version_id", (identity, version))
            db.execute("INSERT INTO observations VALUES (?,?,?,?) ON CONFLICT(item_id,version_id,run_id) DO UPDATE SET retrieved_at=excluded.retrieved_at",
                       (identity, version, directory.name, item["retrieved_at"]))
            changes.append({"item_id": identity, "version_id": version, "change": change})
    for change in changes:
        emit(change)
    receipt["output_count"] = len(changes)
    receipt["tools"].append("SQLite")
    db.close()


def main():
    args = sys.argv[1:]
    if args and args[0] == "upsert" and len(args) == 2:
        directory = run_dir(args[1])
        with stage("store_upsert", directory) as receipt:
            upsert(directory, receipt)
        return
    if not args or args[0] not in ("init", "list", "get"):
        raise ValueError("Usage: store.sh init|list|get ITEM_ID [VERSION_ID]|upsert RUN_DIR")
    if (args[0] in ("init", "list") and len(args) != 1) or (args[0] == "get" and len(args) not in (2, 3)):
        raise ValueError("Invalid store arguments")
    db = connect()
    if args[0] == "list":
        for row in db.execute("SELECT v.record FROM versions v JOIN latest l USING(item_id,version_id) ORDER BY item_id"):
            emit(json.loads(row[0]))
    elif args[0] == "get":
        if len(args) == 3:
            row = db.execute("SELECT record FROM versions WHERE item_id=? AND version_id=?", args[1:]).fetchone()
        else:
            row = db.execute("SELECT v.record FROM versions v JOIN latest l USING(item_id,version_id) WHERE item_id=?", (args[1],)).fetchone()
        if row is None:
            print("Evidence item or version not found", file=sys.stderr)
            raise SystemExit(1)
        emit(json.loads(row[0]))
    db.close()


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, TypeError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(2)
    except (OSError, sqlite3.Error) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
