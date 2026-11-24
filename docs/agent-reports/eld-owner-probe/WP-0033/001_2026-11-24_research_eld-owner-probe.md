# WP-0033 / 001 — Declaration erasure and input attribution at write 8

- Report path `docs/agent-reports/eld-owner-probe/WP-0033/001_2026-11-24_research_eld-owner-probe.md`
- Sequence reservation [WP-0033, author slot 001](https://github.com/jackgumpe/eledgercare/blob/297f028350b1521096061cf27c7ce89702b73e54/INDEX.md#wp-0033-declaration-erasure-and-input-attribution-at-write-8)
- Category and author — research, `eld-owner-probe`. Published by the author.
- Session — native Codex author thread `01a20b5b-98f7-7d70-be9a-6619f6377ca2`, dispatched as `gpt-6.2-astra` with `xhigh` effort. That describes the session configuration. Independent backend identity and effective effort are unverified.
- Timestamp — 2026-11-24T02:33:59Z
- Repository and branch — `jackgumpe/eledgercare`, `research/wp-0033-write8`, Windows worktree `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/w033-author`
- Authority base — `da76b51172bd7a59828d0a9c0fe9306229f47932`. Assignment base — `297f028350b1521096061cf27c7ce89702b73e54`.
- Frozen source — `6e0f1cd046ddc3683e8e9c532f75380e8d6cef29`. Coordinator execution release — `6d018f51b0ed294d72ca72dbe71e259b64754a69`. Evidence — `8849be2f8f7fb83559d944e2db5527d9929aa8b7`.
- Previous related author report [WP-0032 / 001](https://github.com/jackgumpe/eledgercare/blob/707794967c4505131d8d8b5f9e08313d3e7ffa7f/docs/agent-reports/eld-owner-probe/WP-0032/001_2026-11-24_research_eld-owner-probe.md)
- Status — ready for independent review by `eld-rd-reviewer` and disposition by `eld-coordinator`.

## Summary

Halving M1's erasure at the declaration ranked the declared owner first on both prefixes for both donors. The Cedar-prefix, Cedar-donor cell had the smallest absolute numerator of the four. Its signed numerator was −0.000879178, over 43 times its zero budget. A fixed absolute erasure coefficient of 0.80 also gave four correct rankings. A relative multiplier of 0.80 ranked Cedar first in all four cells. None of the 48 M1 rows or four M3 rows met both frozen owner posting cutoffs of 1.0 for the top score and 0.10 for the score gap.

For empty M3 memory, moving from the Cedar declaration to the Alder declaration shifted the owner margin by −0.0339371115. Most of that shift followed the pooled row. The explicit box also shifted the margin toward Cedar at both pooled rows. With the Alder pooled row the box effect cleared the signed budget by only 0.000000052095. The normalized interaction remained unresolved. Both arms concern the same synthetic opening.

## Objective and controls

The unit was the shared first window of the matched 12- and 30-page development fixtures. The two sources have different pooled features and explicit boxes. The instrument authenticated both sensor archives, all required archive members, the 16-row source windows, the model-specific eventual queries, ordered literal anchors, fitted weights, discrete state and all four write-7 snapshot byte strings. The frozen primitives reproduced the seven prefix writes and six separate original controls. Every treatment used a fresh cloned state. It applied one observed declaration at depth zero and retained both registered owners. The latest write was window 1, page 1, span index 7. [Input receipts](../../../research/WP-0033/evidence/input-manifest.json) · [M1 bindings](../../../research/WP-0033/evidence/M1-bindings.json) · [M3 bindings](../../../research/WP-0033/evidence/M3-bindings.json)

The exact controls compared ordered scores, full read bytes, post-write matrix and owner-column digests, query, anchors, registry, controller, rank and threshold outcomes against the archive. Each value below is the concatenation of the two native FP32 scores in little-endian Alder, Cedar order.

| M1 AA | M1 AC | M1 CA | M1 CC | M3 0A | M3 0C |
| --- | --- | --- | --- | --- | --- |
| ae5239bd18d06d3c | 532aa63cf4c2773d | f4e91ebd4ab99c3c | 1496f83ca5778b3d | ea95c83d130e143e | e791883d5197a23d |

The numerical gate was `2e-5 × (1 + max(|observed|, |predicted|))`. A sign uses a zero reference, and a two-cell contrast or four-cell interaction sums the participating cell limits. All 8,700 M1 and 1,135 M3 scalar reconstruction comparisons passed. The largest ratio of residual to limit was 0.002064 for M1 and 0.008609 for M3. The latter came from coordinate 2 of the AC split value (zero-based). Both M3 native diagonals and all four relative-one M1 treatments matched the separate native controls byte-for-byte. M1's four relative-zero reads matched the archived omitted-term reconstructions within the frozen limits. [M1 controls](../../../research/WP-0033/evidence/M1-controls.json) · [M3 controls](../../../research/WP-0033/evidence/M3-controls.json)

## M1 results

The first letter identifies the prefix and the second identifies the declaration donor. Every cell recomputed the old matrix times the donor key across all 128 columns. Only the retrospective query used the owner slice. The sum of retained, direct and scaled erasure vectors was normalized once. Both fixed checks preserved alpha and the direct-write beta. Under relative 0.50 the effective absolute coefficients were 0.7971795201 for Alder and 0.7711265087 for Cedar. Absolute 0.80 executed as FP32 0.800000011920929, corresponding to relative coefficients 0.5017690443 and 0.5187216383. [All operands, gain casts, predictions, observed values and row-level sign budgets](../../../research/WP-0033/evidence/M1.json)

| Cell | Relative rank root | Absolute rank root | Numerator at relative 0.50 | Numerator at absolute 0.80 |
| --- | ---: | ---: | ---: | ---: |
| AA | 0.557622251 | 0.889050076 | +0.005418153 | +0.005251816 |
| AC | 0.440931487 | 0.680027916 | −0.002367818 | −0.003118290 |
| CA | 0.573574805 | 0.914484175 | +0.006917086 | +0.006750767 |
| CC | 0.478070542 | 0.737305737 | −0.000879178 | −0.001629749 |

The affine numerator has a positive intercept and a negative slope in every cell. Intersecting the four required inequalities gives the open relative interval (0.4780705424898513, 0.557622250664914) and the open absolute interval (0.7373057366972366, 0.889050076397909). AA and CC alone give the same bounds on this opening. The fixed-prefix **raw numerator** donor contrast roots are 0.644337123866865 for Alder and 0.6445809992383125 for Cedar.

Each of the four cell columns gives the empirical Alder score minus the Cedar score. The next two columns subtract the two donor margins at the named prefix. The final columns count correct, resolved donor ranks and record whether both original diagonals resolved correctly.

| Gain units | Point | AA | AC | CA | CC | Alder-prefix contrast | Cedar-prefix contrast | Correct | Both twins |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| relative | 0 | +0.0613581 | +0.0305285 | +0.0631514 | +0.0331556 | +0.0308296 | +0.0299958 | 2/4 | no |
| relative | 0.20 | +0.0418273 | +0.0169848 | +0.0437638 | +0.0196541 | +0.0248425 | +0.0241098 | 2/4 | no |
| relative | 0.40 | +0.0194643 | +0.0029237 | +0.0214927 | +0.0055961 | +0.0165406 | +0.0158965 | 2/4 | no |
| relative | 0.50 | +0.0072856 | -0.0042387 | +0.0093332 | -0.0015799 | +0.0115242 | +0.0109131 | 4/4 | yes |
| relative | 0.60 | -0.0054701 | -0.0114515 | -0.0034241 | -0.0088163 | +0.0059815 | +0.0053923 | 2/4 | no |
| relative | 0.70 | -0.0186988 | -0.0186851 | -0.0166762 | -0.0160831 | -0.0000137 | -0.0005931 | 2/4 | no |
| relative | 0.80 | -0.0322666 | -0.0259088 | -0.0302891 | -0.0233493 | -0.0063577 | -0.0069398 | 2/4 | no |
| relative | 1 | -0.0597598 | -0.0402048 | -0.0579287 | -0.0377543 | -0.0195550 | -0.0201744 | 2/4 | no |
| relative | root_AA | +0.0000000 | -0.0083906 | +0.0020493 | -0.0057442 | +0.0083906 | +0.0077935 | 3/4 | no |
| relative | root_CC | +0.0100087 | -0.0026627 | +0.0120538 | +0.0000000 | +0.0126714 | +0.0120538 | 3/4 | no |
| relative | midpoint | +0.0050489 | -0.0055231 | +0.0070978 | -0.0028677 | +0.0105720 | +0.0099655 | 4/4 | yes |
| absolute | 0.80 | +0.0070647 | -0.0055861 | +0.0091125 | -0.0029309 | +0.0126508 | +0.0120434 | 4/4 | yes |

At the scheduled AA root, the AA signed numerator was +1.2734210e−9. At the CC root, the CC signed numerator was −1.0574603e−9. Both fell within about 2.0000000e−5 of zero, while the three other cells at each gain had resolved signs. At relative 0.70, the **normalized** Alder-prefix donor contrast was −0.000013716519 against a 0.000040747677 zero budget. The Cedar-prefix contrast at that point resolved negative. The observed normalized contrasts use each cell's own read norm and finite epsilon.

## M3 results

Each hybrid retained all 16 pooled rows and metadata of the pooled donor and took only the declaration box from its box donor. The instrument recomputed the full 16 × 1312 input block and all frozen projections, checked unchanged rows and routed the pooled donor's observed event. It used the eventual query after a native write to eight initially zero matrices. The four signed retrieval scales cleared their own zero budgets.

| Pooled, box | Scale βz | ‖v‖ | ‖native read‖ | Alder score | Cedar score | Margin |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| AA | +0.238919562 | 3.582478 | 0.855924 | 0.097942188 | 0.144584939 | −0.046642751 |
| AC | +0.238868162 | 3.581233 | 0.855443 | 0.097333029 | 0.143933862 | −0.046600834 |
| CA | +0.229506962 | 3.427957 | 0.786740 | 0.067331441 | 0.080093041 | −0.012761600 |
| CC | +0.229450132 | 3.426669 | 0.786250 | 0.066684537 | 0.079390176 | −0.012705639 |

For each literal and their difference, the signed prediction was `t × (w·v) / (|t| × ‖v‖ + 1e−8)`. The multiplicative factors on the unit value direction ranged from 0.9999999872813932 to 0.9999999883167212. The evidence records unrounded alpha, beta, z, t, effective epsilon, denominators, full-window projected operands and FP64 split vectors per hybrid. [Hybrid inputs, lossless vectors and signed effects](../../../research/WP-0033/evidence/M3.json)

| Raw projection onto | Pooled contribution to diagonal difference | Box contribution to diagonal difference | Observed raw interaction | Four-cell zero budget |
| --- | ---: | ---: | ---: | ---: |
| Alder anchor | +0.120066377 | +0.002303510 | +1.2642342e−8 | 0.0001031753 |
| Cedar anchor | +0.243416797 | +0.002511696 | −2.0430196e−10 | 0.0001116006 |
| Alder minus Cedar | −0.123350420 | −0.000208186 | +1.2846644e−8 | 0.0000884254 |

Independent FP64 products of the pooled and encoded-box weight slices reconstructed the full-window FP32 value. All three diagonal additivity identities and all three zero-interaction identities passed. Each candidate's raw and normalized score increased on the native Alder diagonal, with the larger increase on Cedar.

| Normalized quantity | Pooled at Alder box | Pooled at Cedar box | Box at Alder pooled | Box at Cedar pooled | Diagonal | Interaction |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Alder score | +0.030610748 | +0.030648492 | +0.000609159 | +0.000646904 | +0.031257652 | −0.000037745 |
| Cedar score | +0.064491898 | +0.064543687 | +0.000651076 | +0.000702865 | +0.065194763 | −0.000051789 |
| Owner margin | −0.033881150 | −0.033895195 | −0.000041917 | −0.000055961 | −0.033937111 | +0.000014044 |

Both two-step paths reproduced the native diagonal margin shift. The pooled effects at the two boxes exceeded budgets 0.000041188087 and 0.000041186129. The box effect at the Alder pooled row was −0.00004191696643829346 against a 0.00004186487168073655 limit. At the Cedar pooled row it was −0.00005596131086349487 against 0.00004050934478640556. The interaction of +0.000014044344425201416 lay inside its 0.00008237421646714211 budget. The pooled channel can itself contain layout information. These observations distinguish the authenticated input blocks.

## Change inventory and verification

All five source paths are under `docs/research/WP-0033/`. The 11 evidence paths are under its `evidence/` directory. The separate report commit adds only the canonical /001 path above.

| Added paths | Contents |
| --- | --- |
| `run.py` | Candidate guard, immutable input loader, runtime checks, 52-row scheduler and failure accounting |
| `bindings.py` | Full-window authentication, baseline states, original controls and isolated declaration-event routing |
| `metrics.py` | Lossless values, native scoring, reconstruction and propagated uncertainty |
| `erasure.py` | Two FP32 operation orders, M1 signed vectors, roots and empirical contrasts |
| `attribution.py` | M3 hybrid projection, signed finite-epsilon scoring, block differences and paths |
| `input-manifest.json`, `runtime.json` | Git input and source digests, qualified runtime, actual argv, evidence SHA-256 inventory |
| `M1-bindings.json`, `M3-bindings.json`, `M1-controls.json`, `M3-controls.json` | Source and state identities, queries, anchors and six native controls |
| `M1.json`, `M3.json` | Detailed treatment tables, predictions, signed differences, signs and budgets |
| `M1-checks.json.gz`, `M3-checks.json.gz` | Every scalar/vector check with operands, signed residuals, comparison limits and status |
| `parity.json` | 52 unique comparison keys with native ordered score bytes and digests, promoted-read numerator and norm, and native-score margin |

Run from the author worktree after the coordinator's exact release:

```powershell
& 'C:/Users/jackg/eLedgerCare-Speed/WP-0030/runtime/venv/Scripts/python.exe' -I -B 'docs/research/WP-0033/run.py' '6e0f1cd046ddc3683e8e9c532f75380e8d6cef29'
```

One decisive invocation started 2026-11-24T02:28:54.856715Z and finished 02:29:04.979760Z, exit 0. Python 3.12.10, Torch 2.13.0+cpu, NumPy 2.2.6, deterministic algorithms, one intra-op and one inter-op thread. The attempt created and retained `C:/Users/jackg/eLedgerCare-Speed/WP-0033/author/6e0f1cd046ddc3683e8e9c532f75380e8d6cef29` with its authenticated stage, restricted runtime directories and evidence. All 52 rows completed in one attempt. Static AST parsing and `git diff --cached --check` passed before the source freeze. The handoff was read with pypdf after the optional `pdftotext` executable was unavailable.

The evidence packaging check verified the runtime inventory hashes, 52 unique scheduled identities, read/matrix digest lengths, score pair decoding and margin arithmetic, all gzip check statuses and both table lengths. An initial report-link check received an empty shell path and stopped before reading the report. The corrected check resolved the local report links and verified all 11 Git evidence blobs against the retained files. The original evidence and owned source ancestry were verified at the published branch head with the packet push helper. [Exact source diff](https://github.com/jackgumpe/eledgercare/compare/297f028350b1521096061cf27c7ce89702b73e54...6e0f1cd046ddc3683e8e9c532f75380e8d6cef29) · [Published evidence](https://github.com/jackgumpe/eledgercare/tree/8849be2f8f7fb83559d944e2db5527d9929aa8b7/docs/research/WP-0033/evidence)

## Handoff and limitations

This is author verification. The configured fixed checks were chosen with knowledge of this one development opening. Ranking and posting eligibility have separate gates. The actual posting target, fresh pairs, model fitting, GPU execution and a change applied to earlier writes were outside the experiment. Independent review and coordinator disposition remain pending. The next owners compare all 52 rows and their signed budgets on the frozen source and evidence revisions above. The author stopped at write 8 and has not inspected the WP-0033 review work.
