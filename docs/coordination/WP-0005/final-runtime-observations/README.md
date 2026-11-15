# Completed Q0 author/reviewer runtime observations

Both actual unmodified-model trials completed **QUALIFIED_RUNTIME_OBSERVATION**: six checks pass and zero failures per run, twelve native calls total. Author run20261115T202627Z-eb5bf7da lasted1235.281s; independent reviewer run20261115T210422Z-565e2de9 lasted1266.187s. All four measured outputs are exactly equal across sessions in both token IDs and raw text bytes, and both fixtures are repeatable within each session. Warm-up is excluded. No accuracy score is computed.

[run-comparison.json](run-comparison.json) records exact executing heads, outcome/supervisor SHA-256 values, per-call times/tokens/pages/memory/fallback/cache behavior, four cross-session comparisons, storage floors and cold-load timings. Coordinator verified every native output text/token hash against the preserved actual raw files before deriving the comparison. Native domain outcomes and supervisors were assessed separately.

Reviewer launcher30436 and actual model worker30484 were directly observed absent at **2026-11-15T21:26:25Z**, with no Q0 child left. Sole reviewer lease **WP-0005-reviewer-005-20261115T205527Z is RETURNED**; author lease was already returned. [reviewer-exit.json](reviewer-exit.json) and [host-after-reviewer.json](host-after-reviewer.json) preserve observations. Host pass,58,207,043,584 bytes free, GPU1571 MiB used /14427 MiB reported free, desktop WDDM apps untouched. No GPU lease remains active.

Coordinator post-reviewer verification used accepted `q0.py verify-model <model-dir> --notices <notice-dir>` via host Python `-I -B`; [model-after-reviewer.json](model-after-reviewer.json) again verifies all18 pinned runtime objects and the notice, with no source/weight changes. This is read-only verification, not another model trial. External venv/wheels/model and both raw runs remain retained.

Independent reviewer /005 evidence/report publication and final coordinator /006 integration/disposition still follow. This receipt records completed actual runs and observed lease closure; it does not substitute for the separate reviewer's final verdict.
