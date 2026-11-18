# WP-0017 initial A1 findings

None of the six individual switch removals restored both inspection IDs. The prespecified rules selected three pair removals for replay on the same six pages. No configuration has advanced to the fresh 18-page evaluation. [Machine decision](a1-r1-machine-decision.json) · [Pair release](a1-p1-release.json)

All four controls reproduced the corresponding historical tokens, page texts, stops and source links on both windows. Ordinary Baidu took 99.33 seconds for the two windows and genuine full Carbon took 85.00 seconds. Inside the switchable implementation, all switches off took 98.14 seconds and all on took 87.20 seconds. Setup, three warm-ups per configuration and the subsequent forced-token probes were excluded from these clocks. Each individual switch timing has one observation per window. [Normalized measurements](a1-r1-normalized.json) · [Blind inventory](a1-r1-blind-inventory.json)

| Switch | Time saved when enabled alone | Time added when disabled in full Carbon | Error introduced when enabled alone | Correct ID restored when disabled |
| --- | ---: | ---: | --- | --- |
| S0 · silence the token streamer | −0.01 s | −0.32 s | None | None |
| S1a · group expert operations during prefill | −14.41 s | −0.72 s | None | None |
| S1b · batch expert operations during decode | +12.44 s | +13.41 s | Page 21 | None |
| S1c · fuse gate and up projections | −3.34 s | +1.78 s | Page 21 | None |
| S2 · gather sparse attention keys during decode | −2.27 s | −1.23 s | Page 21 | Page 37 |
| S3 · eight-token GPU bursts | −1.83 s | −1.11 s | None | None |

The time columns use the switchable all-off and all-on controls, respectively, and sum the two ordinary three-page window reads. A negative saving means the addition took longer. A negative removal cost means the removal finished sooner. These estimates depend on the other switches in the comparison. The machine record also gives per-window values, the corresponding differences against the genuine implementations and the probe clocks. [Timing and switch effects](a1-r1-machine-decision.json)

On page 21, ordinary Baidu emitted `I08O1-388` and full Carbon emitted `108O1-388`. Each of S1b, S1c and S2 independently reproduced that substitution in the otherwise native configuration. On the shared history, the full-span log-probability difference favoring the correct ID shifted from +0.05598 nats to −0.06894 nats. The first competing-token margin fell from 0.125 to a tie. [Field locators, scores and margins](a1-r1-machine-decision.json)

On page 37, full Carbon had already changed coordinate token 7 from 291 to 290 before it emitted `80I10-774` for `8OI10-774`. With the earlier token history held to ordinary Baidu's, the correct ID's log-probability advantage changed from +0.06961 to −0.05542 nats. Replaying Carbon's own history shifted the difference a further −0.13082 nats to −0.18624. Disabling S2 restored the ordinary reading on page 37 while leaving page 21 wrong. These results show contributions from the execution path and prior token history. [Prefix audit](../../reviews/WP-0017/evidence/A1-prefix-audit.json) · [Probe and free-read results](a1-r1-machine-decision.json)

One reporting defect matters when interpreting a tied step. The original reviewer table labelled the first entry returned by `topk` as the greedy choice. The capture separately recorded the model's actual `argmax`. Among 73 probe passes, 35 had tied top logits and 14 had different first-listed and selected tokens. For example, with S1c alone on page 37, tokens 26 and 1892 tied at 21.625. The model selected 26. Use the saved argmax for those 14 labels. The free readings, full-span scores and three selected pairs are unaffected. [All affected passes](a1-r1-probe-ties.json) · [Cross-check against the inventoried GPU files](audit_probe_ties.py)

The GPU lease finished both orders successfully. Board memory peaked at 9,304 MiB for the controls and 9,394 MiB for the single-switch tests. The original reviewer issued the GPU command. The coordinator ran that reviewer's frozen programs after publishing the blind inventory. Their 800 decision checks passed, and Astra's rule implementation selected the same three pairs. The independent reviewer's written disposition remains pending. [Signed operator command](../../reviews/WP-0017/commands/a1-r1.json) · [Reviewer availability](operator-availability.json) · [Pair release plan](a1-plans/a1-p1-pairs.json)
