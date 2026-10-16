"""Mechanical date eligibility, separate from editorial selection."""
import datetime as dt
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline_io import component, date_reason, emit, load, records
import json


def filter_items(directory, receipt):
    as_of = dt.date.fromisoformat(load(directory / "run.json")["as_of_date"])
    items = list(records(sys.stdin))
    for item in items:
        if not all(isinstance(item.get(key), str) and item[key] for key in ("item_id", "version_id")) or "published_at" not in item:
            raise ValueError("Date filter requires item_id, version_id, and published_at")
    receipt["input_count"] = len(items)
    with (directory / "exclusions.jsonl").open("w") as exclusions:
        for item in items:
            reason = date_reason(item["published_at"], as_of)
            if reason:
                record = {"item_id": item["item_id"], "version_id": item["version_id"], "reason": reason,
                          "detail": f"Publication date {item['published_at']!r}; inclusive window {as_of - dt.timedelta(days=29)} through {as_of}"}
                exclusions.write(json.dumps(record) + "\n")
            else:
                emit(item)
                receipt["output_count"] += 1


if __name__ == "__main__":
    component("filter_items", filter_items)
