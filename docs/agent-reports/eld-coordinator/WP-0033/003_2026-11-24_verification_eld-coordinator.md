# WP-0033 /003 · Declaration erasure and feature attribution at write 8

**M1 reproduced both fixed-gain ranking predictions. M3 resolved a dominant pooled-row effect and a much smaller explicit box effect.** Both arms met the predeclared controls and numerical gates on one synthetic opening. None of the 52 single-thread CPU reads cleared either posting cutoff. [Author /001](https://github.com/jackgumpe/eledgercare/blob/394cfe4daf2a80dab0571db04c7f8c0477f546e0/docs/agent-reports/eld-owner-probe/WP-0033/001_2026-11-24_research_eld-owner-probe.md) · [Independent review /002](https://github.com/jackgumpe/eledgercare/blob/894a811ed499dc1045a3de256ef4ffe92582dc55/docs/agent-reports/eld-rd-reviewer/WP-0033/002_2026-11-24_review_eld-rd-reviewer.md) · [52 reconciled rows and roots](https://github.com/jackgumpe/eledgercare/blob/4ff27ec890419dbb24143b6bfdde283fa7359ba3/docs/coordination/WP-0033/reconciliation.json) · [M3 raw and normalized attribution](https://github.com/jackgumpe/eledgercare/blob/4ff27ec890419dbb24143b6bfdde283fa7359ba3/docs/coordination/WP-0033/value-reconciliation.json)

| Record | Binding |
| --- | --- |
| Canonical path and reservation | docs/agent-reports/eld-coordinator/WP-0033/003_2026-11-24_verification_eld-coordinator.md · sequence 003, verification · 297f028350b1521096061cf27c7ce89702b73e54 |
| Author and publisher | eld-coordinator · native local Codex on Windows · 01a20a53-eec1-72c1-864c-9f8be8f4aff5 · configured gpt-6.2-astra/xhigh |
| Repository, branch and worktree | Public jackgumpe/eledgercare · coordination/bootstrap · C:/Users/jackg/Asp.net Projects/eledgercare |
| UTC publication preparation | 2026-11-24T02:37:21Z |
| Accepted base and coordinator deliverable | da76b51172bd7a59828d0a9c0fe9306229f47932 · 4ff27ec890419dbb24143b6bfdde283fa7359ba3 |
| Author source, evidence, report | 6e0f1cd046ddc3683e8e9c532f75380e8d6cef29 · 8849be2f8f7fb83559d944e2db5527d9929aa8b7 · 394cfe4daf2a80dab0571db04c7f8c0477f546e0 |
| Independent source, sealed evidence, comparison evidence, review | e46e514c7863dacef44c28028fb24e98d9958451 · b65574714e8ffa3731a0f7f7c1f1fb560214adbb · 221101886159247b6a9da2571fffc04ee7bc8f83 · 894a811ed499dc1045a3de256ef4ffe92582dc55 |
| Previous report and next action | First coordinator report in WP-0033. Verify live branch refs and public objects at publication. |

## M1 · declaration-only gain

The first cell letter denotes the incoming prefix and the second denotes the declaration donor, which supplies the true owner. A positive margin favors Alder. Relative ρ scales the original signed subtraction, whose coefficient already includes donor β. Absolute η directly sets that coefficient, with η = ρβ. The two β values are 1.5943590403 and 1.5422530174 for Alder and Cedar. Relative 0.50 therefore requests absolute gains 0.79717952 / 0.77112651. Absolute 0.80 requests relative gains 0.50176904 / 0.51872163. Each operator cast its requested scalar to FP32 once. The absolute branch used its independently specified matrix operation order.

| Gain | Predicted numerators AA, AC, CA, CC | Observed numerators AA, AC, CA, CC | Native normalized margins AA, AC, CA, CC | Correct ranks |
| --- | --- | --- | --- | --- |
| relative 0.50 | +0.005418156, -0.002367816, +0.006917086, -0.000879178 | +0.005418153, -0.002367818, +0.006917086, -0.000879178 | +0.007285587, -0.004238650, +0.009333223, -0.001579851 | 4/4 |
| relative 0.80 | -0.022790508, -0.014393592, -0.021287212, -0.012906529 | -0.022790511, -0.014393595, -0.021287214, -0.012906528 | -0.032266552, -0.025908802, -0.030289069, -0.023349255 | 2/4 |
| absolute 0.80 | +0.005251815, -0.003118290, +0.006750771, -0.001629750 | +0.005251816, -0.003118290, +0.006750767, -0.001629749 | +0.007064722, -0.005586088, +0.009112485, -0.002930902 | 4/4 |

At fixed recipient and donor the raw numerator is P + ρL. The denominator is always positive. The predicted rank changes at −P/L, and η at that crossover is donor β times the relative root. The zero-budget bands in the evidence use the engineering tolerance on the signed analytical numerator and carry no sampling interpretation.

| Cell | P | L | Relative root | Absolute root |
| --- | --- | --- | --- | --- |
| AA | +0.052432596 | -0.094028881 | 0.557622251 | 0.889050076 |
| AC | +0.017675145 | -0.040085922 | 0.440931487 | 0.680027916 |
| CA | +0.053924248 | -0.094014325 | 0.573574805 | 0.914484175 |
| CC | +0.019166409 | -0.040091173 | 0.478070542 | 0.737305737 |

The predicted open interval for both original twins and for all four crossed cells is (0.4780705425, 0.5576222507) in relative units and (0.7373057367, 0.8890500764) in absolute units. The AA and CC raw numerators observed at their scheduled roots were +1.2734e−9 and −1.0575e−9, each inside its approximately 2.00e−5 budget. Their ranks are unresolved. The raw donor-contrast roots at fixed Alder and Cedar prefixes were 0.6443371239 and 0.6445809992. Normalizing each cell's read separately produces different donor contrasts. The Alder-prefix normalized contrast at relative 0.70 was −0.0000137165, inside its ±0.0000407477 budget. At relative 0.50 the observed normalized donor contrasts were +0.011524238 and +0.010913074.

Each operator ran the eleven relative settings on all four cells plus four absolute rows. Full erasure matched the archived native primitive. Omission agreed with the WP-0032 reconstruction. Held constant on each cell were the incoming write-7 prefix, α, direct-write β, donor key/value, literal anchors, readout and query. The query was used only to read. Every cell used its own recipient matrix in old @ k.

## M3 · pooled declaration row and explicit box

All four rows use the complete pooled donor window with only declaration span 7's explicit box selected from the box donor. The boxes' second coordinates were 486 and 487 on the 0–999 scale. Both native diagonals matched the archive. At depth zero the eight incoming matrices are zero. With t = β k[:32]·direction(q[:32]), the analytical literal score is t(a·v)/(|t|‖v‖ + 1e−8). The table gives the equivalent epsilon in value units (1e−8/|t|) and the attenuation |t|‖v‖/(|t|‖v‖ + 1e−8).

| Pooled / box | t | Effective epsilon | Attenuation | Native Alder / Cedar | Finite-epsilon margin | Native margin |
| --- | --- | --- | --- | --- | --- | --- |
| AA | +0.238919562 | 4.185509100e-08 | 0.999999988317 | +0.097942188, +0.144584939 | -0.046642741 | -0.046642751 |
| AC | +0.238868162 | 4.186409746e-08 | 0.999999988310 | +0.097333029, +0.143933862 | -0.046600824 | -0.046600834 |
| CA | +0.229506962 | 4.357166294e-08 | 0.999999987289 | +0.067331441, +0.080093041 | -0.012761592 | -0.012761600 |
| CC | +0.229450132 | 4.358245469e-08 | 0.999999987281 | +0.066684537, +0.079390176 | -0.012705634 | -0.012705639 |

The bias-free value layer makes the raw projections additive in the pooled row and encoded box. The next table gives the independent blockwise FP64 changes and the observed interaction among the four promoted FP32 raw value projections. Each observed interaction lies within its numerical budget around zero.

| Projection | Raw pooled change | Raw box change | Raw interaction | Four-cell budget |
| --- | --- | --- | --- | --- |
| Alder | +0.120066377 | +0.002303510 | +1.2642e-08 | 1.0318e-04 |
| Cedar | +0.243416797 | +0.002511696 | -2.0430e-10 | 1.1160e-04 |
| margin | -0.123350420 | -0.000208186 | +1.2847e-08 | 8.8425e-05 |

For normalized effects, positive means replacing the Cedar input with the Alder input raised the indicated score or margin. Each entry is the observed signed effect with its propagated zero budget in parentheses. F changes the pooled row at a fixed box. B changes the box at a fixed pooled row. Both paths reproduce the native diagonal contrast.

| Score | F at Alder box | F at Cedar box | B at Alder pooled | B at Cedar pooled | Interaction | Diagonal |
| --- | --- | --- | --- | --- | --- | --- |
| Alder | +0.030610748 (±0.000043305) | +0.030648492 (±0.000043280) | +0.000609159 (±0.000043906) | +0.000646904 (±0.000042680) | -0.000037745 (±0.000086586) | +0.031257652 (±0.000043293) |
| Cedar | +0.064491898 (±0.000044494) | +0.064543687 (±0.000044466) | +0.000651076 (±0.000045770) | +0.000702865 (±0.000043190) | -0.000051789 (±0.000088960) | +0.065194763 (±0.000044480) |
| margin | -0.033881150 (±0.000041188) | -0.033895195 (±0.000041186) | -0.000041917 (±0.000041865) | -0.000055961 (±0.000040509) | +0.000014044 (±0.000082374) | -0.033937111 (±0.000041187) |

The Alder-for-Cedar pooled swap raised the Cedar score more than the Alder score at each box. The explicit box swap acted in the same direction on the margin for both pooled rows. For the Alder pooled row its magnitude (0.00004191696644) exceeded the signed budget (0.00004186487168) by only 5.20948e−8. All three normalized interaction signs lie inside their respective four-cell budgets. The native margin diagonal was −0.033937111496925354. The pooled representation can already contain layout information, so this comparison distinguishes authenticated input channels on this opening.

## Verification and limits

- Both operators read the same immutable manifests, fitted probes and original thresholds. They ran independent source in isolated worktrees using the qualified Windows CPU environment, Torch 2.13.0+cpu, Python 3.12.10, deterministic algorithms and one intra-op and inter-op thread each. Source/argv, UTC releases and thread UUIDs are retained in the [dispatch](../../../coordination/WP-0033/dispatch.json). The [coordinator input check](../../../coordination/WP-0033/verified-inputs.json) covers both full-window archives and row identities.
- Each verified the six original score pairs in FP32 and the applicable read and post-write matrix bindings. All 52 measurement rows matched the independent ordered score bytes, read digests and matrix digests. All 52 failed the native top-score cutoff 1.0 and gap cutoff 0.10. The crossings of the raw numerator concern owner ordering at the declaration. The actual posting step lies beyond write eight.
- The predeclared engineering limit is 2e−5(1 + max(|observed|, |predicted|)) per scalar. Two contributing cell limits bound a difference and four bound an interaction. Across the 48 M1 rows the largest absolute native-margin difference from reconstruction using WP-0032 signed vectors was 4.339e−8. No tolerance was widened.
- Both frozen candidates completed on the first decisive execution. A coordinator manifest inspection initially iterated over the historical M3 aggregate D0 as if it were a cell. The explicit 0A/0C lookup passed before the candidate releases. The reviewer's detailed comparison and any operational issues are recorded in /002.

The reviewer independently accepted both arms and recorded 11,100 numerical and 22,432 exact cross-implementation checks, including row-level identities. The reviewer also recalculated the author's 8,700 M1 and 1,135 M3 scalar gates. [Comparison evidence](../../../reviews/WP-0033/evidence/comparison.json)

The coordinator reconciled committed evidence using these commands from the primary checkout.

~~~powershell
python -I -B docs/coordination/WP-0033/compare_rows.py 8849be2f8f7fb83559d944e2db5527d9929aa8b7 b65574714e8ffa3731a0f7f7c1f1fb560214adbb docs/coordination/WP-0033/reconciliation.json
python -I -B docs/coordination/WP-0033/check_values.py 8849be2f8f7fb83559d944e2db5527d9929aa8b7 b65574714e8ffa3731a0f7f7c1f1fb560214adbb docs/coordination/WP-0033/value-reconciliation.json
~~~

## Disposition and future decision

Accept M1's prespecified relative-0.50 prediction and the separate absolute-0.80 comparator on this exposed opening. For a separately released test, freeze **relative ρ = 0.50 on the declaration write only** before seeing fresh synthetic owner pairs. Evaluate at the actual posting target against native M1 and the M2 symbolic benchmark. Report both twins correctly ranked, correct postings per eligible target, wrong postings and abstentions. Earlier writes must remain native to test this declaration-only finding.

Accept M3's input accounting. Inspect the pooled declaration representation's value-to-anchor alignment first in any separately released M3 work, retaining the explicit box control. The smaller geometry contribution was measured on this opening. Architectural efficacy on other cases remains unmeasured. Both gains were chosen with prior knowledge of this one opening shared by two binder lengths. The packet ended at write eight.

## Changed files and external effects

The following paths changed between the accepted base and the disposition deliverable. The subsequent metadata adds this report, ledgers and the public download receipt. Both worker histories were preserved and fast-forward integrated into the primary checkout. The existing 99 worktrees, original stash and 73 preserved working files passed the inventory check. Two owned worktrees and packet scratch were added. Publication used the existing public repository and the three owned branches.

~~~text
CURRENT.md
INDEX.md
docs/agent-reports/eld-owner-probe/WP-0033/001_2026-11-24_research_eld-owner-probe.md
docs/agent-reports/eld-rd-reviewer/WP-0033/002_2026-11-24_review_eld-rd-reviewer.md
docs/coordination/WP-0033/assignment.md
docs/coordination/WP-0033/check_values.py
docs/coordination/WP-0033/compare_rows.py
docs/coordination/WP-0033/contract.json
docs/coordination/WP-0033/decision.json
docs/coordination/WP-0033/dispatch.json
docs/coordination/WP-0033/reconciliation.json
docs/coordination/WP-0033/value-reconciliation.json
docs/coordination/WP-0033/verified-inputs.json
docs/research/WP-0033/attribution.py
docs/research/WP-0033/bindings.py
docs/research/WP-0033/erasure.py
docs/research/WP-0033/evidence/M1-bindings.json
docs/research/WP-0033/evidence/M1-checks.json.gz
docs/research/WP-0033/evidence/M1-controls.json
docs/research/WP-0033/evidence/M1.json
docs/research/WP-0033/evidence/M3-bindings.json
docs/research/WP-0033/evidence/M3-checks.json.gz
docs/research/WP-0033/evidence/M3-controls.json
docs/research/WP-0033/evidence/M3.json
docs/research/WP-0033/evidence/input-manifest.json
docs/research/WP-0033/evidence/parity.json
docs/research/WP-0033/evidence/runtime.json
docs/research/WP-0033/metrics.py
docs/research/WP-0033/run.py
docs/reviews/WP-0033/audit.py
docs/reviews/WP-0033/compare.py
docs/reviews/WP-0033/evidence/M1.json
docs/reviews/WP-0033/evidence/M3.json
docs/reviews/WP-0033/evidence/comparison.json
docs/reviews/WP-0033/evidence/inputs.json
docs/reviews/WP-0033/evidence/parity.json
docs/reviews/WP-0033/evidence/run.json
docs/reviews/WP-0033/run.py
docs/reviews/WP-0033/trial.py
~~~
