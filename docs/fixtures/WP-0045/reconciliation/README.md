# WP-0045 A2 reconciliation (post-opening, version r1)

Owner: eld-fixture-claude, the same role and source author as the sealed oracle. The coordinator reserved this work as supplemental report /006.

Everything here was written **after** the coordinator-authorized opening. It was also written after the coordinator reported that both frozen candidates and the sealed oracle return `M` and `first` = `["repeat",1]` for `A2.illegal_repeat`, and that they differ on the pair `["page",2]`. I did not read either candidate's implementation or outputs. Nothing here is blind, and none of it changes a scheduled denominator or the original blind counts.

The opened oracle, its expected rows and its manifest under `../opened/` stay byte-for-byte unchanged. So do the inputs, the fixture manifest and the commitment.

| File | Role |
| --- | --- |
| `oracle_r1.py` | Versioned correction `wp0045.expected.r1`. It verifies and loads the opened oracle read-only and replaces only the A2 phase comparison: each phase is compared with its immediate supplied predecessor under its **own** block list, and the cumulative exclusion is used for support (`allowed`) only. It recomputes all 32 unchanged inputs, confirms that v1 still reproduces, and lists every row that differs from v1. |
| `regression.json` | Six small A2 cases with hand-written r1 expectations, v1 conflicts and a "readings differ" flag, all frozen before execution. Three cases distinguish the readings and three are controls. |
| `regression.py` | Runs r1 and the unchanged v1 evaluator on the regression cases and checks every frozen expectation. |
| `results/` | (Separate later commit.) Outputs from the first execution of the files above. |

These files were committed before their first execution. The commands are:

```
python -I -B oracle_r1.py --repo <worktree>
python -I -B regression.py
```
