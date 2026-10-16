"""Report measured workflow state, current review, and approval-bound readiness."""
from collections import Counter
import datetime as dt
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline_io import component, emit, load, records
from publishing.prepare_package import package_current, publication_links
from review.check_content import assess


def read_records(directory, name):
    path = directory / name
    if not path.exists():
        return None
    with path.open() as stream:
        return list(records(stream))


def summarize(directory, receipt):
    run = load(directory / "run.json")
    streams = {name: read_records(directory, name + ".jsonl") for name in ("candidates", "items", "changes", "eligible", "exclusions", "decisions", "briefs", "articles", "video_scripts")}
    logs = [load(path) for path in sorted((directory / "logs").glob("*.json"))]
    stages = {}
    for log in sorted(logs, key=lambda entry: entry["started_at"]):
        stages[log["stage"]] = log
    failures = [{"stage": log["stage"], "status": log["status"], "errors": log.get("errors", [])}
                for log in stages.values() if log["status"] != "completed"]
    counts = {key: len(streams[name]) if streams[name] is not None else None
              for key, name in (("discovered", "candidates"), ("extracted", "items"), ("eligible", "eligible"), ("excluded", "exclusions"), ("briefs", "briefs"), ("articles", "articles"), ("video_scripts", "video_scripts"))}
    for name in ("new", "changed", "unchanged"):
        counts[name] = sum(row["change"] == name for row in streams["changes"]) if streams["changes"] is not None else None
    for name, decision in (("accepted", "accept"), ("rejected", "reject"), ("deferred", "defer")):
        counts[name] = sum(row["decision"] == decision for row in streams["decisions"]) if streams["decisions"] is not None else None
    items = streams["eligible"] or []
    parent = {}

    def find(identity):
        parent.setdefault(identity, identity)
        if parent[identity] != identity:
            parent[identity] = find(parent[identity])
        return parent[identity]

    for item in items:
        for equivalent in item.get("equivalent_item_ids", []):
            parent[find(equivalent)] = find(item["item_id"])
    identities = {find(item["item_id"]) for item in items}
    publishers = sorted({item["publisher_id"] for item in items})
    coverage = {kind: len({find(item["item_id"]) for item in items if item["kind"] == kind}) for kind in ("feed", "youtube", "podcast")}
    minimum_metadata_coverage = len(identities) >= 12 and len(publishers) >= 6 and all(count >= 2 for count in coverage.values())
    complete_collection = all(stages.get(name, {}).get("status") == "completed" for name in ("fetch_feeds", "fetch_youtube", "fetch_podcasts", "extract_content", "store_upsert", "filter_items", "collect_sources"))
    finish = dt.datetime.now(dt.timezone.utc)
    selected = stages.get('select_items', {}).get('status') == 'completed'
    briefed = stages.get('create_briefs', {}).get('status') == 'completed'
    drafted = all(stages.get(name, {}).get('status') == 'completed' for name in ('write_articles', 'write_video_scripts'))
    review = load(directory / 'review.json') if (directory / 'review.json').is_file() else None
    current = assess(directory) if review and review.get('passed') is True else review
    review_current = bool(review and current and current.get('passed') is True and review.get('review_id') == current.get('review_id'))
    overall = 'awaiting_review' if review_current else 'failed'
    reason = 'Drafts pass current mechanical checks; student review and matching approval are required.' if review_current else 'Drafts or current content checks are missing, stale, or contain blocking issues.'
    package_error = None
    if (directory / 'package/manifest.json').is_file():
        try:
            package_current(directory, current)
            overall = 'ready_for_production'
            reason = 'The package matches current reviewed inputs and student approval; rendering and publication remain manual.'
        except (OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
            package_error = str(error)
    remaining_work = 'Complete the missing or failed pipeline stages and content checks.'
    if review_current: remaining_work = 'Complete student review/approval and prepare the production package.'
    if overall == 'ready_for_production': remaining_work = 'Produce videos and publish the approved article/video pairs.'
    remaining = [remaining_work,
                 "Inspect originating-source independence and substantive quality; endpoint counts are not proof of corroboration.",
                 "Verify extracted text and media transcripts against their sources.",
                 "Confirm twelve substantive items, six independent sources, and input-type coverage after editorial review.",
                 "Complete human policy review, two full live runs on different days, video production, and publication."]
    summary = {"run_id": run["run_id"], "as_of_date": run["as_of_date"], "scope": run.get("scope"),
               "status": overall, "status_reason": reason,
               "collection_status": "not_run_retained_corpus" if run.get('scope') in ('selection_only', 'briefs_only', 'content_only') else ("completed" if complete_collection else "incomplete"),
               "selection_status": "completed" if selected else (stages.get('select_items', {}).get('status') or ("retained_input" if run.get('source_selection_run') else "not_run")),
               "brief_status": "completed" if briefed else (stages.get('create_briefs', {}).get('status') or ("retained_input" if run.get('source_briefs_run') else "not_run")),
               "article_status": stages.get('write_articles', {}).get('status') or "not_run",
               "video_script_status": stages.get('write_video_scripts', {}).get('status') or "not_run",
               "review_status": ("passed" if review_current else "stale_or_failed") if review else "not_run", "counts": counts,
               "complete_live_run": bool(run.get('mode') == 'live' and run.get('scope') == 'full_pipeline' and minimum_metadata_coverage and complete_collection and selected and briefed and drafted and review_current and stages.get('create_series', {}).get('status') == 'completed'),
               "package_validation_error": package_error,
               "coverage": {"distinct_underlying_items": len(identities), "by_kind": coverage,
                            "originating_publishers": publishers, "publisher_count": len(publishers),
                            "minimum_metadata_coverage": minimum_metadata_coverage,
                            "independence_verified": False,
                            "duplicate_observations": len(streams["candidates"] or []) - len({row["item_id"] for row in streams["candidates"] or []})},
               "failed_or_incomplete_stages": failures,
               "elapsed_seconds": round((finish - dt.datetime.fromisoformat(run["started_at"].replace("Z", "+00:00"))).total_seconds(), 2),
               "tools": sorted({tool for log in logs for tool in log.get("tools", [])}),
               "models": sorted({model for log in logs for model in log.get("models", [])}),
               "known_or_estimated_cost_usd": sum(log["cost_usd"] for log in logs if isinstance(log.get("cost_usd"), (int, float))),
               "unconfirmed_api_requests": sum(request.get("status") in ("requested", "failed_cost_unconfirmed", "completed_cost_unknown")
                                               for log in logs for request in log.get("transcription_requests", []) + log.get("model_requests", [])),
               "unknown_cost_receipts": sum(log.get("cost_usd") is None for log in logs),
               "remaining_manual_actions": remaining,
               "collection_limits": "Bounded current feed snapshots; archives, mutable-media updates, transcript completeness, and claim independence need review."}
    if (directory / 'package/publication_links.json').is_file():
        try:
            summary['recorded_publication_links'] = publication_links(directory)
        except (ValueError, RuntimeError) as error:
            summary['publication_links_error'] = str(error)
    if summary["unknown_cost_receipts"] and not any(isinstance(log.get("cost_usd"), (int, float)) for log in logs):
        summary["known_or_estimated_cost_usd"] = None
    emit(summary)
    receipt["input_count"] = len(logs)
    receipt["output_count"] = 1


if __name__ == "__main__":
    component("summarize_run", summarize)
