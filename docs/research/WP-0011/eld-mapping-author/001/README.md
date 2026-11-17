# WP-0011 /001: CPU coverage diagnosis and prospective protocol

The candidate adds separate diagnostic measurements and a finite runtime adapter. It changes no model, parser, mapper, converter or historical score. Author verification is complete; independent /002 source/protocol review is next. Fresh WP11 content remains unread by this author, and actual /005 execution is unreleased.

## Exact source and executed evidence

- Root authority: `8d23d755a35be26ff29c319c527bd770abdcae4b`; accepted lane base: `956c056be2ec970340074871ecdd7e1a9855d944`.
- Additional adapter scope: `784e687b25aca3d726c5fbfed3c1b14745cb865d:docs/coordination/WP-0011/runtime-adapter-scope.md`.
- Public interface checkpoint: `63a14cafa1dee7db7cb70aca00cee529c46452fc`. Reviewer identified omitted unit/absence pairing constraints before final freeze; final contract binds those semantics without seeing examples or changing sealed fixtures.
- First complete source: `67615d2b76a92f42a65901deffcc47937f7615fc`. [Attempt 1](attempt-1/tests.json) ran22 checks:21 passed, one test errored because its existing `paired` call omitted the required completion argument. [Trace](attempt-1/stderr.txt), [command/exit](attempt-1/execution.json), and [supervisor output](attempt-1/stdout.txt) are retained. Historical diagnosis did not execute in that attempt. Failure evidence commit: `69bc9d7d39b583a06e3d2aa2c948d7017b36800e` (full identity is also checked in the final inventory).
- Corrected, decisive source: `adb51ac317db18950f3f1ef4629864127956eddc`; coverage tree `ed07a273a57a71b43b0fed9cea12a2245d7c7958`. Only the test invocation changed after the first attempt.
- Protocol SHA256: `b5b2b051d7b154d2696c83b99ce7712490686508147fe267a462c7b73db56ec8`.
- [Attempt 2](attempt-2/execution.json): `python -I -B qualification/coverage_v1/run_checks.py --out docs/research/WP-0011/eld-mapping-author/001/attempt-2`; exit0,22/22 checks passed, no skip. [Summary](attempt-2/summary.json), [checks](attempt-2/stderr.txt), [mocked operational evidence](attempt-2/stdout.txt), [full stage ledger](attempt-2/diagnostic-ledger.json), [144 consumed files and one public Git object](attempt-2/input-inventory.json).

All26 original full B0/v1 score objects and four exposed WP9 complete paired prediction/score objects reproduce exactly. The separate historical recovery score also reproduces. The original26 and exposed WP9 four remain distinct groups; combining them below audits accounting, not generalization. The tested source blocks model/renderer imports. Runtime tests use mocks plus two owned standard-library child processes to verify Windows job cleanup; neither future runtime root is created, no service is started, and no GPU is queried.

## Actual diagnosis

The primary historical frame contains30 documents,29 completed,2,291 expected field/cell slots. Presence evidence is eligible for2,096 slots and unavailable for195. These are diagnostic denominators, not a replacement for original family-weighted metrics. The original failed `SYN-MP-01-v2-skew-pos4deg` keeps15 fields and180 cells. A missing final raw file does not prove no recognition. Its separate completed recovery has `page_3:table:unsupported_span` and keeps195 unavailable slots for the new globally eligible presence rate; locally parsed positive evidence remains visible separately.

| Exposed group / slot kind | Exact payload present / eligible | Unavailable presence | Exact declared schema supported / known | Unknown schema support |
| --- | ---: | ---: | ---: | ---: |
| Original26 fields |302/346|15|278/361|0|
| Original26 cells |1568/1621|180|0/0|1801|
| WP9 four fields |38/39|0|0/39|0|
| WP9 four cells |88/90|0|0/0|90|

Old ground truth lacks the new condition-specific table annotations, so automated table support and row-local stage metrics are unknown here. The earlier independently reviewed manual table evidence remains separately attributed; no inferred annotations are silently added. Exact presence is bounded visible-payload evidence: it may be repeated, in a different row, or unrelated to a label. It is not character accuracy or semantic association correctness.

Among135 original fields with supported labels and unique exact label/value payload evidence, B0 credits109 and v1 credits128;15 unavailable fields and all nonmembers remain separately counted. This restricted diagnostic subset does not replace the full previously measured27-field gain. The unchanged full old score counts remain B0 fields193/361 versus v1 fields220/361, and cells730/1801 under both. Typed cells724/1801 retain six printed-correct unsupported units. All these documents are exposed; no new improvement claim is made.

The WP9 four retain the known neutral end-to-end result under both mappers:0/39 fields,0/90 cells and0/15 rows. The new presence measurements find38/39 field strings and88/90 cell strings in decoded same-page payload, while none of the39 exact declared field labels maps to its expected canonical field. Example `WP09-F01-v0`, expected `/expected_fields/0`, is `work_order_id='RPR-0006382'`; raw p1/b2 contains `Request key RPR-0006382`, with label span[0,11] and value span[12,23], yet no field candidate is emitted. The exact raw path and visible-leaf digest are in ledger `/documents/26/slots/0`. This supports a vocabulary/structured-coverage limitation. It does not establish that all uncredited cells were semantically recognized, and it does not turn the old zero score into an OCR accuracy metric.

### Bound examples by stage

The new ledger's `reused_reviewed_diagnosis` preserves the source JSON pointer, expected value, raw location, quote and attribution from `docs/research/WP-0009/eld-mapping-author/diagnosis/results/ledger.json`. That prior ledger and the actual raw/expected files are hashed in the input inventory.

| Stage evidence | Exact exposed anchor | What it establishes and leaves uncertain |
| --- | --- | --- |
| Recognition substitution | Prior ledger `/documents/0/items/22`; `SYN-WO-01-v0-clean`, stock_parts/P01/part_sku, raw p1/b28/r1/c0 | Expected `CAP-45-5MFD-440V`, actual native and mapped value `CAP-45-SMFD-440V`. Mapper did not create this character substitution. |
| Association | Prior `/documents/2/items/0`; skewed work order raw p1/b0/r2/c0-c1 | `Work Order ID:` is beside `WO-004192`; B0 chose `Property:`. Existing v1 corrects this same-row association; no treatment is added here. |
| Native structure / header matching | Prior `/documents/5/items/15`; `SYN-WO-02-v2-skew-neg3deg`, raw p1/b10 | `Action Performed` has colspan2 and five-cell data rows against four expected columns. Parser accepts this span, exact table matcher does not. This is not a global parser failure and is not repaired. |
| Actual parser rejection | Separate recovery, raw p3 table; new `/supplement_separate/0/parse_errors` | Unsupported rowspan produces the observed parser error. Local positive leaves elsewhere survive as evidence, while no global presence success/failure rate is asserted. |
| Vocabulary / unsupported table coverage | Prior diagnosis README and detailed ledger, F03/F08 | The reviewed audit found616 unsupported-table cells,568 locally exact and48 omitted. These overlapping barriers are not616 guaranteed recoverable values. |
| Typed conversion boundary | New `/documents/19/slots/45` and `/54`, plus corresponding raster/skew rows20/21 | Exact `2.00 GL` and `5.00 ST` have literal unit agreement but historical typed conversion rejects the units. Six slots total; this is not unread text. |
| Representation/scoring boundary | Prior `/documents/7/items/0`, address_bill_to | Native line breaks versus admitted comma-space line joining explain a string mismatch. The old audit retains ten such cases; no normalizer is changed. |
| Unavailable / unadjudicated | Original failed document index12; prior `/documents/2/items/11` for an ambiguous narrative | No failed-output recognition conclusion; unexplained narrative mismatch remains unadjudicated. |

The old manual categories remain named as old evidence, not recomputed under a new meaning:61 recognition/omission,12 native structure,873 field/table mapping,16 conversion/scoring,195 unavailable and150 unadjudicated slots, with overlap. New automatic flags have different definitions:94 nonobserved exact values;120 visible unsupported labels;111 B0 versus92 v1 mismatches despite unique/local exact payload;391 versus383 reused/multiple-occurrence ambiguities;576 unadjudicated;195 unavailable; six typed barriers. These counts are not a causal partition and must not be added to100%.

The historical typed `qty_unit` semantics validate supported unit spelling and compare numeric magnitude. A synthetic `2.00 HR` versus numeric target `2.00` still earns historical typed credit while a separate unit diagnostic can disagree with expected printed unit. This is a tested semantic blind spot, not an observed wrong-unit model result. Identifier comparisons retain leading zeroes. The original26 absence slots have17 unverified mappings; the WP9 four have four unverified absences. Zero detected nonempty violations cannot establish zero inventions. Original full absence, unmatched-candidate, parse and page metrics remain in the unchanged score packets.

## Prospective controlled protocol

Source [README](../../../../../qualification/coverage_v1/README.md), [interface](../../../../../qualification/coverage_v1/INTERFACE.md) and [protocol](../../../../../qualification/coverage_v1/protocol.json) specify the deterministic definitions. Three opaque families each have control/layout/vocabulary/degraded one-page conditions. Semantic slots, values, types, optional unit presence/value and explicit absent-blank meaning are paired. Degraded compares with its own control. Independent admission must establish visual fidelity and one-factor isolation; schema equality alone cannot. Each control's ideal native witness must recover all intended supported fields/tables/absences under both frozen mappers, not merely contain familiar labels. Witnesses are reference-only and never prediction inputs.

Public reservation `98a3a3f73df0e578ae98ebf3923db7ba4882d018:docs/evaluation/WP-0011/reservation/reservation.json`, SHA256 `ac58c97459b199232cb541ba2216159cada61db73b8e44abaa4128a22284cddc`, fixes12 IDs/48 artifact descriptors. The author has read only this public metadata, not any of those artifacts. Sentinel `WP11-F03-degraded-v0` is preselected before outputs. Author schedule: two historical excluded warmups then12 primaries; reviewer: same two warmups then one sentinel. First failure stops without retry, retains all12 primary rows and all9 matched pairs with eligible/unavailable counts. Twelve documents represent three families, and fixed condition order confounds time; no randomized causal estimate is claimed.

`runtime.py` is the bounded namespace adaptation of accepted mapping-v1 runtime. A passing isolation test checks that only provenance/names/schema/source-metadata keys differ and that model/render/call/resource/GPU/guard/warmup settings remain unchanged. CPU mocked outcomes cover normal completion, first scan failure, malformed records/outcomes and failed post observers. Exact observed source/input/lease authority, accepted /002, admitted /004 and explicit unseal are authenticated before opening any fresh artifact. Root-owned future release fields and proof routes are documented in the source README; there is no usable release in this candidate. Pinned external Q0 environment/model/dependency artifacts are reused read-only later, including the explicit torchvision local-SHA TOFU limitation. Desktop GPU sharing and WDDM unknown values remain disclosed; an exact root sole-model-job lease does not claim OS-exclusive hardware.

Next action is independent /002 inspection and reproduction on this exact source and evidence. This lane implements no quality treatment. The controlled matrix is needed to distinguish supported-control behavior from changes in arrangement, wording and scan quality before selecting another treatment. Neutral finite results will complete the later experiment without retries or tuning.
