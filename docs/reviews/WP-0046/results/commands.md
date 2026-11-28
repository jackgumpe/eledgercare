# Executed commands and outcomes (eld-rd-reviewer, WP-0046 Stage 0)

Environment: Windows x64, CPython 3.12.10, Git Bash shell. `BUNDLE` is a fresh private copy of the supplied extracted bundle. Before and after every run, its 27 files matched `docs/coordination/WP-0046/source-pins.json`. No `__pycache__` was created there or here. `REVIEW` is `docs/reviews/WP-0046` in the owned worktree. Absolute private paths are omitted.

The expectation freeze was committed first at `cffc9101e769bc6f7ab11fdb4137401f8f228490`. Every execution below came after it.

| # | Command | Outcome |
| --- | --- | --- |
| 1 | verify the 4 outer artifacts, 27 bundle members and the zip listing against source-pins.json (stdlib hashlib/zipfile) | 4/4 and 27/27 equal. The zip members equal the extracted bundle. |
| 2 | copy bundle to a new empty private directory, re-verify | 27/27 |
| 3 | `python -I BUNDLE/check.py > stdout 2> stderr`, cwd outside the bundle | exit 0. stdout has 6 lines, 622 bytes, SHA-256 e6976a43d7a5363cd9a0e3448bdb25f78cb4ba65578782f04fd330f0a52b4520. stderr has 0 bytes. expected.txt has 616 bytes, SHA-256 35adef646987b6a6a9a68680732e5809176e3855c62fb6330337bce70d7296cf. The bytes are unequal because Windows text-mode stdout wrote 6 CRLF. After LF normalization they are equal. The frozen prediction "byte-equal" was therefore wrong at byte level and right in content. |
| 4 | `python -I REVIEW/tools/evaluate.py REVIEW/challenges/cases.json REVIEW/results/evaluate.json` | 49 cases evaluated |
| 5 | `python -I REVIEW/tools/compare.py REVIEW/expectations/expected.json REVIEW/results/evaluate.json` (run twice, the second time saved to compare.txt) | full-record agreement 49/49, 0 unexpected ids |
| 6 | `python -I REVIEW/tools/audit_register.py BUNDLE > results/audit_register.json` | exit 0. Every frozen prediction in tool-predictions.json held. |
| 7 | `python -I REVIEW/tools/archive_checks.py BUNDLE` (first attempt) | failed with KeyError 'generation_config'. The tool used the wrong JSON path: the key sits under `configuration`. |
| 8 | the same command after a one-line path correction | exit 0. Every frozen prediction held. The correction appears in the results commit, and the freeze commit keeps the original. |

The ad hoc read-only `python -I -c` inspections of the pinned JSON/text sources are not counted as checks. No other code ran: no model, torch or stock import, no stock worker or rehearsal, no device, network, process or file attack, no private replay and no harness change. worker43.py was parsed with `ast` and never executed. amendments.py was executed only inside check.py via its own runpy call.
