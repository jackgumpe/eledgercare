# Final-verification commands (after freeze 9a9f24f0ab4592eaa6599c695a6a5c92866c4749)

Placeholders: `PF` is a fresh private `git archive` export of dd7982dc. Its 23 files were verified against the manifest before use. `R` is my worktree, `B` my verified private bundle copy, and `F` = `R/docs/reviews/WP-0046/final`. Every command ran with `python -I -B` and exited 0.

| # | Command | Output |
| --- | --- | --- |
| 1 | `PF/.../controls_r2.py --cases PF/.../control_cases.json --out F/results/r2-own-16.json` | 16/16 |
| 2 | `PF/.../controls_r2.py --cases R/.../exchange/challenges/peer-schema-cases.json --out F/results/r2-on-reviewer-27.json` | 27 returned |
| 3 | `PF/.../controls_r2.py --cases F/challenges/final-cases.json --out F/results/r2-on-final-4.json` | 4 returned |
| 4 | `PF/.../controls_r2.py --claude-r1-cases .../cases-r1.json --claude-expected .../expected-r1.json --out F/results/r2-claude-r1.json` | 3/3 |
| 5 | `PF/.../controls_r2.py --claude-cases R/.../challenges/cases.json --claude-expected R/.../expectations/expected.json --out F/results/r2-claude-49.json` | strict 49/49; amended 47/49 |
| 6 | `PF/.../build_register_r2.py --verify > F/results/r2-register-verify.txt` (run twice; once to the console) | verified |
| 7 | `R/.../exchange/tools/compare_peer.py R/.../exchange/expectations/peer-schema-expected.json F/results/r2-on-reviewer-27.json` (run twice; second run saved as compare-r2-27.txt) | required 27/27; Turn-1 predicted 23/27 |
| 8 | `compare_peer.py F/expectations/final-expected.json F/results/r2-on-final-4.json` (run twice; second run saved as compare-r2-final4.txt) | required 3/4; predicted 4/4 |
| 9 | `F/tools/recount_r2.py PF/.../register-r2.json B > F/results/recount-r2.json` | Pi_3 hard_unbound differs from the claim |
| 10 | `F/tools/d1_check.py R B > F/results/d1-check.json` | aligned_emission 0/5 under my frozen convention |
| 11 | post-hoc inline offset search and aligned recomputation → `F/results/d1-check-posthoc.json` | offset +1 aligns 5/5; 2,935 starts; Ban_1 empty |

Read-only `git show` was used at e43af2e2, aca4b43d and dd7982dc. I did not run any stock module, worker43, torch, model, device, network or host probe.
