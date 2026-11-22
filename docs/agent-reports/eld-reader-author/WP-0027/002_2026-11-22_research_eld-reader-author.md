# WP-0027 / 002 · Three-page terminal delimiter replay

| Report metadata | Value |
| --- | --- |
| Author and publisher | eld-reader-author, native Codex session `/root/w27_reader`. Requested effort xhigh. The exact serving model and effective effort were not exposed to the author. |
| Category and UTC timestamp | Research · 2026-11-22T06:28:00Z |
| Report path | `docs/agent-reports/eld-reader-author/WP-0027/002_2026-11-22_research_eld-reader-author.md` |
| Repository and branch | Private `jackgumpe/eledgercare`, `research/wp-0027-terminal-reader`, worktree `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/w027-reader` |
| Reservation and base | `ce04b773329c3c67cd0ab4b578ddf442690019a0`. [WP-0027 reservation](https://github.com/jackgumpe/eledgercare/blob/ce04b773329c3c67cd0ab4b578ddf442690019a0/INDEX.md#wp-0027-twin-binder-cpu-diagnosis) |
| Frozen source and acceptance policy | `67e0898e09ee9fc848677990850f9320a7d3cd6f` |
| Deliverable including evidence | `10f64a7e26e2e2477435a05543efbf647cefdff8` |
| Previous / related report | First author report for this assignment. Prior stopping evidence is WP-0026 /003. [Independent WP-0026 report](https://github.com/jackgumpe/eledgercare/blob/e9e24e5ea2730358fb67cfe269049a66a92ce8a5/docs/agent-reports/eld-rd-reviewer/WP-0026/003_2026-11-21_review_eld-rd-reviewer.md) |
| Status and next owner | Ready for review, eld-rd-reviewer /003 |

## Outcome

The original reader rejected k0014 with `Expected three grounded native pages`. The prospective reader mapped all six printed lines from physical pages 16–18 to their six corresponding native spans. Each glyph-line center lay inside its matching box, and each of the three raster pages had zero nonwhite pixels outside its source line rectangles. Token 121 is an unassigned terminal delimiter at original bytes [356, 362). Its payload is empty. Observed EOS ID 1 follows at token 122 and byte offset 362. The complete stream contains 123 IDs through EOS. [Exact mapping and original rejection](https://github.com/jackgumpe/eledgercare/blob/10f64a7e26e2e2477435a05543efbf647cefdff8/docs/research/WP-0027/reader/evidence/k0014.json)

The CPU replay matched all **32 expected decisions and reasons**. Five cases were accepted, including k0014, two archived ordinary controls and two independently printed synthetic controls. All 27 negative or unresolved controls were withheld. In particular, the reader detected reordered/duplicated pages, redistributed/missing/extra lines despite the expected section count, unmatched geometry and a line omitted from both the candidate text and source witness but visible in the pixels. It explicitly withheld a verified white middle page in its original position. [Machine-readable case table](https://github.com/jackgumpe/eledgercare/blob/10f64a7e26e2e2477435a05543efbf647cefdff8/docs/research/WP-0027/reader/evidence/parser-cases.json)

| Physical page | Native section token interval | Printed lines matched |
| --- | --- | --- |
| 16 | [0, 42) | Field record · Field work on record. |
| 17 | [42, 81) | Stock check · Records checked on receipt. |
| 18 | [81, 121) | Inspection log · Continuation attached. |

## Objective and acceptance

Reproduce the historical stopping decision, retain every emitted ID and byte, and examine one prospective exception under independent source binding. The coordinator’s separately committed constructor reconstructed the call identity, selected only physical pages 16–18, checked the released and archived plan, process begin event and native stream, and compared each archived raster with the pixels rendered from the corresponding PDF page. The frozen reader pins this evidence and checks all three PNGs again. [Independent source constructor](https://github.com/jackgumpe/eledgercare/blob/f13a148225efeecb7faf287179a3e010f3c385ac/docs/coordination/WP-0027/source_witness.py)

The policy admits a single immediately terminal empty marker only with three populated, fully grounded and independently distinguishable sections. The fourth marker remains in the raw record. It can never select a grounded span position. The conventional three-page projection, span ranges and feature positions on both saved ordinary controls had to remain equal to the accepted archive. [Frozen acceptance policy and case API](https://github.com/jackgumpe/eledgercare/blob/67e0898e09ee9fc848677990850f9320a7d3cd6f/docs/research/WP-0027/reader/POLICY.md)

## Change inventory

Paths in the table are relative to `docs/research/WP-0027/reader/`. All are additions to the reserved base. The report is the separate metadata file identified above. [Base-to-deliverable diff](https://github.com/jackgumpe/eledgercare/compare/ce04b773329c3c67cd0ab4b578ddf442690019a0...10f64a7e26e2e2477435a05543efbf647cefdff8)

| Path | Purpose |
| --- | --- |
| `POLICY.md` | Frozen acceptance criteria, external trust boundary, replay and independent case API |
| `reader.py` | Immutable stream and token ledger, source binding, complete source-to-section comparison, per-span offsets and unused delimiter |
| `fixtures.py` | Fixed H0 archive/PDF controls and independently printed synthetic raster fixtures |
| `replay.py` | Original rejection, bounded case matrix, historical whole-projection/position comparison and evidence writes |
| `run.ps1` | Isolated CPU-only Q0 entry point and owned cache directories |
| `evidence/parser-cases.json` | Machine-readable expected and actual outcomes, timings, runtime, identities and result digests |
| `evidence/k0014-native.json` | Unmodified 7,171-byte native record |
| `evidence/k0014-source.json` | Independently produced source manifest with ordered raster, PDF, plan, native and begin-record identities |
| `evidence/k0014-ids-through-eos.u32le` | 492 bytes, all 123 original IDs including the observed EOS as little-endian uint32 |
| `evidence/k0014.json` | Full raw offsets, original exception, mapped lines and boxes, marker and EOS disposition |
| `evidence/b01w01H.json`, `evidence/b01w02H.json` | Source lines, accepted historical projection identities, per-span emitted and absolute feature position selections |

## Verification

The decisive command ran from the owned worktree on Windows under Python 3.12.10, Pillow 13.0.0, pypdfium2 5.15.2 and tokenizers 0.21.4. Q0 ran with `-I -B`, hidden CUDA, offline model-library flags and packet-owned cache paths. The recorded CPU run began at 06:27:00.522962 UTC and ended at 06:27:02.020443. The measured replay took 1.497 seconds. Exit code was 0.

```powershell
pwsh -File docs/research/WP-0027/reader/run.ps1 -Run C:/Users/jackg/eLedgerCare-Speed/WP-0027/reader/replay-01 -Candidate 67e0898e09ee9fc848677990850f9320a7d3cd6f
```

| Check | Observed result |
| --- | --- |
| Original parser at `4a867f91d47c12e49e78c2381d5bc4661c6927fa` and local tokenizer | SHA-256 `29817b77589e88ef6b741dc1c36e9da3d07bcf641887109f3a77d4b7a39aeece` and `c55c165e32c5a67830362a53e1f548c8930dcc8469efa30ff3252a982799c589`, respectively |
| Historical record and verified source | Native SHA-256 `ce9d03a8d73ecf4366b96bc2dbbf9e129f5a2ca30265876a16b17c07cc20b169`. Source manifest SHA-256 `10aea96000abf9bd571f95cee7bf2270d1854b1c3c6341ff8548d2bc9593be32` |
| UTF-8 emission and complete IDs | Raw UTF-8 SHA-256 `6d30b721626204a3628246c2a7aff0a0d2325a39707b75f1263570c5ee7d4cec`. Through-EOS SHA-256 `aa252199f6a1b963d5d9b11a32cba39c784dff494fea3db85d702215dc705f26` |
| Grounded page/row/span projections and consumed positions | b01w01H, 14 spans and 102 position selections. b01w02H, 8 spans and 69 position selections. All six development pages, both complete projections and all selections matched the archive exactly. |
| Case table SHA-256 | `2c768486fa89691f525aa2921972cc8a8c5b854432b4a878a274fc5885f1607e` |
| `git diff --check ce04b773329c3c67cd0ab4b578ddf442690019a0 HEAD` | Exit 0 at the evidence revision |
| `git ls-remote origin refs/heads/research/wp-0027-terminal-reader` | Verified candidate `67e0898e09ee9fc848677990850f9320a7d3cd6f`, then the evidence publication `10f64a7e26e2e2477435a05543efbf647cefdff8` after normal pushes |

The seven replay outputs were compared by SHA-256 when copied from the owned scratch directory. The branch, its Git commits and `C:/Users/jackg/eLedgerCare-Speed/WP-0027/reader` are the persistent author-side effects. Each witness records its input digests and exact absolute selections where applicable. [First saved control](https://github.com/jackgumpe/eledgercare/blob/10f64a7e26e2e2477435a05543efbf647cefdff8/docs/research/WP-0027/reader/evidence/b01w01H.json) · [Second saved control](https://github.com/jackgumpe/eledgercare/blob/10f64a7e26e2e2477435a05543efbf647cefdff8/docs/research/WP-0027/reader/evidence/b01w02H.json)

## Limits and handoff

The results establish correspondence for this exact k0014 call and controls. Wider layout support would require additional evidence. The exceptional path checks every nonwhite source pixel against the complete independently printed line rectangles, using a one-unit allowance for box rounding. Pictures and ruled tables can therefore be withheld. The complete glyph transcript remains the authority for differences inside any one line’s rectangle.

The historical k0014 call stopped before a feature return. No model ran and no hidden feature bytes, held-out answer key, new predictions or other blind examples were accessed by this reader replay. Blind C1 retains its stopped status. Author verification is complete. The next owner, eld-rd-reviewer /003, independently exercises the exact source and malformed controls, verifies source provenance and offsets, and publishes a disposition. The coordinator receives the report publication SHA after the owned branch push.
