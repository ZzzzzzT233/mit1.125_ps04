# Editorial Notes — Piece 02

**Title:** What the new AI evaluations show—and what they leave out

**Reviewed:** 2026-10-14. **Disposition:** revise the specific points below before final approval.

[Dashboard](../STUDENT_REVIEW.md) · [Brief](../runs/20261014T195037Z-briefs-017322/briefs/02.md) · [Article](../runs/20261014T212823Z-content-3b48fa/articles/02.md) · [Script](../runs/20261014T212823Z-content-3b48fa/video_scripts/02.md) · [Exact evidence notes](../runs/20261014T212823Z-content-3b48fa/source_notes/02.json)

## Brief

- Keep the evaluation-focused argument and comparisons within their own tasks.
- Add the HiRO test-input condition to claim 02-c4 and both matching drafts.
- Explain what changed in the release separately from inherited architecture; add evidence before expanding that point.

## Six Claims

| Claim | Result | Comment | Locations |
| --- | --- | --- | --- |
| 02-c1 | Clarify | The article should say four experts are selected per MoE block. This architecture is inherited; do not present the expert count itself as the new advance. | [article](../runs/20261014T212823Z-content-3b48fa/articles/02.md:7), [script](../runs/20261014T212823Z-content-3b48fa/video_scripts/02.md:24), [brief](../runs/20261014T195037Z-briefs-017322/briefs/02.md:27) |
| 02-c2 | Keep | The table supports the mixed benchmark comparison. Keep vendor attribution, named baselines, and evaluation conditions. | [article](../runs/20261014T212823Z-content-3b48fa/articles/02.md:9), [script](../runs/20261014T212823Z-content-3b48fa/video_scripts/02.md:25), [brief](../runs/20261014T195037Z-briefs-017322/briefs/02.md:35) |
| 02-c3 | Keep | Both WER figures match the report. The public average and internal dialect test use different data and must remain separate. | [article](../runs/20261014T212823Z-content-3b48fa/articles/02.md:15), [script](../runs/20261014T212823Z-content-3b48fa/video_scripts/02.md:38), [brief](../runs/20261014T195037Z-briefs-017322/briefs/02.md:68) |
| 02-c4 | Revise | The within-3% result is reported when HiROv2 receives coarsened X-SHiELD data. Add that condition; it is not a blanket bound for the entire ACE-to-HiRO pipeline. | [article](../runs/20261014T212823Z-content-3b48fa/articles/02.md:21), [script](../runs/20261014T212823Z-content-3b48fa/video_scripts/02.md:51), [brief](../runs/20261014T195037Z-briefs-017322/briefs/02.md:79) |
| 02-c5 | Keep; audio check open | The publisher transcript supports the stated inputs and outputs. This is the co-founder’s technical description, not an independent performance test. | [article](../runs/20261014T212823Z-content-3b48fa/articles/02.md:27), [script](../runs/20261014T212823Z-content-3b48fa/video_scripts/02.md:64), [brief](../runs/20261014T195037Z-briefs-017322/briefs/02.md:93) |
| 02-c6 | Keep | Different tasks and references justify the bounded-comparison conclusion. Avoid a cross-domain winner or a claim of independently replicated results. | [article](../runs/20261014T212823Z-content-3b48fa/articles/02.md:29), [script](../runs/20261014T212823Z-content-3b48fa/video_scripts/02.md:11), [brief](../runs/20261014T195037Z-briefs-017322/briefs/02.md:101) |

## Article

- The piece usefully distinguishes benchmarks from universal model quality.
- Qualify the HiRO statistic with its test-input condition; specify routing per MoE block.
- Keep the internal/public ASR distinction. Dyna explains architecture here and should not read as an evaluated benchmark result.

## All Five Video Scenes

| Scene | Narration | Visual direction |
| --- | --- | --- |
| [Scene 1](../runs/20261014T212823Z-content-3b48fa/video_scripts/02.md:7) | Keep the warning that different tasks are not one contest. | Keep four task tiles; do not create a shared score axis. |
| [Scene 2](../runs/20261014T212823Z-content-3b48fa/video_scripts/02.md:20) | Per-block routing is clear; preserve vendor attribution for comparisons. | Label the routing diagram illustrative and benchmarks company-reported. |
| [Scene 3](../runs/20261014T212823Z-content-3b48fa/video_scripts/02.md:34) | Keep the two WER datasets separate. | Use two distinct cards; no direct head-to-head accuracy chart. |
| [Scene 4](../runs/20261014T212823Z-content-3b48fa/video_scripts/02.md:47) | Add “when given coarsened X-SHiELD data” to the within-3% claim. | Label the reference and input condition beside the statistic. |
| [Scene 5](../runs/20261014T212823Z-content-3b48fa/video_scripts/02.md:60) | Keep the co-founder attribution and bounded conclusion. | Keep the diagram as a company-described architecture, not demonstrated autonomy. |

## Evidence and Remaining Checks

- [Run fast, private agents on-device with LFM2.5-24B-A2B](https://huggingface.co/blog/LiquidAI/lfm25-24b-a2b) · [retained text/transcript](../data/assets/856ea6764a22dce8df7ffc75c89574e829ff62de706651994f561c3f79f3ee7d/1ac3f1cf2a149fc1be6b8ee3807f82dc93b1e752754ad5ffc67091e7de97160d/text.txt).

- [Introducing Falcon ASR](https://huggingface.co/blog/tiiuae/falcon-asr) · [retained text/transcript](../data/assets/858bf9b2909fe58763207e8ff1c0842b0c241cd19a553e30b4308bad04d87511/72f1079c2ffa7b4666d21915b0558d5f46fdeee282da019f33bb1e8898b1ba6e/text.txt).

- [HiRO-ACEv2: Simulating extreme weather at 3 km resolution for a fraction of the cost](https://huggingface.co/blog/allenai/hiro-acev2) · [retained text/transcript](../data/assets/70bc304929c28abf44b723574ae63a984072e44976033d1e1b612c759cfb4baf/347feda09f10a36f91fcebf27f2cb941254596fb8682d717b46e8f806db78699/text.txt).

- [Dyna-2: General Purpose Physical Agents with Hour-Long Autonomy — Jason Ma, Dyna Robotics](https://www.latent.space/p/dyna) · [retained text/transcript](../data/assets/3bb68713a78830a8a51788de85e86d24640d4e655ef81e435e48bc9cb9e27ce8/f64a606580eb9edf5dd23191b9292737d4e0411a2640395aaedede16ce22520c/text.txt) · [timestamped segments](../data/assets/3bb68713a78830a8a51788de85e86d24640d4e655ef81e435e48bc9cb9e27ce8/f64a606580eb9edf5dd23191b9292737d4e0411a2640395aaedede16ce22520c/segments.json).

Written references resolve to retained versions. Article length is 732 words; narration is an estimated 3.44 minutes. Production timing has not been measured.

**Still required:** audio/visual recording checks for cited media, resolved edits in the actual draft files, a fresh content check, and final student approval. These notes do not record a completed listening/viewing audit.

**Version:** `20261014T212823Z-content-3b48fa`; review ID `2998a175670435f357de9d81b6858de5a1158b52674695d74574289eed961524`. Notes do not change or approve this version.
