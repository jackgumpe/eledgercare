# WP-0011 /009 bounded source correction

Corrects independent findings F002-01..03 under root authority `7a99cee83b6077c1e155ebf0cbfb6b3ebb3ad203`. The unchanged preliminary findings/evidence are `bb7d3df4d2d46af2c7116268254176b1ad1dde26:docs/reviews/WP-0011/eld-mapping-reviewer/source/findings-initial.md` and `attempt-2/probes.json`. This is author verification for independent final /002, not acceptance or inference release. Original /001 and its evidence remain immutable.

Exact clean merged pre-edit base: `b3d4da6f9e49e7ebd0e7eb71bb91ff0deb079806` after normal merges of only supplied root authority and preliminary reviewer publication. Initial prior author publication: `9ecf0de071a664f9f06ec043706705834a6abed0`. The merge imports public metadata and already published evidence only; no private corpus payload was read.

## Corrections and evidence

| Finding | Corrected behavior | Relevant evidence |
| --- | --- | --- |
| F002-01 visible HTML concatenation | Declared block/line boundaries become whitespace, genuine inline adjacency remains, hidden script/style/comments and attributes stay excluded. Unknown tags make the block and global presence rate unavailable; local positive evidence elsewhere survives. | `Visible.BOUNDARIES`/`INLINE`, `visible_units`, two additional diagnostic tests; all seven unchanged independent visible probes pass. |
| F002-02 returned observer failures | Pre/during/post captures require exactly two successful complete exact-device rows, bounded matching byte counts and no error/truncation/stderr. Post-validation errors produce exit1 and unavailable final observation; original rows and finalization errors are retained. Cleanup/post failure does not rewrite a completed active-phase call as failed. | Four unchanged independent actual-supervisor returned-row probes now fail safely; fourteen author pre/post fault cases cover nonzero/null exits, wrong device, empty capture, truncation, size mismatch and an explicit error despite exit0. A last-active-phase post failure retains all completed calls. |
| F002-03 impossible score history | `validated_calls` checks every scheduled row including excluded warmups, full order/count/known states/availability, completed prefix then failed or unavailable call and only not-run suffix. Completed observations require successful flags and untruncated raw with matching hash. Invalid packets reject before credit; legitimate failed/not-run rows retain denominators. | Revised-schema actual score-run test accepts the complete packet first, changes only the first warmup to failed, and requires `after first failure` rejection before any scoring artifact read. Positive finalization-failure scoring retains12/12 credits and nine eligible pairs; all-not-run state is accepted with unavailable rows. |

The original independent invalid-packet probe lacks the newly required run schema/failure/observation_status/raw truncation metadata, so its current rejection occurs earlier as `Malformed run result`. That legacy result alone is not evidence of first-failure progression. The author test `test_actual_score_run_rejects_otherwise_valid_completed_after_failed_warmup` closes that distinction using an otherwise valid revised record and the actual score-run entry point. Independent /002 must reconcile the revised boundary independently.

The entire runtime worker remains byte-identical to the prior accepted scoped adaptation, including model/session/render/call behavior. Q0/B0/mapping-v1 and all historical scorer/converter/mapper objects remain unchanged. Source-isolation testing now checks the complete worker and pinned model/render/call/guard/GPU/resource/warmup settings rather than asserting that the corrected supervisor has no changes.

## Frozen execution and retained attempts

1. Source/helper frozen at `d2a877f1907faaf5c7d490496184462b45fd43d2`, coverage tree `830d22452f2128b6183dc6af3752519dc101113c`. `python -I -B docs/research/WP-0011/eld-mapping-author/009/run_correction_checks.py docs/research/WP-0011/eld-mapping-author/009/attempt-1` exited0:26 author checks and18 unchanged independent probes passed. Evidence retained at `f08eece0de47f3a870bfd07c534d4aa2b6898b83` before any further edit.
2. Root identified that the old independent invalid-packet shape rejects before progression. Added the meaningful actual score-run regression above; this was a test-strengthening change, with no further functional correction. Final source frozen at `253519e07e7d45cf1f5ecb3e03053582f7f7d4cc`, coverage tree `6bdab544c9fe26cbf093cc765212db2a2e7a97a5`.
3. Same command with `attempt-2` exited0 at2026-11-17T09:19:21.839438+00:00:27/27 author checks, zero failures/errors/skips;18 legacy independent probes pass. All26 original full B0/v1 scores, four exposed WP9 complete paired predictions/scores and the separate recovery reproduce exactly. The original failed raw remains unavailable and primary; recovery remains separate.

Both attempts retain stdout/stderr, exact execution/source/helper/protocol identities, all author input hashes/full stage ledger/summary/tests, and complete independent public probe results. The independent helper functions are loaded unchanged from `c23a2f0cff3621f05fe1caa77b170167a2406876:docs/reviews/WP-0011/eld-mapping-reviewer/source/probes_v2.py`; its original main is not used because it pins the previous source/output directory. The owned orchestration verifies exact helper bytes before invoking those functions and supplies only owned scratch/output paths. Re-execution by the author is author verification with independent probe provenance, not new independent acceptance.

Final protocol SHA256 `03b13a41a0047c827af32e71209933700457a5dfd6d38ec106daed82ef5b9000`; orchestration helper SHA256 `f61a567a6000f33fee3c0046e430bd79eeb562b7e972957fde737a934d213b0c`. Actual Python3.12.10/PowerShell7.7.0 on Windows. No /009 execution failed. Prior author /001's test invocation failure and reviewer helper packaging failure remain untouched and are not erased by the passing corrections.

## Honest diagnostic effect

Historical end-to-end predictions/scores are identical. The new conservative visibility grammar changes diagnostic availability: `SYN-MP-02-v2-skew-neg3deg` p3/b10 contains unsupported `<MERGE>` and has123 slots; `SYN-MP-02-v3-hybrid-stamp` p3/b8 contains the same unsupported tag and has124. These247 slots become globally unavailable for new presence rates. The grammar was not expanded to force old counts. Local positive evidence elsewhere remains recorded, and every original historical field/cell stays in its end-to-end denominator.

| Primary frame | Prior /001 | Corrected /009 |
| --- | ---: | ---: |
| Documents / completed |30 /29|30 /29|
| Expected field/cell slots |2291|2291|
| Presence eligible |2096|1849|
| Presence unavailable |195|442|
| Old26 field presence |302/346,15 unavailable|282/323,38 unavailable|
| Old26 cell presence |1568/1621,180 unavailable|1364/1397,404 unavailable|
| Exposed WP9 field presence |38/39,0 unavailable|38/39,0 unavailable|
| Exposed WP9 cell presence |88/90,0 unavailable|88/90,0 unavailable|

The full nonexclusive flag changes are retained in each execution receipt and stage ledger. Reductions in some flag counts follow unavailable measurements, not quality improvements. Historical30 primary outcomes,2,291 expected slots and original failure are preserved. A syntactic HTML grammar is not CSS rendering or full semantic recognition; unknown markup abstention is conservative and may reduce coverage.

No fresh expected/reference/annotation/PDF/render/ideal-witness content, generation code, model/backend/renderer import, live GPU observer, inference, download or service was used. CPU probes use mocked observers and the existing bounded two-owned-child Windows job test; children are cleaned, no other owner is terminated, and no future runtime root is created. Fixed12-primary/two-warmup author and one-sentinel/two-warmup reviewer schedules, root source/admission/unseal/lease gates and desktop-sharing limitations remain intact. Next is independent final /002 on the exact corrected source and this evidence.
