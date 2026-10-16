# Collection Stage: Setup and Execution

Current project and publication status: see [README.md](README.md), [LIVE_RUNS.md](LIVE_RUNS.md), and [SUBMISSION.md](SUBMISSION.md). The stage-specific notes below retain the state and limitations of their recorded executions.

All 16 required scripts are implemented, including packaging, the full series workflow, and the `run.sh` entry point; see [PIPELINE.md](PIPELINE.md). Selection is documented in [SELECTION.md](SELECTION.md), briefs in [BRIEFS.md](BRIEFS.md), and content in [CONTENT.md](CONTENT.md). Student review/approval, two complete live runs on different days, video production, and publication remain to be completed. A collection-stage execution does not satisfy the requirement for two complete live publication-pipeline runs.

## Setup

Requirements: Python 3.12 or later, Bash, curl, FFmpeg/ffprobe, Node.js 22 or later for YouTube extraction, and network access. Install Python dependencies in the project environment:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

The pinned packages include `yt-dlp-ejs`, matching yt-dlp's own dependency
requirement. The [official EJS setup guide](https://github.com/yt-dlp/yt-dlp/wiki/EJS)
explains why YouTube extraction needs both those scripts and a supported runtime.

On this machine, macOS converted files in the Desktop virtual environment to
`dataless` cloud placeholders. Python imports stalled while retrieving package
files. The original environment is retained as `.venv-cloud-backup-20261014/`;
`.venv` now links to the project's local environment at
`/Users/zhoutong/.cache/mit1.125_ps04/venv-20261014`. Both are ignored by Git.
Other machines should create their own environment; do not copy this host's
absolute symlink as a portable dependency installation. For a cloud-synced
checkout, create the environment in a local cache directory and link `.venv`
to it. The ordinary install command above works through that link.

YouTube requests also stalled on the default connection path. A live IPv4
metadata diagnostic succeeded, so the extractor now passes `--force-ipv4`.
This changes the downloader's connection choice, not the machine's network settings.

YouTube uses yt-dlp to retrieve public audio and the OpenAI API to produce timestamped English transcription. Podcasts reuse a sufficiently complete publisher-provided timestamped transcript when available, falling back to the same API otherwise. Inaccessible media and failed requests produce explicit incomplete-stage receipts; they are not accepted as successful evidence.

## Configure API Transcription

Create an API key in your own [OpenAI account](https://platform.openai.com/api-keys), then enter it locally in the ignored `.env` file as `OPENAI_API_KEY=YOUR_KEY`. Alternatively, supply the `OPENAI_API_KEY` environment variable. Do not put the key in configuration snapshots, transcripts, or logs.

The provider settings are in [config/transcription.json](config/transcription.json). This implementation uses `whisper-1` with `verbose_json` and segment timestamps, as specified by the [official OpenAI transcription guide](https://developers.openai.com/api/docs/guides/speech-to-text). Long audio is compressed into chunks of at most twenty minutes, with timestamps offset back to the original recording. Fixed boundaries may cut utterances; review those passages.

The estimated rate is $0.006 per minute, checked on October 14, 2026 against the [official model page](https://developers.openai.com/api/docs/models/whisper-1). A thirty-minute recording therefore has an estimated transcription fee of $0.18. Fees and request outcomes are recorded in extraction receipts. Estimates are not a billing statement, and local compute/transfer remain unmeasured. Cached successful chunks do not trigger new requests on replay. A timed-out request may have been billed even without a retained response; summaries report `unconfirmed_api_requests` separately. Requests are not retried automatically. The model is selected for timestamp support; recheck model availability before future reuse.

The API integration passed offline checks with a simulated response, including missing-key and caching checks. A subsequent live pilot completed timestamped video transcription using the user's locally configured key. Its extraction receipt reports an estimated API fee of $0.124. The key is never included in this document or run snapshots.

## Start with Three Real Items

From the repository root:

```bash
bash workflows/start_collection.sh --sample
```

The sample selects Google AI, Matt Wolfe, and Latent Space, with one candidate per source. It skips YouTube Shorts. The run metadata records the actual UTC date and the limited collection scope. The full source list is retained alongside the exact source configuration used. All configuration and prompts are snapshotted. Earlier collection snapshots contain empty editorial prompts; preserve them as the actual inputs used. The four populated prompts have subsequently been executed in separate scoped selection, brief, and content runs.

To collect from all configured endpoints:

```bash
bash workflows/start_collection.sh
```

The current complete-run profile bounds discovery to at most 14 candidates: 9 written items, 3 videos, and 2 podcast episodes across 7 endpoints. The earlier profile allowed 17 candidates across 9 endpoints; its actual snapshots remain preserved. OpenAI article pages returned HTTP 403, and two long recordings had incomplete API transcription, so those unavailable inputs are explicitly omitted or deferred in the current configuration. The reason and original configuration are recorded in [source_recovery_plan.json](runs/20261014T233327Z-full-9be760/source_recovery_plan.json). These items are not described as recovered or counted as completed evidence. Feed contents may change between executions. This is a bounded feed scan rather than a complete archive search.

When YouTube RSS fails, the collector can discover the bounded public channel list with the installed yt-dlp, retaining upload timestamps and the original RSS error in its receipt. Explicit `exclude_item_ids` in a source definition skip known unavailable items before the limit is reached; skipped identities are logged. The current Latent Space profile defers the incomplete Lab-in-the-Loop recording and selects the next two available episodes. This is a discovery exclusion, not an AI accept/reject decision. Successful prior transcription responses remain cached for later recovery.

## Inspect the Result

Replace `RUN_ID` with the directory printed by the command:

```bash
cat runs/RUN_ID/summary.json
cat runs/RUN_ID/candidates.jsonl
cat runs/RUN_ID/eligible.jsonl
cat runs/RUN_ID/exclusions.jsonl
```

Candidate records describe discovery. Item records point to retained text, media, and segments. The corpus exports the latest stored versions; eligible and exclusion records apply this run's date window to that corpus. Current-run extraction counts can differ from eligible counts because previously stored evidence remains usable.

`collection_status` reports the collection stage. A collection-only execution remains incomplete as a publication pipeline. Current drafts with passing checks have overall status `awaiting_review`; a valid approved package has status `ready_for_production`, which does not establish publication. Article, script, and editorial-decision counts remain `null` when those stages have not run. The run scope and `complete_live_run` flag distinguish partial executions and offline fixtures from complete live runs.

## Recorded Pilot Results

The initial four collection pilots were executed on October 14, 2026. They are same-day collection tests, not the assignment's two complete live runs on different days. Subsequent bounded collection and recovery executions are documented in [EVIDENCE_INVENTORY.md](EVIDENCE_INVENTORY.md). The completed expanded corpus has 16 eligible items; its conservative provisional audit identifies 13 substantive candidates (8 written, 3 video, 2 podcast) across 9 originating producer groups. This does not replace editorial selection or student review.

| Pilot | Discovered | Extracted | New | Unchanged | Collection status |
| --- | ---: | ---: | ---: | ---: | --- |
| [Initial pilot](runs/20261014T170414Z-collection-6dc88e/summary.json) | 3 | 2 | 2 | 0 | Incomplete |
| [Second pilot](runs/20261014T170708Z-collection-0db78c/summary.json) | 3 | 2 | 0 | 2 | Incomplete |
| [API-path pilot](runs/20261014T171558Z-collection-b7eb11/summary.json) | 3 | 2 | 0 | 2 | Incomplete: API key missing |
| [Completed collection pilot](runs/20261014T172342Z-collection-c2ecd7/summary.json) | 3 | 3 | 1 | 2 | Completed |

The retained article contains 2,760 extracted words. The podcast has downloaded audio and 241 publisher-provided transcript segments covering approximately 72 minutes. These measurements establish extraction artifacts, not editorial acceptance or factual correctness.

The YouTube subtitle endpoint returned HTTP 429 in both pilots. The failure receipts remain accessible. After the first attempt, Node.js was explicitly enabled and caption selection narrowed to one English track; the endpoint remained rate-limited. No video evidence was invented or counted as successfully extracted. The implementation subsequently switched video transcription to the user-selected API approach; completing that stage requires the user's key and a successful live API request.

The second pilot retained the same two evidence versions and reported both as unchanged, demonstrating duplicate handling on real material. Inspect the run directories and component receipts for the saved inputs and outputs.

The API-path pilot successfully downloaded the video audio and retained its content-derived media path under `data/assets/downloads/`. It stopped transcription with an explicit missing-key error. No model request was sent and no paid transcription was performed. A later execution can reuse that audio once the key is supplied locally.

After the key was supplied locally, the completed pilot reused the video audio, generated timestamped API transcription, and stored one new video evidence version. All three input types were extracted and passed the mechanical date filter. The estimated transcription fee was $0.124; local compute and transfer costs remain unmeasured. At that pilot's execution, later editorial components were unfinished, so its saved overall status is `failed`. Subsequent editorial executions and completed workflow integration are documented separately; the historical pilot is not relabeled as a complete run.

The completed run's `replay_video_items.jsonl` records a later extraction replay using the same video version. Its separate extraction receipt reports one reused item and no model request. This replay incurred no additional API transcription fee.

## Replay and Retrieve Evidence

```bash
bash data/store.sh upsert runs/RUN_ID < runs/RUN_ID/items.jsonl
bash data/store.sh list
bash data/store.sh get ITEM_ID VERSION_ID
bash processing/filter_items.sh runs/RUN_ID < runs/RUN_ID/corpus.jsonl
```

Storage preserves all referenced versions and records each observing run. Replaying an existing item/version produces `unchanged`; retrieval-time changes do not create evidence versions. New substantive versions remain retrievable by their original IDs. Only the store component accesses `data/evidence/evidence.sqlite3`.

Version IDs hash compact, sorted JSON containing title, URL, publication date, extracted text, and transcript segments. Retrieval timestamps and incidental download filenames are excluded. Retained assets use content-derived paths and are not overwritten.

When a podcast's feed content explicitly embeds its YouTube recording, discovery records an `equivalent_item_ids` link. Reporting reconciles linked identities for evidence counts. Other cross-platform duplicates and source-independence judgments still require inspection; a repeated announcement is not independent corroboration.

## Verification

```bash
.venv/bin/python tests/test_collection.py
```

This single offline check exercises RSS/Atom parsing, podcast enclosure selection, timestamp parsing, the supplied store replay fixtures, historical-version retrieval, all date-filter fixtures, and rejection of invalid storage input. It also checks that a small embedded model card does not hide substantive text in the surrounding main element, validates API timestamps, and verifies that cached transcription avoids repeated requests using a simulated response. Fixture checks use temporary storage and do not pollute real evidence or incur API fees.

## Current Limitations and Media Retrieval

Written extraction uses a conservative HTML heuristic and retains original HTML for comparison. Inspect layout noise and completeness before accepting claims. API transcripts can contain recognition errors. Publisher timestamps delimit speaker turns; verify the particular passages used in publication.

Whisper's final timestamp can extend slightly past the actual recording. The
parser accepts at most one second of end padding and clips it to the probed
duration; larger, non-finite, reversed, or unordered timestamps remain invalid.
A live response overshot its chunk by approximately 0.537 seconds. Its raw
response and failed receipt were preserved, and the completed text was recovered
from the cache after this boundary check was repaired, without another model
request. The offline check covers both small padding and rejection of larger
overshoots. Review the last passage when using a boundary segment as evidence.

YouTube extraction reuses retained audio and transcription when native identity, title, URL, and publication metadata are unchanged. Downloads are retained even if API transcription cannot proceed. Podcasts refetch the page but reuse retained audio at an unchanged enclosure URL. In-place audio edits can therefore be missed; conditional media validation is a future improvement.

`data/media/` is excluded from Git. Item records retain the original source URL, audio enclosure URL when supplied, and local media path. To reconstruct omitted media, download the recorded podcast enclosure or rerun yt-dlp against the recorded video URL. Public availability can change; retain local media needed for your review and describe any retrieval failure.
