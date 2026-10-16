# AI Frontier Watch: Source Plan

Checked on October 14, 2026. The reference date window for this source-discovery check is September 15 through October 14, inclusive, in UTC. A future live run must compute its own window from its actual execution date.

This is a source-discovery plan, not a completed pipeline run or an accepted evidence corpus. Feed access and metadata were checked; full content extraction, media retrieval, timestamped transcription, editorial review, and publication remain to be completed.

## Core Collection Sources

The nine configured endpoints cover five written feeds, two YouTube channels, and two podcast feeds. They represent nine configured producer groups; the final evidence must still establish at least six independent originating sources after item-level attribution and duplicate reconciliation.

| Source | Input | Editorial use | Main limitation |
| --- | --- | --- | --- |
| [OpenAI News](https://openai.com/news/) | RSS / written | Model releases, access changes, agents, and research announcements | Vendor statements require claim-level scrutiny |
| [Google AI](https://blog.google/innovation-and-ai/) | RSS / written | Model, multimodal, research, and product developments | Google and DeepMind are one producer group |
| [Hugging Face Blog](https://huggingface.co/blog) | RSS / written | Discover technical approaches and open-model releases | Attribute partner articles to their originating organizations |
| [Simon Willison's Weblog](https://simonwillison.net/) | Atom / written | Practitioner tests, reproducible examples, and model limitations | Personal experiments are bounded tests; the feed also includes unrelated material |
| [TechCrunch AI](https://techcrunch.com/category/artificial-intelligence/) | RSS / written | Industry reporting | Filter promotions and repeated announcements |
| [AI Explained](https://www.youtube.com/@aiexplained-official) | YouTube | Candidate analysis of model capabilities and research | Verify the full video, evidence, and timestamps; titles do not establish conclusions |
| [Matt Wolfe](https://www.youtube.com/@mreflow) | YouTube | Candidate release roundups and demonstrations | Inspect sponsors, promotional clips, test conditions, and short-form material |
| [Latent Space](https://www.latent.space/about) | Podcast | Technical interviews about models, agents, infrastructure, and research | Guests may be promoting their own work; audio and video copies count once |
| [Last Week in AI](https://lastweekin.ai/about) | Podcast | Weekly developments, interpretations, and links to original sources | Repeated headlines are discovery; accepted passages need substantive commentary |

Machine-readable endpoints and attribution notes are in [config/sources.json](config/sources.json). The two podcast URLs are mixed Substack feeds: their collectors must select entries with audio enclosures. Simon Willison's feed uses Atom rather than RSS 2.0 and must be supported by the feed collector.

## Endpoint Verification

All seven written or podcast endpoints and both YouTube discovery feeds returned HTTP 200 and parseable XML during this check. YouTube channel IDs were resolved from their public channel pages and checked against their channel feeds.

Recent-entry counts describe only the returned feed snapshots. They are not total publication counts, accepted evidence counts, or an assessment of substantive quality. Feed archives may be truncated; an eligible older item can be absent from the current snapshot.

| Source | Entries returned | Entries dated within the reference window | Audio-enclosure entries within the window |
| --- | ---: | ---: | ---: |
| OpenAI News | 1290 | 64 | 0 |
| Google AI | 20 | 12 | 0 |
| Hugging Face Blog | 876 | 16 | 0 |
| Simon Willison | 30 | 30 | 0 |
| TechCrunch AI | 20 | 20 | 0 |
| AI Explained | 15 | 4 | Not applicable |
| Matt Wolfe | 15 | 15 | Not applicable |
| Latent Space | 20 | 20 | 5 |
| Last Week in AI | 20 | 5 | 2 |

Google's older feed URL redirected to the canonical URL recorded in the configuration. Podcast audio enclosure URLs were present, but full audio downloads were not performed. YouTube publication metadata was verified through public Atom feeds; video content and captions have not yet been inspected.

## Candidate Starting Points

These are discovery leads, not accepted claims. Dates come from the publisher page or public feed. Video titles reflect the creator's framing and must not be adopted as factual conclusions.

| Date (UTC) | Candidate | Type | Suggested use |
| --- | --- | --- | --- |
| 2026-09-29 | [Introducing GPT-6.1 Sol](https://openai.com/index/introducing-gpt-6-1-sol) | Written / OpenAI | Investigate a model release and its stated capabilities |
| 2026-10-13 | [Gemini 4 Argon: Built to solve your hardest problems](https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-gemini-4-argon/) | Written / Google | Compare release claims, test conditions, and access |
| 2026-10-13 | [Run fast, private agents on-device with LFM2.5-24B-A2B](https://huggingface.co/blog/LiquidAI/lfm25-24b-a2b) | Written / Liquid AI, hosted by Hugging Face | Investigate an alternative deployment approach; count the originating producer as Liquid AI |
| 2026-10-13 | [llm-gemini 0.35](https://simonwillison.net/2026/Oct/13/llm-gemini/) | Written / Simon Willison | Inspect a practitioner's model test and its limits |
| 2026-09-24 | [Opus 5.5: How Close Are We to Automated AI Research?](https://www.youtube.com/watch?v=R9momwXV9w4) | YouTube / AI Explained | Candidate analysis of research capabilities; obtain and inspect the transcript |
| 2026-10-13 | [Google Just Caught Up (Gemini-4 Argon)](https://www.youtube.com/watch?v=eBszYxzE2dk) | YouTube / Matt Wolfe | Candidate release commentary; verify what was demonstrated |
| 2026-10-03 | [Last Week in AI #258](https://lastweekin.ai/p/lwiai-podcast-258-opus-55-sol-and) | Podcast / Skynet Today | The show notes place the Jev-related discussion at 29:34; verify the precise supporting audio passage |
| 2026-10-13 | [Dyna-2 interview with Jason Ma](https://www.latent.space/p/dyna) | Podcast / Latent Space | Candidate discussion of world-action models and physical agents; distinguish guest claims from verified findings |

Last Week in AI #258 was recorded on September 26 and published on October 3. Preserve both dates and explain the lag when assessing freshness. Do not count its embedded YouTube recording as another underlying item. The Dyna interview also has a video version; use it as one podcast item in this plan.

## Supplemental Primary Sources

These pages extend coverage of competitors and smaller teams. They are manual or optional-collector discovery routes, not configured as RSS feeds without a verified feed endpoint.

| Source | Why consult it | Collection status |
| --- | --- | --- |
| [Anthropic News](https://www.anthropic.com/news) | Primary announcements and supporting documents | News page inspected; no feed endpoint configured |
| [Mistral News](https://mistral.ai/news/) | Another producer's model announcements | News page inspected; no feed endpoint configured |
| [TypeSafe AI Blog](https://typesafe.ai/blog) and [Jev documentation](https://docs.typesafe.ai/introduction) | The user's example of an alternative model design | Product description checked; the Jev announcement date still needs verification |
| [Hugging Face Daily Papers](https://huggingface.co/papers) | Discover research behind technical developments | Discovery only; follow the original paper, authors, and publication history |

## Independence and Evidence Rules

- Attribute each retained item to its originating producer. Hugging Face hosting does not turn a Liquid AI announcement into an independent Hugging Face assessment. Google and DeepMind share one producer group.
- A creator, journalist, or podcaster repeating an announcement does not independently corroborate it. Identify original testing, reporting, interviews, or analysis and record what they actually add.
- A vendor interview can add distinct material, but repeating the vendor's earlier claim is not independent validation. Track both the publisher and the claim's underlying origin.
- Reconcile the same episode distributed as audio, YouTube, and an RSS link. Count underlying items once and retain all useful discovery URLs.
- Prioritize substantive new developments and relevant new analysis. Popularity is optional discovery context, not a selection requirement or ranking criterion. Explain sponsorships, commercial incentives, test conditions, missing perspectives, and uncertainty.
- Apply the live run's 30-date window to substantive material. Record publication dates separately from retrieval dates; exclude undated evidence until its date is established.

## Initial Collection Target

Collect at least six substantive written items, three distinct YouTube videos, and three distinct podcast episodes, spanning at least six independent originating sources after reconciliation. This is a suggested allocation of the assignment's minimum twelve items, not a claim that they have already been collected.

Prefer releases that connect across sources: a primary announcement, a bounded practitioner test, and a distinct interview or analysis can support a stronger argument than unrelated headlines. Save rejections and deferrals when evidence is weak. Each of the three final pieces still requires at least three independent sources and an insight connecting evidence.

The publication currently lacks a systematic sample of nontechnical users and independent controlled evaluations. Chinese and other non-US model developers also need stronger primary-source representation if selected developments involve them. Disclose these gaps rather than treating this starter list as comprehensive.
