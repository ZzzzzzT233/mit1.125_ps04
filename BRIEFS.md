# Three English Editorial Briefs

Current project and publication status: see [README.md](README.md), [LIVE_RUNS.md](LIVE_RUNS.md), and [SUBMISSION.md](SUBMISSION.md). The stage-specific notes below retain the state and limitations of their recorded executions.

The brief component turns accepted, versioned evidence into three distinct
arguments for AI Frontier Watch. These are drafts for student review; they
are not finished articles, factual approval, or a completed publication run.

From the project root, for a run with retained eligible evidence and decisions:

```bash
bash editorial/create_briefs.sh runs/RUN_ID < runs/RUN_ID/decisions.jsonl > runs/RUN_ID/briefs.jsonl
```

The component uses the run's policy, project brief, and actual brief prompt.
It outputs exactly three brief records with piece IDs `01`, `02`, and `03`,
and saves readable copies in `RUN_DIR/briefs/01.md`, `02.md`, and `03.md`.
Each brief contains a question, central argument, synthesis, limitations,
and typed claims linked to exact written passages or media segment IDs.
`brief_coverage.json` records the items and producer groups actually used.

Only accepted items at their retained versions may support claims. Validation
checks exact quotes (at most 25 words each), existing segment IDs, unique
claims/pieces, three producer groups per brief, one multi-source inference
per brief, and all three input types across the series. These mechanical
checks cannot prove semantic support, novelty, or source independence.
Vendor claims, interview perspectives, and inferences remain distinguished.

The component reuses the selection transport, credential handling, pricing
settings, fee ceiling, raw-response retention, and fingerprinted cache.
It uses `gpt-6-luna` with the official
[Structured Outputs interface](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses).
No dependencies were added. See [SELECTION.md](SELECTION.md) for the shared
API setup and fee-estimate limitations. A repeated identical request uses
the retained response without a new provider request. No automatic retry
or silent evidence truncation occurs.

Insufficient evidence is an explicit failed stage with retained blocking
reasons. Invalid caller input exits 2; model/transport/validation failures
exit 1 without emitting unvalidated brief records.

```bash
.venv/bin/python tests/test_briefs.py
```

This single offline check uses fictional supplied evidence and a mocked
response. It validates references, source coverage, synthesis references,
blocking output, readable rendering, and cached replay without API fees.

## Completed October 14 Drafts

- [01: New AI releases: what you can use now, and on what terms](runs/20261014T195037Z-briefs-017322/briefs/01.md)
- [02: What the new AI evaluations show—and what they leave out](runs/20261014T195037Z-briefs-017322/briefs/02.md)
- [03: The next AI bottleneck may be the system around the model](runs/20261014T195037Z-briefs-017322/briefs/03.md)

Each brief has six typed claims. Prose and claim statements contain approximately
513, 550, and 541 words, excluding evidence locators. The briefs use 5, 4, and 3
originating producer groups respectively, and all three input types across the
series. These counts remain proxies for independence. The structured records
are [briefs.jsonl](runs/20261014T195037Z-briefs-017322/briefs.jsonl).

This `briefs_only` run carries forward the novelty-first selection and its exact
evidence versions. The [summary](runs/20261014T195037Z-briefs-017322/summary.json)
reports `brief_status: completed`; the overall pipeline remains incomplete.
One real provider response used 114,452 input tokens and 7,758 output tokens,
including reasoning, with a conservative estimated fee of **$0.018186**.
No recollection or retranscription occurred.

The first validation failed: one quote exceeded 25 words, and two table-row
quotes replaced original newlines with spaces. Assistant inspection added
support for multi-part claims, included table headers, corrected exact locators,
and narrowed prose lacking a matching claim. Original output and the failed
receipt remain preserved. The explicit
[assistant corrections](runs/20261014T195037Z-briefs-017322/brief_corrections.json)
identify the original output by digest; stale corrections fail. The component
replayed the cached response, applied these recorded corrections, revalidated
everything, and exported all three drafts without another provider request.
No student review or approval has been entered.
