# WP-0041 / 001 — native development-field custody

| Reservation | Recorded identity |
| --- | --- |
| Report | `docs/agent-reports/eld-twin-custodian/WP-0041/001_2026-11-26_research_eld-twin-custodian.md` |
| Category and sequence | Research, packet-wide slot 001. [Coordinator reservation](https://github.com/jackgumpe/eledgercare/blob/5f73e671ccd2fc12eb0f2d85b2effae713dc867c/INDEX.md#wp-0041-layer-11-one-field-feasibility-and-handoff-rule-review) |
| Author and publisher | eld-twin-custodian, native Codex child `/root/layer_custody`, environment thread ID `01a21654-c9bd-7fb1-bc66-92e96459070c` |
| Model and effort | Requested `gpt-6.2-astra/xhigh` in the packet. This child exposes its thread ID and no separate model/effort attestation. |
| Environment | PowerShell 7.7.0, Git 2.55.0.windows.1, CPython 3.12.10. Guidance PDF read with pypdf 6.16.2. Frozen verifier uses the standard library, git and read-only pinned metadata/source files. |
| Timestamp | 2026-11-26T05:38:23Z |
| Repository, branch and worktree | jackgumpe/eledgercare, `research/wp-0041-custody`, `eledgercare-worktrees/w041-custody` |
| Base | Assignment ancestor `a0bf6122d082675d483ffd9aeb7f4dbedbfb174c`, execution reservation `5f73e671ccd2fc12eb0f2d85b2effae713dc867c` |
| Frozen source and evidence | Source `091a8e0557c264629612422dd59a6767771ef4c7`, evidence `2950a7e0b9a71bf43a00ff37ceb67af97da62de9` |
| Prior material | First packet custody report. [WP-0040 / 001 physical custody](https://github.com/jackgumpe/eledgercare/blob/5f73e671ccd2fc12eb0f2d85b2effae713dc867c/docs/agent-reports/eld-twin-custodian/WP-0040/001_2026-11-25_research_eld-twin-custodian.md) |
| Status and next owner | Ready for independent review by eld-rd-reviewer. eld-coordinator owns resource release and final disposition. |

## Summary

**One developer field has a verified source coordinate, original generated IDs and clean delimiters.** It is the first line item's Unit Price in the WP-0005 author's first measured F07 capture. The source PDF and raw stream both show `$28.50` in that column, equal to +2,850 signed minor units. The row's Net Line also reads `$28.50`, making row/column provenance material. The historical archive has zero complete native state traces and zero P1/P2 comparisons for the selected field. [Frozen field evidence](https://github.com/jackgumpe/eledgercare/blob/2950a7e0b9a71bf43a00ff37ceb67af97da62de9/docs/custody/WP-0041/field.json)

## Objective and decisions

Select at most one permitted native amount by source metadata and field order, verify its byte, model-token and image bindings, and identify exactly what a later experimental release would still need. The selection was frozen and sent to the coordinator before examining its contextual pieces or PDF cell edges. The field serves as a structural development probe. No published historical arithmetic trigger for it was found in the named released records. The WP-0040 denominator remains zero eligible physical families. [Selection rule and archive exclusions](https://github.com/jackgumpe/eledgercare/blob/091a8e0557c264629612422dd59a6767771ef4c7/docs/custody/WP-0041/intake.md)

The synthetic starter admission authorizes the F07 development input. WP-0005 is the first qualified native packet. Its F01 times, hours and quantities precede F07 and supply no monetary target. In the F07 author run `20261115T202627Z-eb5bf7da`, lexical capture order selects `F07.warm1`. On page 1, table 1 contains invoice metadata. The first eligible amount is in table 2, row 2 including header, column 5, after the line ID, SKU, description and quantity. Later WP-0007 dev invoices and WP-0015 dense dev also expose native IDs and independent layout. The WP-0024 H0 sensor's retained BF16 rows are measured at the *normalized final output* consumed by the head. Its FP32 span means and WP-0029 Cedar observations also lack the layer-10 exit and complete mutable pre-token state. No inspected authorized candidate supplied those snapshots in a higher priority tier. The intake's table lists the scope of that negative finding.

## Observations and position convention

Full decode of 2,558 original generated IDs yielded the exact 7,617 native UTF-8 bytes, SHA-256 `893bf5783fb25ba58cbff1a021d177bb6c7c30e55ac530fc9eaefa37fe4a517e`. Tokenizer JSON SHA-256 is `c55c165e32c5a67830362a53e1f548c8930dcc8469efa30ff3252a982799c589` at model revision `0480966938291445591f69f08a13b041c073a96a`. Original ID serialization, decoded text and metadata all match the original run receipts. The byte ranges below are zero-based and half-open.

| Piece | Generated index | Native ID | Byte interval |
| --- | ---: | ---: | --- |
| `<td>` | 618 | 128821 | [1823, 1827) |
| `$` | 619 | 6 | [1827, 1828) |
| `28` | 620 | 1449 | [1828, 1830) |
| `.` | 621 | 16 | [1830, 1831) |
| `50` | 622 | 1328 | [1831, 1833) |
| `</td>` | 623 | 128822 | [1833, 1838) |

Five field-branch decisions consume generated indices 618–622 and predict 619–623 inclusive. Native prompt length 827 and the preserved decode-loop indexing give absolute model input positions 1445–1449. These positions follow from source and observed IDs. The Q0 archive contains no independent per-field position tensor trace. There are four amount tokens and one complete closing token. Both isolation boundaries pass. No delimiter rule change or search for another field is needed.

The 612 × 792-point source page draws the fifth-column edges at x=344 and 398, and the L01 row spans y=504.50 to 529.50 from the PDF bottom. The selected string's baseline begins at (371.44, 519.00). The matching 2,550 × 3,301 RGB raster is recoverable from a committed synthetic derivative. Its 25,252,650 bytes match the native run's page-1 SHA-256 `6d49398a6e94f1ed8d9ee0e7b68678e69dd03d690f955c01edb94c458e29711c`. Four pixel checks intersect the printed grid. This independent developer-layout binding is distinct from the model's table-wide first-pass rectangle.

## Runtime gate and outstanding observations

The original native wrapper observed 2,558 decode steps, 30,696 DASH decode calls, 30,696 FP32 decode-attend calls, 12 dense SDPA prefill calls and zero non-DASH attention calls for F07.warm1. The archived runtime identifies Windows, NVIDIA GeForce RTX 5070 Ti, PyTorch 2.13.0+cu130, BF16 native model policy, DASH TopM=16, greedy temperature zero, no-repeat-ngram size 35 with 1,024-token window and enabled page-count guard. Native custom-code module cache hashes agree with the pinned files. The author lease `WP-0005-author-004-20261115T202152Z` and the independent Q0 reviewer lease were returned. No device, operator command or native/P1/P2 lease was released for WP-0041.

The first missing observation is h₀ after layer 10 and the full native state immediately before consuming generated index 618. The five decisions lack independently cloneable pre-state, h₁ and full post-state, K/V and DASH keys/routing indices, rotary/page counters, influencing mutable processor state, and raw/processed score bytes, masks and ties. Prefix strings, final cache lengths, aggregate call paths and normalized hidden rows from other captures cannot fill this gap. The native output's token and prefix hashes authenticate that branch's emitted history. They do not authenticate the unmodified document branch's mutable state across a replay.

A later exact stock observer could supply the missing native reference if its source, image bytes, native prefix, runtime and device were bound and deterministic. P1/P2 additionally require a reviewed branch implementation and actual isolated calls with byte comparisons at **every** position through the close, independent pre-state copies, correct single state advance and a preserved original branch. Arithmetic-trigger provenance remains a separate condition for a triggered pilot. Layer-11 accuracy, cost, parity, physical truth and improvements remain unmeasured. [Machine-readable gate and failed attempt](https://github.com/jackgumpe/eledgercare/blob/2950a7e0b9a71bf43a00ff37ceb67af97da62de9/docs/custody/WP-0041/verification.json)

## Change inventory and verification

| Path or action | Result |
| --- | --- |
| `docs/custody/WP-0041/intake.md` | Frozen selection, ordering, source/geometry methods and native evidence requirements. |
| `docs/custody/WP-0041/verify.py` | Frozen reader checks one field's full native decode, source and raster geometry, observed path metadata, receipt identities and historical lease. |
| `docs/custody/WP-0041/field.json` | Output from the final frozen verifier, including 32 pinned source blobs. LF SHA-256 `11aa760ae7f87abf21fe89c2dfc6e5dbc42f9f11bb65f6287588bc0d1ecf194a`. |
| `docs/custody/WP-0041/verification.json` | Actual attempts, exact failed command stderr, normalized output hash, denominators and missing observations. |
| This WP-0041 / 001 file | Canonical report committed separately after the source and evidence. |
| Source PDF and environment | `Get-FileHash` and `pypdf.PdfReader(...).pages` across nine pages matched the 215,820-byte supplied document, SHA-256 `3f4451dd3a1bd2dc37d50c5ddb720dfd37005f62c1da68a6b2958aa86db14264`. Read-only metadata inspection of the existing Q0 model directory covered the tokenizer/config and two decoder source files. |
| `git diff --cached --check` on initial source | Reported one blank final line before runtime checks. Removed in `e7a52c391beb6fd169dfed0b154c1ebe1ea9cb73`. |
| `python -I -B docs/custody/WP-0041/verify.py`, first frozen run | Final receipt check encountered a shadowed receipt dictionary, TypeError at line 217. The capture, rule and field stayed fixed. The correction changed four variable references. |
| Same command at `091a8e0557c264629612422dd59a6767771ef4c7` | Exit 0 in 1.56 seconds. Repeated at evidence HEAD and compared LF-normalized stdout to `git cat-file blob HEAD:docs/custody/WP-0041/field.json`, yielding all 14,313 canonical bytes identical. Scratch stdout remained under `C:/Users/jackg/eLedgerCare-Speed/WP-0041/custody`. |
| `git diff --check 5f73e671ccd2fc12eb0f2d85b2effae713dc867c HEAD`, `git diff --name-status`, scoped `coordination/push.ps1 -ExpectedHead <full-sha>` | Source diff checks passed, four deliverable/evidence files accounted for. Source and evidence remote refs matched their full SHAs. Final report publication SHA and remote receipt follow separately to the coordinator. |

The reviewer can reproduce the numerical bindings from the pinned source PDF and original native ID/raw files independently of this script. The complete artifact comparison spans the reservation through custody evidence. No external checkout, protected records, new OCR, runtime/model load, device query, P1/P2 or L2 execution was needed or performed. [Source and evidence diff](https://github.com/jackgumpe/eledgercare/compare/5f73e671ccd2fc12eb0f2d85b2effae713dc867c...2950a7e0b9a71bf43a00ff37ceb67af97da62de9)

eld-rd-reviewer receives the frozen field and evidence for independent reproduction. eld-coordinator owns disposition and any later finite release. This custody report supplies author verification only.
