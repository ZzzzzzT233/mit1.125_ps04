# Complete Live Run Record

**First complete live lifecycle:** `20261014T234433Z-full-4bc4b0`. Actual UTC start/as-of date: **2026-10-14**. Scope: `full_pipeline`; mode: `live`. This is real collection and provider generation, not a fixture.

**Current result:** `ready_for_production`; `complete_live_run: true`; final content checks pass. The initial entry exited 1 at quotation validation; the documented series recovery exited 0. This is a completed lifecycle with recorded recovery, not an uninterrupted successful entry invocation.

[Final summary](runs/20261014T234433Z-full-4bc4b0/summary.json) · [Content review](runs/20261014T234433Z-full-4bc4b0/review.json) · [Recovery record](runs/20261014T234433Z-full-4bc4b0/recovery_record.json) · [Code hashes](runs/20261014T234433Z-full-4bc4b0/execution_code.json)

## Results

- Discovered and extracted **14/14** current-run candidates from seven configured endpoints, covering written feeds, YouTube, and podcasts.
- Date-filtered persistent corpus: **19** distinct items, including previously retained versions. This is not 19 newly collected items.
- Storage observations: **0 new, 1 changed, 13 unchanged**; duplicate/version reuse is recorded.
- AI selection: **15 accepted, 3 rejected, 1 deferred**.
- Generated **three English briefs, three articles, and three matching video scripts**.
- Eligible metadata coverage: **14 written, 3 videos, 2 podcasts; 10 producer labels**. Substantive quality and claim-level independence still need student confirmation.
- Elapsed through the initial post-recovery summary (before student approval and packaging): **736.56 seconds** (12.28 minutes), including stage recovery.

## Drafts

| Piece | Title | Brief | Article | Video script | Length / estimated narration |
| --- | --- | --- | --- | --- | --- |
| 01 | A Release Is Only as Useful as Its Route to Users | [Brief](runs/20261014T234433Z-full-4bc4b0/briefs/01.md) | [Article](runs/20261014T234433Z-full-4bc4b0/articles/01.md) | [Script](runs/20261014T234433Z-full-4bc4b0/video_scripts/01.md) | 786 words / 3.96 min |
| 02 | The Right Test Depends on the Job | [Brief](runs/20261014T234433Z-full-4bc4b0/briefs/02.md) | [Article](runs/20261014T234433Z-full-4bc4b0/articles/02.md) | [Script](runs/20261014T234433Z-full-4bc4b0/video_scripts/02.md) | 819 words / 4.09 min |
| 03 | The Hard Part Starts After the Model Works | [Brief](runs/20261014T234433Z-full-4bc4b0/briefs/03.md) | [Article](runs/20261014T234433Z-full-4bc4b0/articles/03.md) | [Script](runs/20261014T234433Z-full-4bc4b0/video_scripts/03.md) | 891 words / 4.37 min |

## Commands and Recovery

The real entry command was `bash run.sh`. After the first quotation-validation failure, the series was replayed with `bash workflows/create_series.sh runs/20261014T234433Z-full-4bc4b0`, then its summary was refreshed. Selection and the original brief response were cached on replay; revised article and script requests were real provider calls.

1. The initial brief output contained two 27/28-word Flock locators. They were shortened to exact retained passages within the 25-word limit. [Correction record](runs/20261014T234433Z-full-4bc4b0/brief_corrections_initial.json) binds the original response digest.
2. Exact early-access and Google-briefing segments were added for the creator demonstration. [Current brief correction](runs/20261014T234433Z-full-4bc4b0/brief_corrections.json) preserves the reason and earlier correction.
3. The first article output failed because article 02 had 909 words. Its raw response and receipt remain preserved. After the evidence-reference update, a fresh article request produced valid drafts.
4. Final article word counts are 786, 819, and 891. Estimated narration is 3.96, 4.09, and 4.37 minutes at 135 words/minute. Actual rendered duration is still unmeasured.

[First-pass summary](runs/20261014T234433Z-full-4bc4b0/first_pass_summary.json) · [Initial entry stderr](runs/20261014T234433Z-full-4bc4b0/entry_stderr.log) · [Component receipts](runs/20261014T234433Z-full-4bc4b0/logs) · [Raw requests/responses](runs/20261014T234433Z-full-4bc4b0/model_calls)

The original failed `run_pipeline` coordination receipt remains visible in the summary’s history. Required substantive stages and the latest series/check results have completed; no historical receipt or exit code was rewritten.

## Source Access Recovery

Two prior full-scope attempts were incomplete and do not count as additional complete live runs: [Sandbox DNS failure](runs/20261014T233206Z-full-1f5ae6/summary.json) and [Access/transcription failure](runs/20261014T233327Z-full-9be760/summary.json).

- YouTube RSS returned 404. The collector now uses bounded public channel-page discovery via the installed yt-dlp, retaining upload timestamps and RSS errors in receipts. Existing successful video evidence was reused.
- OpenAI article pages returned 403. The current profile omits that endpoint.
- Lab-in-the-Loop and Last Week in AI transcription remained incomplete after real transport failures. The current profile explicitly defers/omits them and collects Dyna and the biology interview instead. Neither failed recording is counted as recovered evidence.
- A 60-second live transcription probe succeeded, but does not validate the failed long recordings or count as a substantive source.
- Original configuration and failure logs remain accessible in the [source recovery plan](runs/20261014T233327Z-full-9be760/source_recovery_plan.json). The final run snapshot contains the actual seven-endpoint configuration and its explicit item exclusion.

## Costs

Complete-run provider estimate: **$0.075230**, including its rejected original article response; no unconfirmed requests in this run. Estimates use conservative configured token rates and are not a provider invoice. Collection reused cached video transcription and publisher-provided podcast transcripts.

Across the failed access attempt, transcription probe, and this completed lifecycle, recorded known/estimated API fees total **$0.601943**. Two failed long-transcription requests have unconfirmed fees. The earlier sandbox DNS failure also carries a conservative unconfirmed-request marker in its receipt. Local compute, transfer, and actual billing remain unmeasured.

## Student Approval and Production Package

The student directly confirmed in conversation that the current drafts had been reviewed and no issues were found. The [approval record](runs/20261014T234433Z-full-4bc4b0/approval.json) is bound to review ID `4170d3c8b2b2f0a76e5dd34cf6278e60eb50fb51a5e1e3c1445574744550c19e` and recorded at `2026-10-15T02:46:13.024645Z` (October 14 in America/New_York). The reviewer is identified by role; no personal name or signature was invented.

The packaging entry command is `bash run.sh --package runs/20261014T234433Z-full-4bc4b0`. Fresh checks passed, and the [manifest](runs/20261014T234433Z-full-4bc4b0/package/manifest.json) contains nine verified assets: three articles, three matching video scripts, and three source-note files. Approved source drafts were preserved. Packaging made no model requests.

[Production and publication steps](runs/20261014T234433Z-full-4bc4b0/package/MANUAL_STEPS.md) · [Publication link record](runs/20261014T234433Z-full-4bc4b0/package/publication_links.json)

All three articles and all three Google Vids productions are published, with six real URLs recorded in [publication links](runs/20261014T234433Z-full-4bc4b0/package/publication_links.json). Each video has six scenes and approved narration. Anonymous playback started successfully; measured durations are 200.001, 218.441, and 215.321 seconds. Fresh anonymous article requests showed the correct companion-video links, although canonical URLs initially served stale cached versions. Full article URLs and sources were saved in YouTube descriptions, but the platform shortens external addresses and disables their hyperlinks until channel verification. This final student platform step remains pending. No full listening review is claimed. See [production record](runs/20261014T234433Z-full-4bc4b0/production/README.md), [verification observations](runs/20261014T234433Z-full-4bc4b0/production/publication_verification.json), and [production state](runs/20261014T234433Z-full-4bc4b0/production/publication_state.json). The refreshed summary includes the human-review wait; 736.56 seconds records the earlier collection-to-draft lifecycle.

## Second Complete Live Lifecycle — October 15

Run `20261015T185032Z-full-71d5e6` used the actual October 15, 2026 date. It completed live collection, selection, three briefs, three articles, three matching video scripts, and current content checks. The [summary](runs/20261015T185032Z-full-71d5e6/summary.json) reports `complete_live_run: true` and `awaiting_review`. Together with the October 14 lifecycle, this supplies two complete pipeline executions on different actual dates. New student review and approval remain pending.

Collection extracted 14/14 candidates: 7 new and 7 unchanged. The eligible retained corpus grew from 19 to 26 items: 21 written, 3 video, and 2 podcast items across 11 producer labels. Selection accepted 19, rejected 4, and deferred 3. These metadata counts do not establish substantive independence. The source configuration, policy, prompts, and pipeline code were unchanged.

Elapsed through the saved completion summary was **474.11 seconds (7.90 minutes)**, including stage recovery. The estimated provider fee was **$0.070438**, with no unconfirmed request in this completed lifecycle. This is an estimate, not an invoice. Collection reused retained media evidence; no new paid transcription was required.

The initial entry stopped because brief locators exceeded the 25-word limit or differed in capitalization. The [correction record](runs/20261015T185032Z-full-71d5e6/brief_corrections.json) also clarifies attribution, adds creator-context segments, and makes a planned feature's availability explicit. The existing series replay reused selection and brief responses, then made fresh article and script requests. Its exit code was 0; the original failed entry receipt and [first-pass summary](runs/20261015T185032Z-full-71d5e6/first_pass_summary.json) remain preserved. This is a completed lifecycle with recovery, not an uninterrupted successful invocation. A separate [sandbox DNS failure](runs/20261015T184946Z-full-a7a360/summary.json) is excluded from the completed-run count and retains an unconfirmed-request cost marker.

The first new pair uses newly collected Muse Spark Open material; the second adds Apertus 1.5. The third is a newly generated synthesis of retained evidence within the current date window. Newly collected does not mean that an event happened today, and the three new pairs are not all different events from yesterday.

[Review all new drafts](runs/20261015T185032Z-full-71d5e6/REVIEW_INDEX.md) · [Comparison](runs/20261015T185032Z-full-71d5e6/run_comparison.json) · [Recovery](runs/20261015T185032Z-full-71d5e6/recovery_record.json) · [Completion validation](runs/20261015T185032Z-full-71d5e6/completion_validation.json)

## Remaining Requirements

- Two complete live pipeline lifecycles on different actual dates are recorded. Review the October 15 drafts before approval-bound packaging or publication; no prior approval was copied.
- Student approval of the current drafts and production packaging are complete. Earlier editorial notes remain a record of the prior content-only version. Verify the final rendered videos, source credits, disclosures, and publication access during production.
- Three Substack/YouTube pairs are published and anonymous opening playback was checked. Complete YouTube channel verification and recheck external hyperlinks. The separate technical demo has now been recorded and is included at [submission/technical-demo/technical-demo.mp4](submission/technical-demo/technical-demo.mp4).

[Earlier editorial notes](STUDENT_REVIEW.md) · [Submission form](SUBMISSION.md)
