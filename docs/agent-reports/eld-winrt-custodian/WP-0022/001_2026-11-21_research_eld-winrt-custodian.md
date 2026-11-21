# WP-0022 / 001 — Custody of eight synthetic interrupted ledgers

| Report metadata | Record |
| --- | --- |
| Report path | `docs/agent-reports/eld-winrt-custodian/WP-0022/001_2026-11-21_research_eld-winrt-custodian.md` |
| Reservation and category | WP-0022/001, research, [INDEX at reservation](https://github.com/jackgumpe/eledgercare/blob/10cbfb0fa8de2befb28a69c6fb10da90ca737219/INDEX.md#wp-0022-rendered-versus-winrt-ledger-ownership) |
| Author and publisher | eld-winrt-custodian, fresh native Codex session `/root/win22_custody`. GPT-6 family. Coordinator requested xhigh. Specific backend variant and applied effort were unexposed in this session. |
| Execution environment | Windows, PowerShell, Git, pinned Python 3.12.10 environment |
| UTC timestamp | 2026-11-21T06:51:27Z |
| Repository, branch and worktree | Private `jackgumpe/eledgercare`, `research/wp-0022-custody`, `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/scope22-custody` |
| Assignment base | `10cbfb0fa8de2befb28a69c6fb10da90ca737219` |
| Public commitment | `e207ee56ce1716abf6568ecdb254c6f8e0a89f74` |
| Unsealed deliverable | `e6ea32afbfa4aaf4e693cdea8af1c1121c0cadd1` |
| Previous report | First custody report in WP-0022 |
| Status and next owner | Ready for independent review by eld-winrt-reviewer /003 |

## Summary

Eight synthetic forms contribute 42 rows across 16 page appearances, with 21 rows each for child and parent ledgers. The 26 post-break rows include 20 populated cells, four empty cells and two genuinely ambiguous continuations. Two forms have identical public observations across both pages and opposite hidden continuation owners. Before either arm ran, the custodian committed the 14 distinct PNGs, 16 page bindings, eight rendered documents and SHA-256 commitments to the withheld key and generator. The unsealed truth and generator match those earlier commitments byte for byte.

## Objective and criteria

Supply independently constructed inputs for the paired Windows study. Every population, empty cell and ambiguous row needs a unique spatial target with section and banner provenance. Fresh inputs must include differently sized right-aligned amounts, two- and three-line descriptions, interrupted parent and sibling ledgers, and matched numeric notes adjacent to both populated and empty cells. The custodian owns specimen generation and verification. Root controls release after both arm freezes; the reviewer adjudicates source, scoring, observations and execution independently.

## Change inventory

| Stage | Exact paths under `docs/fixtures/WP-0022/` | Contents |
| --- | --- | --- |
| Public commitment | `public/manifest.json`, `commitments.json`, `precounts.json` | Logical page-to-raster bindings, source and key hashes, rendering dependencies and design totals |
| Public commitment | `public/rasters/N01-p1.png` through `N08-p2.png`, two pages per ID | Sixteen RGB PNGs of 2550 × 3300 pixels each |
| Public commitment | `public/rendered/N01.json` through `N08.json` | Ordered page lines, literal tokens, source IDs and point rectangles |
| Unsealed deliverable | `generate.py`, `truth.json`, `verify_custody.py`, `README.md` | Original sealed generator and key, executable receipt checks, fixture interpretation and reproduction commands |
| Report metadata | This canonical /001 path, added after the deliverable | Author verification and handoff |

External effects consist of owned private-remote branch pushes, reads of the pinned Python environment and two Windows Arial fonts, and the retained local `wp0022-data/custody` directory holding render drafts, final original, byte-identical regeneration and a visual contact sheet. No other worktree, database or service was changed.

## Decisions and rationale

The design fixes setup versus post-break membership, scope, literal, full row/amount/note regions and printed sources before either arm executes. Compact left-aligned controls accompany wide right-aligned stress rows. The two ambiguous forms preserve identical entire public page sequences. Distinct printed source regions identify similarly labelled sibling sections. Four matched note pairs use the same numeral opposite a populated row and a truly empty amount. In two pairs the note equals the populated amount exactly. A string match by itself cannot establish spatial ownership. [Fixture design and replay instructions](../../../fixtures/WP-0022/README.md)

All 13 hidden resumed-parent rows have the `return` tag. One is the parent half of the ambiguous twins, which has no visible return cue. For the damaged-header condition the intended Amount source refers to its previous valid header. The visible damaged line remains in both the render and the raster. The body row rectangle covers every wrapped line and note at its height. Empty amount targets contain zero renderer words in their amount rectangles.

## Verification

| Executed check | Result |
| --- | --- |
| `git status -sb`, `git rev-parse HEAD`, `git remote -v` in owned worktree | Clean assigned branch at reservation and expected private repository remote |
| `python -B generate.py sealed` and `python -B generate.py replay` in owned scratch | Independently wrote all 28 final files twice. Prespecified geometry, signed/parenthesized literals, wraps, notes, sibling names and ambiguous twins are explicit in the source. |
| `python -B verify_custody.py sealed generate.py replay` | Passed all 28 byte comparisons, 354 renderer-word edge checks, 42 target cell/provenance checks, four matched note pairs, two sibling pairs and both opposite ambiguous scopes |
| Visual contact sheet of N01 pages 1–2, N03 page 2 and N05 page 2 | Inspected actual pixels of compact control, right-aligned wraps, note pairs and rapid child-to-parent returns |
| `git ls-remote origin refs/heads/research/wp-0022-custody` after public push | Exactly `e207ee56ce1716abf6568ecdb254c6f8e0a89f74` before authorization to unseal |
| Root release | Root authorized unsealing after verifying 147 blind archive hashes at dc033d1491e930eba933f6afd694a5ecde1ea8f7 and publishing receipt 1da1c80bebdcd6ca7a8285c5b3601bd8c0675b1b. The author released the previously committed files after this instruction. |
| Verification from the pinned unsealed deliverable | Ran the documented generate and verify commands from e6ea32afbfa4aaf4e693cdea8af1c1121c0cadd1 with owned output wp0022-data/custody/after-release. All 28 files matched; the remote ref matched that exact deliverable. Git diff --check reports one trailing blank line in the sealed generator. Its unchanged SHA-256 preserves the original source. |

The pre-run key SHA-256 is `ef32bc6bff114900deda32d6f161dce4bf311930f7802dc23c9a6dd36d8e40df`; the generator SHA-256 is `c84c75addfc8d2d3b8901dcc7ab142118afa7abe39d95ee72d3d45eb5d64b3ea`. The manifest SHA-256 is `bb527e498409db4b813f1ca4534bcfcc7967eeb5a48f8acbf99abd2bfab961c3`. [Pre-run commitments](https://github.com/jackgumpe/eledgercare/blob/e207ee56ce1716abf6568ecdb254c6f8e0a89f74/docs/fixtures/WP-0022/commitments.json)

## Review map, limits and handoff

Review the actual public commit, the independently regenerated key, glyph projection in `Page.line` and target construction in `Form.table`. Check the ambiguous twins as whole documents, the physically distinct header positions for repeated sibling names, and both sides of each numeric-note pair. Replay exact hashes using the documented interpreter and the named, digest-checked fonts. The paired arm executions and outcome reports belong to their assigned owners. Custody used no saved reader, detector, OCR or GPU. The 42 observations span seven distinct visible two-page forms and count the two ambiguous logical instances separately. The design supports a bounded comparison on these synthetic inputs.

The unsealed deliverable and public commitment were pushed to the owned branch. The exact /001 publication SHA and remote confirmation are provided separately to the coordinator. Independent /003 review and root /004 disposition follow under the packet reservation.
