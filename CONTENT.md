# English Article and Video-Script Drafts

Current project and publication status: see [README.md](README.md), [LIVE_RUNS.md](LIVE_RUNS.md), and [SUBMISSION.md](SUBMISSION.md). The stage-specific notes below retain the state and limitations of their recorded executions.

Read the concise editorial comments in [STUDENT_REVIEW.md](STUDENT_REVIEW.md). It links three article/video note files covering every claim and scene, with specific revisions and source checks. These notes refer to the earlier content-only version; its original drafts are unchanged. Student approval and packaging of the current full-run drafts are recorded in [LIVE_RUNS.md](LIVE_RUNS.md).

The latest complete live lifecycle and its new drafts are documented in [LIVE_RUNS.md](LIVE_RUNS.md). They have 786/819/891 article words and 3.96/4.09/4.37 estimated narration minutes. The review notes and retained drafts below describe the earlier content-only version; they do not approve the new live-run output.

The two content components generate three distinct article drafts and three
matching production scripts from retained brief/evidence versions. They do not
render videos, publish content, or enter student approval.

From the project root, for a run containing valid briefs and evidence:

```bash
bash content/write_articles.sh runs/RUN_ID < runs/RUN_ID/briefs.jsonl > runs/RUN_ID/articles.jsonl
bash content/write_video_scripts.sh runs/RUN_ID < runs/RUN_ID/briefs.jsonl > runs/RUN_ID/video_scripts.jsonl
bash review/check_content.sh runs/RUN_ID > runs/RUN_ID/review.json
```

Article generation must run first: scripts also read the actual matching
articles. Each content manifest contains `piece_id`, the repository-relative
draft `path`, and its `claim_ids`. Outputs are `articles/01.md` through `03.md`
and `video_scripts/01.md` through `03.md` under the run.

Article prose targets 600–900 words, excluding the source notes. Scripts have
separate narration and planned visuals, with scene times estimated at 135
spoken words per minute. Timing is an estimate, not a rendered-video duration.
The generator requires 3–5 minutes of estimated narration. Pauses, edits, and
transitions still need production checks in Google Vids or HeyGen.

The drafting helper shares transport, credential handling, fee limits, and
response caching with selection; the two modes have different schemas and
prompts. It loads and validates evidence behind each brief and preserves the
exact source versions. No dependency or SDK was added. Raw requests/responses
and stage receipts remain retained. See [SELECTION.md](SELECTION.md) for API
configuration, protected credentials, and fee-estimate limitations.

Readable footnotes are rendered directly from brief evidence, including media
timestamps. HTML comments preserve claim IDs without exposing them as reader
citations. `source_notes/PIECE.json` holds exact written passages or segment
IDs and versions. `video_scenes/PIECE.json` holds the generated scene structure.
Video descriptions have an explicit placeholder for the eventual article URL.

Citation numbers are normalized from explicit claim markers so that an article's
appearance order cannot point a reader to the wrong source. Receipts record
renumbering, while the original model response remains unchanged. Explicit
assistant refinements may be retained in `articles_corrections.json` or
`video_scripts_corrections.json`, bound to the original output digest. They
must pass the same validation; stale refinements fail. These records are
assistant edits, not student judgment or approval.

The checker validates files, manifests, exact evidence, dates, minimum producer
coverage, input types, footnote/claim binding, matching claim coverage, and
retained scene/Markdown consistency. Length deviations are review warnings.
It fingerprints the actual assessed drafts, briefs, source notes, date, and
referenced evidence: changed inputs produce a new `review_id`.

An assessment exits 0 even when `passed` is false; callers must inspect the
JSON. Operational failures use nonzero exit codes. A passing mechanical review
does not establish factual accuracy, independent corroboration, sound analysis,
or final approval. Only the student supplies the approval required for packaging.
If editing a script, keep its scene JSON and rendered Markdown consistent.

```bash
.venv/bin/python tests/test_drafts.py
```

This single offline check uses fictional example evidence and mocked responses;
it exercises reference binding, invalid claims/length, both drafting modes,
cache replay, source rendering, stable review fingerprints, stale edits, and
missing files. It does not make paid calls or alter the persistent evidence index.

## Completed October 14 Drafts

| Piece | Article draft | Words excluding sources | Video script | Spoken words | Estimated narration |
| --- | --- | --- | --- | --- | --- |
| 01: New releases and actual access | [Article 01](runs/20261014T212823Z-content-3b48fa/articles/01.md) | 775 | [Script 01](runs/20261014T212823Z-content-3b48fa/video_scripts/01.md) | 462 | 3.42 min |
| 02: Technical differences and evaluation limits | [Article 02](runs/20261014T212823Z-content-3b48fa/articles/02.md) | 732 | [Script 02](runs/20261014T212823Z-content-3b48fa/video_scripts/02.md) | 465 | 3.44 min |
| 03: Data, infrastructure, and system constraints | [Article 03](runs/20261014T212823Z-content-3b48fa/articles/03.md) | 769 | [Script 03](runs/20261014T212823Z-content-3b48fa/video_scripts/03.md) | 463 | 3.43 min |

The [mechanical review](runs/20261014T212823Z-content-3b48fa/review.json)
passes with warnings requiring student judgment and recording verification.
All three pairs cover their six brief claims and have readable source links;
media footnotes include exact segment times. No human approval is supplied.
The [run summary](runs/20261014T212823Z-content-3b48fa/summary.json) records
completed article/script stages and a passing review. Following workflow
integration, its refreshed overall status is `awaiting_review`: the full entry
point and packaging are implemented, but student approval has not been supplied.
This `content_only` run does not satisfy a complete live-run requirement.

Two real provider requests have a combined conservative estimated fee of
**$0.022515**, with no unconfirmed requests in this scope. No recollection,
transcription, or additional API requests occurred during cached refinements.
Local compute and transfer remain unmeasured.

The first article validation failed because the model numbered citations in
appearance order while sources were keyed by claim identity. Canonical
renumbering corrected that rendering mismatch; receipts and the raw response
preserve the original failure. Explicit
[article refinements](runs/20261014T212823Z-content-3b48fa/articles_corrections.json)
and [video refinements](runs/20261014T212823Z-content-3b48fa/video_scripts_corrections.json)
record attribution, access wording, technical explanations, and scope changes.
These are assistant edits, not student review or final publication approval.

The full workflow and packaging are implemented; see [PIPELINE.md](PIPELINE.md).
Current full-run drafts have student approval and a verified production package.
Remaining work: a second complete live run on a different date; actual Google Vids/HeyGen video
production; Substack/YouTube publication and cross-links; submission and demo.
