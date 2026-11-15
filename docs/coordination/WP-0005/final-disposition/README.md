# WP-0005 final disposition

The unmodified-model Q0 trial and separate independent reproduction are **ACCEPTED** for the frozen runtime qualification. Both returned `QUALIFIED_RUNTIME_OBSERVATION`, passed all six checks, and completed all six native calls normally. All four measured outputs match within and across sessions; the two corresponding excluded warm-ups also match across sessions. No accuracy score is assigned.

| Binding | Exact revision |
| --- | --- |
| Packet base | `df9a2b50894f01987d779d7f9ae805794503ce6f` |
| Accepted harness core | `41d6204648e4115ab197507d1a22f6d5c7f3e784` |
| Author executing HEAD / evidence / report | `9e73ef86600b5e16f74b056676a6d3a4f1474058` / `6e5f87fe4d0e19338a387bb5870efd083b2b491c` / `72fffbcbfa47f3c93425d9de5f338e511df7da3e` |
| Independent executing HEAD / evidence / report | `c8daa97c5be6bc67931b215652a7a0f6ced621ef` / `acf2ce43ccb3c22883e9961f2c763a2ece11b54f` / `848fe70bd6d6fce9c958f11b76102d2fdfad77d4` |
| Coordinator integration | `8bb643ce79f3728fcf90b1ad4e08e9ab87e76982` |

[Publication receipt](reviewer-publication-receipt.json) binds the accepted report, exact origin refs, unchanged merged bytes and the earlier 96-blob audit. The earlier audit's pending-report field remains an accurate historical observation. [Runtime comparison](../final-runtime-observations/run-comparison.json) contains actual hashes, timings, page/token counts, memory and storage observations. Both model-worker identities in each trial were observed absent and both GPU leases returned. Author and reviewer CLI sessions completed successfully; the task environment and original run directories remain retained.

## Evidence reconciliation

Published reports remain byte-identical. The [author handoff](../gpu-reviewer-release/author-publication-handoff.md) corrects four `/004` prose statements using original evidence. Three additional `/005` prose statements are reconciled here and in reserved coordinator `/006`:

1. Excluded F01 warm-up comparison has **36 paired bounding-box tuples**, as recorded in the reviewer's own [check 14](../../../reviews/WP-0005/eld-q0-reviewer/runtime-005/checks/14-author-004-publication-verification.json), rather than the report's 37. The 19 differing token positions, identical non-coordinate text and maximum delta of 10 native coordinate units remain correct. Measured repeats match exactly.
2. `metadata-correction-acceptance.md` was first published at **`e0ee634f6a92624c8c305c1c8730f79e95b93647`**. The report's `4317ea99bb85b96983c7dc3a0ed828a0a6a6ed1f` is the preceding integration, not that receipt's publication.
3. Active Windows WDDM applications are recorded confounders. The two sessions produced identical corresponding outputs. These observations do not isolate the cause of wall-time variance, establish that desktop activity has zero effect, or prove determinism for other inputs or runs.

These corrections do not alter source, protocol, raw measurements or the bounded independent verdict. They require no additional model trial.

## Preservation and publication sequence

[Exact inventory](change-inventory.tsv) covers every path from the packet base through the coordinator deliverable, including itself. The unchanged frozen `verify-preservation.py` is run against that committed deliverable, with accepted core `41d6204648e4115ab197507d1a22f6d5c7f3e784`; its result is subsequently added as `preservation.json`. The reserved canonical coordinator `/006` report and final `INDEX.md`/`CURRENT.md` publication receipts follow as separately identified metadata. Their full commit identities belong in the final index receipt, avoiding circular self-identification.

The accepted F1 application and admitted corpus remain protected. Only synthetic dev F01/F07 v0-clean inputs were executed. No holdout/expected-value scoring, E1-E3 treatment, training, production OCR integration, customer data, deployment or legacy migration is released. The local torchvision SHA-256 TOFU exception and WDDM/timing/memory observation limits remain disclosed. Jack receives the completed Q0 result; no further agent execution is pending within this packet.
