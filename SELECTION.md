# AI Editorial Selection

Current project and publication status: see [README.md](README.md), [LIVE_RUNS.md](LIVE_RUNS.md), and [SUBMISSION.md](SUBMISSION.md). The stage-specific notes below retain the state and limitations of their recorded executions.

The selection component is implemented. It reads every date-eligible item,
its retained full written content or timestamped media segments, the project
brief, the snapshotted editorial policy, and the actual selection prompt.
It returns one English decision per item/version: `accept`, `reject`, or
`defer`, with a reason and intended piece IDs. These are proposals for the
student's review, not human approval or completed editorial briefs.

## Start a Selection Run

From the project root:

```bash
bash editorial/start_selection.sh
```

This creates a uniquely dated run, snapshots configuration and prompts,
exports the current persistent corpus through `data/store.sh list`, reapplies
the actual UTC date window, and invokes selection. It does not recollect
sources or retranscribe media. Metadata identifies the scope as
`selection_only`; it does not satisfy the two complete live publication-run
requirements. The existing ignored `.env` or environment variable supplies
`OPENAI_API_KEY`. Never put its value in snapshots or logs.

The independently runnable component is:

```bash
bash editorial/select_items.sh runs/RUN_ID < runs/RUN_ID/eligible.jsonl > runs/RUN_ID/decisions.jsonl
```

Input must match that run's entire eligible stream. The component reads
retained assets and uses the store's pure record validation function; it does
not directly access the canonical evidence index.

## Model, API, and Cost

[config/editorial.json](config/editorial.json) selects `gpt-6-luna` with medium
reasoning and a 16,000-token output limit. The
[official model page](https://developers.openai.com/api/docs/models/gpt-6-luna)
documents Responses API and Structured Outputs support. Its documented model
ID is an alias; the actual response model identity is retained. This model is
used for focused selection; editorial judgments still require review.

The [official Structured Outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses)
provides the JSON Schema interface. The component sends a strict schema to
`POST /v1/responses`, with `store: false`, no tools, and standard service tier.
It aggregates text across response output messages, rather than assuming the
first output entry is the answer. The complete public-source request and raw
successful response are retained for inspection.

Native curl uses IPv4. The authorization header enters through stdin and is
absent from command arguments and the retained request file. Provider error
bodies are not printed or retained, since they may echo credential fragments.
No new Python dependencies or SDK were installed for this stage.

Prices checked on October 14, 2026 are $0.10 per million input tokens,
$0.01 for cached input, $0.125 for cache writes, and $0.50 for output.
The documented long-context pricing multiplier applies above 272,000 input
tokens. The preflight uses a deliberately conservative byte-based token bound,
long-context multipliers, and a $0.25 estimated request-fee ceiling. It rejects
oversized inputs before reading the credential or making a model request; it
never silently truncates source content. For a larger corpus, explicitly split
or redesign the selection pass and preserve the changed inputs.

Receipts retain provider token usage and a conservative estimate that prices
all input at the cache-write rate, ignores cached-input discounts, and includes
reasoning tokens in reported output usage. These figures are estimates rather
than an account billing statement. Local compute/transfer and account-specific
billing adjustments are not measured. Missing usage and failed-request charges
remain unknown; requests are not retried automatically.

## Inspect and Replay

Each run saves:

- `decisions.jsonl`: the required structured decisions, in input order.
- `selection_report.md`: readable English reasons and provisional piece coverage.
- `selection_coverage.json`: accepted input types and originating producer groups.
- `model_calls/FINGERPRINT.request.json`: exact model input and schema, without credentials.
- `model_calls/FINGERPRINT.response.json`: the successful provider response, preserved even if downstream validation fails.
- `logs/select_items-UNIQUE_ID.json`: invocation times, counts, model, usage, fee estimate, and errors.
- `summary.json`: the stage status and counts, including incomplete executions.

A same-run invocation with the same model request reuses its response file and
incurs no additional model request. Changing evidence, dates, the model, or the
snapshotted prompt/policy changes the request fingerprint. Prior request/response
files and invocation receipts remain preserved. Use a new run for policy
comparisons; do not overwrite the original snapshots. Concurrent invocations
against the same run are not supported.

Output validation checks complete coverage, duplicate identities, exact
versions, decision values, piece assignments, and cited media segment IDs.
Invalid caller input exits 2; model/transport failures exit 1 and emit no
unvalidated decisions. Empty eligible input completes with zero decisions and
no model request. Refusals and incomplete responses are explicit failures.

Producer-group counts are proxies to inspect, not proof of claim-level
independence. The model can retain an announcement as evidence of what was
announced without treating the vendor's performance claim as independently
verified. Reasons require source inspection before publication.

## Verification and Remaining Work

```bash
.venv/bin/python tests/test_selection.py
```

This offline check uses the clearly fictional supplied examples and a mocked
response. It checks decision completeness, identities/versions, assignment
invariants, invalid segment references, incomplete/refused responses, credential
handling, the fee gate, and cache replay. It makes no paid API calls and does
not add fixture evidence to the persistent index.

The [October 14 live selection](runs/20261014T184854Z-selection-dfc589/selection_report.md)
processed all 16 eligible items: **12 accepted, 3 rejected, and 1 deferred**.
Accepted coverage is 8 written items, 2 YouTube videos, and 2 podcast episodes
across 9 originating producer groups. These counts do not establish independent
corroboration. Each proposed piece has at least 7 producer groups available,
but those selection-stage counts did not by themselves define final arguments
or claim-level support. Subsequent briefs and drafts are linked below.

The [first-pass summary](runs/20261014T184854Z-selection-dfc589/first_pass_summary.json)
records 110.26 seconds and a conservative model-fee estimate of **$0.020075**:
134,827 input tokens and 6,443 output tokens, including reasoning. There was
one completed provider request and no unconfirmed request in this stage.
A same-run cached replay produced byte-identical decisions without another
provider request. Offline selection checks passed. The overall pipeline status
remains incomplete even though `selection_status` is `completed`.

[Assistant spot-check notes](runs/20261014T184854Z-selection-dfc589/selection_review_notes.md)
identify a potentially over-narrow rejection of product/funding news and the
need to inspect underlying sources before rejecting an entire analysis video.
These notes preserve the model's original decisions and do not constitute the
student's required review or approval.

Student review must compare at least three accepted and three rejected/deferred
items, record corrections, revise the policy, and rerun the affected stage.
Article/script generation and mechanical checks are documented in [CONTENT.md](CONTENT.md). Workflow orchestration and approval-bound packaging are implemented in [PIPELINE.md](PIPELINE.md). Student approval, an actual approved package, two complete live runs on different days, and publication remain to be completed.
Brief generation and its three retained drafts are now documented in [BRIEFS.md](BRIEFS.md).

## Novelty-First Revision

The student subsequently clarified that substantive novelty matters more than
popularity. The revised policy and prompt prioritize the actual new contribution,
do not require high attention, distinguish recent reporting from new developments,
and allow meaningful product/industry changes without a frontier technical
breakthrough. The [revised live report](runs/20261014T193533Z-selection-9581af/selection_report.md)
records 13 accepted, 1 rejected, and 2 deferred items: 9 written items, 2 videos,
and 2 podcasts from 9 producer groups. The estimated model fee is $0.019960.

The [comparison](runs/20261014T193533Z-selection-9581af/policy_comparison.md)
preserves the original result and checks that all evidence identities and
versions match. Zenzap changes from rejected to accepted; the AI Explained
video changes from rejected to deferred. Model variation also affects outputs,
so this is an observed comparison rather than an isolated causal experiment.
This revision does not replace the student's required six-item sample review.
