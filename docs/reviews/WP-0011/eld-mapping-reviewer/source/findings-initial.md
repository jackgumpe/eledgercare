# WP-0011 /002 preliminary independent source findings

This is an immutable preliminary evidence exchange, not canonical /002. Reviewed source `adb51ac317db18950f3f1ef4629864127956eddc`, coverage tree `ed07a273a57a71b43b0fed9cea12a2245d7c7958`, protocol SHA256 `b5b2b051d7b154d2696c83b99ce7712490686508147fe267a462c7b73db56ec8`. Actual review began `2026-11-17T08:57:30.9357748Z` at normally merged HEAD `a1dcf1a8318b88ca4fd6886c5e6f650299298c31`, under root authority `d1fc5ac96cd3518eaa2b35118f8bd5967335602c` and author publication `9ecf0de071a664f9f06ec043706705834a6abed0`.

Independent owner eld-mapping-reviewer, stable existing native Codex session, requested xhigh; actual backend/effort not exposed. No reviewed implementation authorship or subagents. Generic examples below are newly authored public test data. No sealed contents were read for these probes. No live observer, GPU/model/backend/renderer call, service or inference occurred.

The original reviewer helper is frozen at `cdb6f7069ffe29e7a56f6a9169716ef7e5773b78`. Its packaging failed because the output directory was absent; the original helper and transcribed actual tool receipt are preserved. The corrected version `probes_v2.py` was frozen at `c23a2f0cff3621f05fe1caa77b170167a2406876` before execution. Exact evidence: `attempt-2/probes.json`. Command: `python -I -B docs/reviews/WP-0011/eld-mapping-reviewer/source/probes_v2.py docs/reviews/WP-0011/eld-mapping-reviewer/source/attempt-2`, using existing recovery venv Python 3.12.10. Actual tool chunk `3fd57c`, exit 0, 0.9052627 seconds. Exit 0 means the probe packet was collected; it does not mean the source passed the assertions.

## F002-01: Visible HTML boundary concatenation changes presence

`qualification/coverage_v1/diagnostics.py:Visible` drops block/line-break boundaries, and `visible_units` joins all data with an empty separator. Valid native text payload `RED<br>BLUE` and `<p>RED</p><p>BLUE</p>` both become `REDBLUE`. Exact target `REDBLUE` receives one eligible presence hit although it is not the visible text; target `RED BLUE` receives none although whitespace-normalized visible text contains it. This changes the new presence numerator and stage attribution. Correct inline concatenation, hidden attributes/comments/script/style exclusion, entity decoding and identifier-boundary probes pass.

Acceptance requirement: rendered block/line-break boundaries must not create synthetic concatenated values; use an explicitly bounded visible-text grammar or conservatively mark unsupported structures unavailable. Preserve legitimate inline behavior and unchanged historical mapper/scorer definitions. Independent generic evidence is in `visible` (three failed checks, four passing controls).

## F002-02: Failed returned post-observer rows are treated as successful

`qualification/coverage_v1/runtime.py:execute` wraps post `run_observers` in exception capture but never validates the returned rows. The real Q0 observer normally returns rows carrying nonzero/null return codes for command failure/timeout. Four independent mocked actual-supervisor executions return post rows with nonzero exit, timeout/null exit, wrong device, or no captures. Every execution returns 0, with no run failure and `final_observation_status.post_observers=available`. The full generated run result is preserved in each `supervisor` item. All worker calls are otherwise successful, isolating final-observation handling.

Acceptance requirement: post capture status must reflect failed/unavailable/truncated or wrong-device observation and preserve an unsuccessful finalization result. Preserve actual raw observer rows, completed-call accounting, primary failure, secondary errors and owned-job cleanup. Do not alter desktop/WDDM policy or infer OS hardware exclusivity. The author's raised-exception post-failure test does not cover the observer's normal error-return path.

## F002-03: Score-run accepts execution after a failed first call

`qualification/coverage_v1/scoring.py:score_run` checks the fixture/kind/excluded schedule but not its status progression. A public synthetic packet with the first excluded warmup `failed` followed by all other calls `completed` is accepted. It earns 12/12 field credit under both mappers and nine eligible paired comparisons. This impossible finite-run history bypasses first-failure/no-retry accounting; a bound release and raw hashes do not validate the run state machine. Evidence: `score_state`.

Acceptance requirement: reject structurally invalid statuses/progression and completed calls after the first noncompleted scheduled call before scoring them. Retain valid failed/not-run author denominators (12) and the reviewer sentinel denominator (1), with no invented failure rows for unselected fixtures. A genuine failure during post-finalization may still retain all completed calls; overall run failure alone must not erase their observations.

## Other checked boundaries and next action

All six independent public negatives for unit presence, unit value, null/empty unit, absence state and expected/annotation absence-label parity pass. Earlier checkpoint gaps are corrected in the current contract. Full author CPU suite and historical full score/diagnostic reproduction are still being completed separately; no acceptance is claimed from this packet. Root acknowledged the three blockers and will release author-owned correction under reserved /009. Canonical /002 remains unpublished for exact corrected candidate reconciliation. Corpus /004 is unaffected; no fresh input release or inference is granted.
