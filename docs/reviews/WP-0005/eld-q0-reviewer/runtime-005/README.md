# WP-0005 /005 Independent Runtime Verification & Reproduction Evidence (`eld-q0-reviewer`)

Safe in-Git evidence for the independent WP-0005 `/005` pre-execution verification, single unmodified-model Q0 GPU reproduction trial (`20261115T210422Z-565e2de9`), observed dual-PID worker exit & explicit GPU lease return (`WP-0005-reviewer-005-20261115T205527Z`), and independent audit of author `/004` (`9e73ef86600b5e16f74b056676a6d3a4f1474058`, `6e5f87fe4d0e19338a387bb5870efd083b2b491c`, `72fffbcbfa47f3c93425d9de5f338e511df7da3e`).

This directory sets `* -text` so every script, check output, and raw runtime artifact preserves exact bytes and SHA-256 digests. No wheels, model weights, binary `.pyc`/CUDA caches, credentials, cookies, or private transcripts are included. External reviewer artifacts remain untouched at `C:\Users\jackg\eLedgerCare-Q0\WP-0005\runs\reviewer\20261115T210422Z-565e2de9` (`101` files, `65,853,464` B).

| Field | Value |
| --- | --- |
| Reviewer / session | `eld-q0-reviewer` / Gemini 4 Carbon (High) (`gemini-4-carbon-high`, `high` effort), `0815536f-045a-4112-8a89-ebf0e0cc782f` |
| Owned branch / worktree | `review/wp-0005-q0-carbon` / `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-q0-reviewer-carbon` |
| Clean executing `HEAD` throughout verification & GPU trial | `c8daa97c5be6bc67931b215652a7a0f6ced621ef` (`harness_clean: true`, `dirty: []`) |
| Accepted harness core (`0` core edits) | `41d6204648e4115ab197507d1a22f6d5c7f3e784` |
| Bound coordinator releases | `reviewer-install.json` & `reviewer-execute.json` (`release_commit` `3a2906b1eb7f1873ae9129119d465ea0813d31f3`, dispatch `a3422609ff0afab5ca01c51be140e03a2066f6e9`) |
| Sole reviewer GPU lease | `WP-0005-reviewer-005-20261115T205527Z` (**RETURNED** at `2026-11-15T21:25:47.167155+00:00` after `child_pid=30436` & `heartbeat.pid=30484` verified absent) |
| Reviewer run ID & supervisor verdict | `20261115T210422Z-565e2de9` / `CHILD_COMPLETED` (`elapsed_s: 1266.187`, `child_returncode: 0`) |
| Domain qualification outcome | `QUALIFIED_RUNTIME_OBSERVATION` (`6/6` checks pass, `failures: []`, `accuracy_score: null`) |
| Cross-run reproduction vs author `20261115T202627Z-eb5bf7da` | **`6/6` calls (`11,040 / 11,040` generated tokens) match token-for-token and byte-for-byte** (`F01.warmup`, `F07.warmup`, `F01.warm1`, `F07.warm1`, `F01.warm2`, `F07.warm2`) |

## Index of Evidence Files

- [manifest.json](manifest.json): complete byte-size and SHA-256 manifest of this directory
- Pre-execution verification (`checks/01..06`, `pre-execute-summary.json`):
  - [checks/pre-execute-summary.json](checks/pre-execute-summary.json)
  - [checks/01-host-precheck-during.json](checks/01-host-precheck-during.json)
  - [checks/02-verify-wheelhouse.json](checks/02-verify-wheelhouse.json)
  - [checks/03-pip-check-and-venv-inventory.json](checks/03-pip-check-and-venv-inventory.json)
  - [checks/04-verify-model-before.json](checks/04-verify-model-before.json)
  - [checks/05-preflight-cpu.json](checks/05-preflight-cpu.json)
  - [checks/06-pre-gpu-process-and-vram.json](checks/06-pre-gpu-process-and-vram.json)
- Single GPU trial invocation (`checks/07*`):
  - [checks/07-execute-reviewer-receipt.json](checks/07-execute-reviewer-receipt.json)
  - [checks/07-execute-reviewer-stdout.json](checks/07-execute-reviewer-stdout.json)
  - [checks/07-execute-reviewer-stderr.txt](checks/07-execute-reviewer-stderr.txt)
- Post-execution lease return, reverification, run inventory, comparison & `/004` audit (`checks/08..14`):
  - [checks/08-post-run-worker-exit-and-lease-return.json](checks/08-post-run-worker-exit-and-lease-return.json)
  - [checks/09-post-run-host-precheck-during.json](checks/09-post-run-host-precheck-during.json)
  - [checks/10-verify-model-after.json](checks/10-verify-model-after.json)
  - [checks/11-module-cache-verification.json](checks/11-module-cache-verification.json)
  - [checks/12-reviewer-run-inventory.json](checks/12-reviewer-run-inventory.json)
  - [checks/13-author-vs-reviewer-comparison.json](checks/13-author-vs-reviewer-comparison.json)
  - [checks/14-author-004-publication-verification.json](checks/14-author-004-publication-verification.json)
- Byte-identical reviewer runtime copies (`72` files under `run-20261115T210422Z-565e2de9/`):
  - [run-20261115T210422Z-565e2de9/supervisor.json](run-20261115T210422Z-565e2de9/supervisor.json)
  - [run-20261115T210422Z-565e2de9/heartbeat.json](run-20261115T210422Z-565e2de9/heartbeat.json)
  - [run-20261115T210422Z-565e2de9/parent-context.json](run-20261115T210422Z-565e2de9/parent-context.json)
  - [run-20261115T210422Z-565e2de9/child.stdout.txt](run-20261115T210422Z-565e2de9/child.stdout.txt)
  - [run-20261115T210422Z-565e2de9/child.stderr.txt](run-20261115T210422Z-565e2de9/child.stderr.txt)
  - [run-20261115T210422Z-565e2de9/evidence/outcome.json](run-20261115T210422Z-565e2de9/evidence/outcome.json) and all `22` sibling `evidence/*` files plus `44` `observer-*.txt` snapshots
- Reviewer scratch wrappers (`wrappers/`): [run_pre_execute_checks.py](wrappers/run_pre_execute_checks.py), [launch_reviewer_execute.py](wrappers/launch_reviewer_execute.py), [run_post_execute_and_compare.py](wrappers/run_post_execute_and_compare.py), [package_005_evidence.py](wrappers/package_005_evidence.py)
