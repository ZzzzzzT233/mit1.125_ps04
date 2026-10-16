# Problem Set 4 — AI Frontier Watch

**Student:** Tong Zhou

**Repository:** https://github.com/ZzzzzzT233/mit1.125_ps04

Original course requirements are preserved in [ASSIGNMENT.md](ASSIGNMENT.md) and [ARCHITECTURE.md](ARCHITECTURE.md). Setup and entry commands are in [README.md](README.md).

## Topic and Audience

AI Frontier Watch covers new AI model releases, technical and research advances, and changes in companies, products, and the open-model ecosystem over the preceding 30 days. Readers are interested in technology and AI; no programming or machine-learning background is assumed.

The central question is: **What is substantively new, what evidence supports it, and what directions do these developments suggest?** Novelty matters more than popularity. Recent publication alone does not establish a new development. Unsourced rumors, event promotions, and claims without substantive support are rejected or deferred. Vendor claims, observed results, and analytical inferences remain distinct.

All publication content is in English. The three pieces examine access, evaluation, and the wider workflow and infrastructure around AI.

## Published Series

| Piece | Substack article | YouTube video |
| --- | --- | --- |
| A Release Is Only as Useful as Its Route to Users | [Article](https://tongzhou2.substack.com/p/a-release-is-only-as-useful-as-its) | [Video](https://youtu.be/sBxcOquNgms) |
| The Right Test Depends on the Job | [Article](https://tongzhou2.substack.com/p/the-right-test-depends-on-the-job) | [Video](https://youtu.be/8kLHG2qRHPQ) |
| The Hard Part Starts After the Model Works | [Article](https://tongzhou2.substack.com/p/the-hard-part-starts-after-the-model) | [Video](https://youtu.be/NURPMsMGosY) |

The audience videos were produced in Google Vids using six scenes and approved narration. Anonymous opening playback was checked, with measured durations of 200.001, 218.441, and 215.321 seconds. Fresh anonymous article requests showed their companion-video links. Full article URLs were saved in YouTube descriptions; clickability after the channel-verification prompt has not been reverified. See the [production record](runs/20261014T234433Z-full-4bc4b0/production/README.md) and [verification observations](runs/20261014T234433Z-full-4bc4b0/production/publication_verification.json). Full listening review of all audience videos is not claimed.

## Technical Demonstration

[Recorded technical demonstration — MP4](submission/technical-demo/technical-demo.mp4), approximately **4 minutes 12 seconds**. It is included in this repository; no separate hosted YouTube URL has been recorded. [Media verification](submission/technical-demo/verification.json) records its measured duration, streams, checksum, and checks. Temporary recording instructions and rehearsal scripts have been removed.

## Setup, Architecture, and Manual Handoffs

[README.md](README.md) provides dependencies, installation, credential variable names, entry commands, a pipeline diagram, and offline verification commands. [PIPELINE.md](PIPELINE.md) explains component responsibilities, stage replay, error reporting, and packaging. All 16 prescribed Bash entry points are implemented.

The two workflows coordinate collection and series generation. Only the store component directly accesses the persistent evidence index. Components exchange JSON Lines; retained assets and per-run snapshots make the process inspectable. The normal entry reaches article drafts, video scripts, source notes, and checks, then stops for student review. Packaging requires a matching approval fingerprint. Production and platform publication remain manual steps.

The implementation uses Python 3.12, SQLite, curl, FFmpeg/ffprobe, Node.js, and pinned yt-dlp/EJS packages. Recorded editorial calls used `gpt-6-luna`, and API transcription used `whisper-1`. `OPENAI_API_KEY` is supplied only through the environment or ignored `.env`. Further source access and setup details are in [COLLECTION.md](COLLECTION.md) and [SELECTION.md](SELECTION.md).

## Evidence and Two Real Runs

| Live lifecycle | Artifacts | Measured time | Estimated provider fee |
| --- | --- | --- | --- |
| October 14, 2026 | [Summary](runs/20261014T234433Z-full-4bc4b0/summary.json), [recovery](runs/20261014T234433Z-full-4bc4b0/recovery_record.json) | 736.56 s through initial post-recovery draft summary | $0.075230 |
| October 15, 2026 | [Summary](runs/20261015T185032Z-full-71d5e6/summary.json), [recovery](runs/20261015T185032Z-full-71d5e6/recovery_record.json), [draft index](runs/20261015T185032Z-full-71d5e6/REVIEW_INDEX.md) | 474.11 s through completion summary | $0.070438 |

Both lifecycles completed real collection, selection, briefs, articles, scripts, and checks, with documented recovery. Original failed entries remain preserved; they were not uninterrupted successful invocations. Costs are estimates, not invoices. Earlier failed-access attempts and unconfirmed request fees are accounted for separately in [LIVE_RUNS.md](LIVE_RUNS.md); local compute and transfer costs are unmeasured.

Configuration, policy, prompts, and pipeline code stayed unchanged between the two full runs. October 15 collected 7 new and 7 unchanged items, increasing the retained eligible corpus from 19 to 26. Selection changed from 15 accepted / 3 rejected / 1 deferred to 19 / 4 / 3. The new drafts add Muse Spark Open and Apertus 1.5 material; piece 03 reuses retained sources. Newly stored does not mean that an event happened that day.

The second eligible corpus includes 21 written items, 3 videos, and 2 podcasts across 11 producer labels. These are metadata counts, not proof of substantive quality or independent corroboration. See the [comparison](runs/20261015T185032Z-full-71d5e6/run_comparison.json), [duplicate/version records](runs/20261015T185032Z-full-71d5e6/changes.jsonl), and [date-filtered corpus](runs/20261015T185032Z-full-71d5e6/eligible.jsonl). The inclusive window is the execution date minus 29 days through that date. Dates, unknown/future items, duplicate replays, and retained versions are also covered by offline checks.

The original [source list](SOURCES.md), [evidence inventory](EVIDENCE_INVENTORY.md), and collection logs retain source limitations. Text and timestamped transcripts are under `data/assets/`; the persistent index is under `data/evidence/`. Omitted large media can be retrieved using the public URLs in item records and the documented collectors. Fictional examples and offline fixture runs are labeled and do not count as live evidence.

## A Published Claim Traced to Evidence

Article 01 states that Falcon-ASR had a demo while API access and native applications were planned in its October 14 evidence snapshot.

1. [Retained TII source](data/assets/858bf9b2909fe58763207e8ff1c0842b0c241cd19a553e30b4308bad04d87511/72f1079c2ffa7b4666d21915b0558d5f46fdeee282da019f33bb1e8898b1ba6e/text.txt): “API access and native applications are planned.” Publication date: October 7, 2026.
2. [Eligible source metadata](runs/20261014T234433Z-full-4bc4b0/eligible.jsonl): item begins `feed:7a6c7164`; version begins `72f1079c`.
3. [Editorial decision](runs/20261014T234433Z-full-4bc4b0/decisions.jsonl): accepts the source and explicitly distinguishes demo access from planned services.
4. [Brief 01](runs/20261014T234433Z-full-4bc4b0/briefs/01.md): claim `01-c3` links to that exact source version and passage.
5. [Approved article](runs/20261014T234433Z-full-4bc4b0/articles/01.md) footnote 3 and [matching script](runs/20261014T234433Z-full-4bc4b0/video_scripts/01.md) preserve the same claim. Both connect to the published pair above.

## Editorial Judgment and Approval

The policy was revised to prioritize substantive novelty over popularity and to include meaningful industry/product developments without requiring a new frontier architecture. The [before/after comparison](runs/20261014T193533Z-selection-9581af/policy_comparison.md) uses the same 16 source versions. Zenzap changed from rejected to accepted with commercial claims attributed; AI-security commentary changed from rejected to deferred pending stronger evidence. Accepted items changed from 12 to 13. Model variation prevents attributing every difference to one instruction.

[STUDENT_REVIEW.md](STUDENT_REVIEW.md) and [piece notes](student_review/) preserve the six-item review sample and comments on briefs, claims, independence, transcripts, and corrections. Those historical notes describe an earlier content version. The student later confirmed approval of the actual October 14 full-run drafts; [approval](runs/20261014T234433Z-full-4bc4b0/approval.json) matches the [current review](runs/20261014T234433Z-full-4bc4b0/review.json). The [production manifest](runs/20261014T234433Z-full-4bc4b0/package/manifest.json) contains nine matching approved assets. October 15 drafts have their own passing checks and await new approval; the earlier approval was not copied.

Corrections and reasons remain recorded, including exact quote locators, creator early-access context, simulation test conditions, and attribution. The second full run stopped on brief quote validation, then resumed through the existing correction mechanism without changing the source configuration or weakening checks. Raw responses and failed receipts remain accessible.

## Reflection

**Insight:** The series shows that a model release is only part of practical access. Downloadable weights, a hosted demo, planned API access, and paid product access serve different needs; the source comparison makes those differences visible.

**Limitation:** Exact reference checks can pass while a sentence still overstates the evidence. Vendor benchmarks, company interviews, and practitioner demonstrations require careful attribution, test conditions, and judgment about independence. Transcript text alone does not establish recording fidelity.

**Next improvement:** Strengthen the review of whether each claim is supported by its cited passage and whether its underlying event is new. Keep source-version references and human approval so revisions remain inspectable.

**Architecture tradeoff:** Small Bash entry points, JSON Lines, and SQLite make stages easy to inspect and replay. They require more coordination and validation between components. This fits a small, auditable course project while keeping publication decisions under human review.
