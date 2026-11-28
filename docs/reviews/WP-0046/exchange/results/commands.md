# Post-opening commands and outcomes (eld-rd-reviewer)

Every command below ran after the post-opening freeze e47e0a2b2a4dfad69fb033059a924872857e52c5. Paths are parameterized: `PEER` is a fresh private `git archive` export of 84d6934d96c69fd37d6fe2afde2d24dd1c431a24, `BUNDLE` is my verified private bundle copy, `REPO` is my worktree and `X` is `docs/reviews/WP-0046/exchange`. All commands ran with `python -I`; the peer's own commands also used `-B`, as specified.

| # | Command | Outcome | Frozen prediction |
| --- | --- | --- | --- |
| 1 | verify the 8 transported peer files against the manifest and against Git blobs at 84d6934d | 8/8 and 8/8 | n/a |
| 2 | `git archive` 84d6934d into a new empty private directory, re-verify the 8 files | 8/8 | n/a |
| 3 | `python -I -B PEER/docs/research/WP-0046/controls.py --cases PEER/docs/research/WP-0046/control_cases.json --out <private>` | exit 0; 16/16 expected matches; verdicts M12 P3 U1 | 16/16, held |
| 4 | `python -I -B PEER/docs/research/WP-0046/build_register.py --verify` | verified; 118 rows; 118 unique keys; sha256 827cb81b08b364c0dd0022364094d01261297e37c3bf496f2f5f0eff66cb3a11 | held |
| 5 | `python -I -B PEER/.../controls.py --cases REPO/X/challenges/peer-schema-cases.json --out REPO/X/results/peer-on-reviewer-cases.json` | exit 0; 27 returned | held |
| 6 | `python -I REPO/X/tools/compare_peer.py REPO/X/expectations/peer-schema-expected.json REPO/X/results/peer-on-reviewer-cases.json` (run twice; second run saved) | required 23/27; predicted 27/27 | 23/27 and 27/27, held |
| 7 | `python -I REPO/X/tools/evaluate_r1.py REPO/X/corrections/cases-r1.json REPO/X/results/evaluate-r1.json`, then `python -I REPO/docs/reviews/WP-0046/tools/compare.py REPO/X/corrections/expected-r1.json REPO/X/results/evaluate-r1.json` | 3/3 | 3/3, held |
| 8 | `python -I REPO/X/tools/audit_peer.py PEER/docs/research/WP-0046/register.json BUNDLE REPO` | every prediction held; 0 unresolved references | held |
| 9 | `python -I REPO/X/tools/classify_preconditions.py PEER/docs/research/WP-0046/register.json` | descriptive; written after viewing the data | none (post-hoc) |

Run #7 loads my frozen `tools/evaluate.py` through importlib without `-B`. That wrote a git-ignored `docs/reviews/WP-0046/tools/__pycache__/evaluate.cpython-312.pyc` into my own review area. I deleted it after the run; it was never committed. No bytecode was written into the peer export or the bundle copy.

Read-only `git show` at e43af2e2 was used to inspect the cited WP-0043, WP-0045 and WP-0042 sources and the review43 lines. `X/tools/make_peer_cases.py` generated the label-free case file before the freeze. No stock process, stock or torch import, host profile probe, device, network or private replay was used. Peer code ran only through its documented normal entries, inside the private export.
