# WP-0027 / 005 · Ordinary reader coverage correction

| Report metadata | Value |
| --- | --- |
| Author and publisher | eld-reader-author, continuing native Codex session `/root/w27_reader`. Requested effort xhigh. Exact backend model and effective effort were not exposed. |
| Category and UTC timestamp | Research · 2026-11-22T06:35:29Z |
| Path | `docs/agent-reports/eld-reader-author/WP-0027/005_2026-11-22_research_eld-reader-author.md` |
| Repository, worktree and branch | Private `jackgumpe/eledgercare`, Windows worktree `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/w027-reader`, `research/wp-0027-terminal-reader` |
| Authority and base | Correction at `635425576401536d6fb231f085e8f483bf21c7be`. Owned base `20c4b5a6001eeded732dd70f381a4d4186346aa0`. [Correction assignment](https://github.com/jackgumpe/eledgercare/blob/635425576401536d6fb231f085e8f483bf21c7be/docs/coordination/WP-0027/reader-reconciliation.md) · [Index reservation /005](https://github.com/jackgumpe/eledgercare/blob/635425576401536d6fb231f085e8f483bf21c7be/INDEX.md#wp-0027-twin-binder-cpu-diagnosis) |
| Frozen corrected candidate | `8bf8ec2c9eb6eff282366d61711ec1a249f4760a` |
| Deliverable with execution evidence | `b0a4d3a90a825a9a3f27d334ded2e11759edfd20` |
| Previous report | [WP-0027 /002](https://github.com/jackgumpe/eledgercare/blob/20c4b5a6001eeded732dd70f381a4d4186346aa0/docs/agent-reports/eld-reader-author/WP-0027/002_2026-11-22_research_eld-reader-author.md) |
| Status and next owner | Ready for independent review, eld-rd-reviewer /003 |

## Finding and correction

The original candidate falsely accepted the reviewer’s ordinary three-marker record. The middle source raster contains an extra visible line outside all declared glyph rectangles. The trusted case binding and native output omit that line. The previous reader enforced complete pixel coverage only on the four-marker path. Author replay reproduced the original false acceptance on the exact reviewer inputs. The corrected candidate returns `unresolved / incomplete_source_pixel_coverage`. The native SHA-256 was `eae3356b3df4500c67cb83914395513eef6224518ab10b05f66717879accaa32`, the binding SHA-256 was `83a93a2a6d6b4b161ba85d0a57b91103bdaa222745b661153546b062e9467071`, and all three ordered PNG digests matched the reviewer’s published record. [Independent original discrepancy](https://github.com/jackgumpe/eledgercare/blob/309b9cd834a2f91728cbb88f974f589fedb0ff58/docs/reviews/WP-0027/reader-challenge-r1.json) · [Author replay before the change](https://github.com/jackgumpe/eledgercare/blob/b0a4d3a90a825a9a3f27d334ded2e11759edfd20/docs/research/WP-0027/reader/evidence-r2/reviewer-counterexample-before.json) · [Corrected replay](https://github.com/jackgumpe/eledgercare/blob/b0a4d3a90a825a9a3f27d334ded2e11759edfd20/docs/research/WP-0027/reader/evidence-r2/review-counterexample.json)

Both shapes now require every source line rectangle to contain ink and every nonwhite pixel to have an independently established source. Two archived H0 development pages contain structural ruling outside their glyph rectangles. Only the full authenticated binding of each specific control can invoke its ruling proof. The source PDF must render to the exact archived RGB pixels. The check removes every text object from an in-memory copy and verifies that each surviving PDF object is a single axis-aligned line segment. It masks the same glyph rectangles in the observed and path-only renders and compares every RGB pixel in the remaining pages. Unknown graphics or any differing pixel withhold acceptance. [Corrected policy](https://github.com/jackgumpe/eledgercare/blob/8bf8ec2c9eb6eff282366d61711ec1a249f4760a/docs/research/WP-0027/reader/POLICY.md) · [PDF ruling proof](https://github.com/jackgumpe/eledgercare/blob/8bf8ec2c9eb6eff282366d61711ec1a249f4760a/docs/research/WP-0027/reader/source_ruling.py)

| Control and physical page | Text objects removed | Axis-aligned paths | Residual ink pixels | Differing residual RGB pixels |
| --- | ---: | ---: | ---: | ---: |
| b01w01H page 1 | 13 | 8 | 30,470 | 0 |
| b01w02H page 4 | 7 | 7 | 24,690 | 0 |

The residual RGB SHA-256 was `9b79fea82d64dcc0070f6a07141ade4319a32befdacc8725d52461c535fa0f80` on page 1 and `cbfe540fa65764f3aa88cdfeb882ccaf8c16fdfec7b6df0658ec60d9459d4859` on page 4. The other four development pages had zero residual ink. All 22 archived spans and their 171 absolute-position selections matched. [First archived control](https://github.com/jackgumpe/eledgercare/blob/b0a4d3a90a825a9a3f27d334ded2e11759edfd20/docs/research/WP-0027/reader/evidence-r2/b01w01H.json) · [Second archived control](https://github.com/jackgumpe/eledgercare/blob/b0a4d3a90a825a9a3f27d334ded2e11759edfd20/docs/research/WP-0027/reader/evidence-r2/b01w02H.json)

## Verification and scope

The author suite matched **36/36 decisions and reasons**, with five accepted and 31 withheld. The original 32 cases reproduced every decision and reason. The four additional cases covered the exact independent counterexample, an ordinary synthetic omitted line, a foreign document claiming original H0 ruling, and new ink on an altered H0 raster carrying a copied ruling receipt. All four were withheld. k0014 retained six mapped spans, unused marker 121 at bytes [356,362) and EOS ID 1 at index 122. The raw native, coordinator source, and complete through-EOS bytes matched /002. [Machine-readable case table](https://github.com/jackgumpe/eledgercare/blob/b0a4d3a90a825a9a3f27d334ded2e11759edfd20/docs/research/WP-0027/reader/evidence-r2/parser-cases.json) · [k0014 witness](https://github.com/jackgumpe/eledgercare/blob/b0a4d3a90a825a9a3f27d334ded2e11759edfd20/docs/research/WP-0027/reader/evidence-r2/k0014.json)

The frozen-source replay used the owned Windows worktree and read-only Q0 Python 3.12.10 with `-I -B`, hidden CUDA, offline model-library settings and run-local caches. Package versions were Pillow 13.0.0, pypdfium2 5.15.2 and tokenizers 0.21.4. The run began at 06:34:26.673361 UTC and ended at 06:34:29.414953, measured 2.740 seconds and exited 0. The resulting case-table SHA-256 was `fa8cbeae8b05ea07b662ff5357f7a8e2b4dfe374b6cc2576be325e01300de151`.

```powershell
pwsh -File docs/research/WP-0027/reader/run.ps1 -Run C:/Users/jackg/eLedgerCare-Speed/WP-0027/reader/replay-02 -Candidate 8bf8ec2c9eb6eff282366d61711ec1a249f4760a
git diff --check 20c4b5a6001eeded732dd70f381a4d4186346aa0 b0a4d3a90a825a9a3f27d334ded2e11759edfd20
git diff --exit-code 20c4b5a6001eeded732dd70f381a4d4186346aa0 b0a4d3a90a825a9a3f27d334ded2e11759edfd20 -- docs/research/WP-0027/reader/evidence docs/agent-reports/eld-reader-author/WP-0027/002_2026-11-22_research_eld-reader-author.md
git ls-remote origin refs/heads/research/wp-0027-terminal-reader
```

Both diff checks exited 0. Remote branch verification returned the exact candidate and then the exact evidence revision after each owned push. Scratch outputs persist under `C:/Users/jackg/eLedgerCare-Speed/WP-0027/reader`. The source PDF was read as immutable bytes and edits existed only in memory. The historical reader’s rejection of k0014 and the blind stopping decision stand. This author replay made zero inference calls and opened zero hidden-feature archive members. Ruling on other documents and hidden-state recovery are outside this packet.

## Change inventory and handoff

All source and evidence paths below are relative to `docs/research/WP-0027/reader/`. The separately committed report is the metadata file named above. [Complete correction diff](https://github.com/jackgumpe/eledgercare/compare/20c4b5a6001eeded732dd70f381a4d4186346aa0...b0a4d3a90a825a9a3f27d334ded2e11759edfd20)

| Change | Files |
| --- | --- |
| Shared pixel-coverage rule, eligibility and complete correction replay | Modified `reader.py`, `POLICY.md`, `replay.py` |
| PDF-layer verification and independent fixture adapter | Added `source_ruling.py`, `review_regression.py` |
| Case table and paired counterexamples | Added `evidence-r2/parser-cases.json`, `evidence-r2/reviewer-counterexample-before.json`, `evidence-r2/review-counterexample.json` |
| Grounded correspondence and original identities | Added `evidence-r2/k0014.json`, `evidence-r2/k0014-native.json`, `evidence-r2/k0014-source.json`, `evidence-r2/k0014-ids-through-eos.u32le` |
| Archived controls and source-ruling evidence | Added `evidence-r2/b01w01H.json`, `evidence-r2/b01w02H.json` |

The reviewer independently replays candidate `8bf8ec2c9eb6eff282366d61711ec1a249f4760a` and records the original contradiction and corrected outcome under /003. The corrected policy still relies on independently supplied complete glyph transcripts for content inside each line rectangle. This is a bounded result on the disclosed record, two H0 controls and synthetic fixtures. Publication of /005 records author verification.
