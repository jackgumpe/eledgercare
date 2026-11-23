# WP-0031 / 001 — Declaration swaps at write 8

Both frozen probes shifted toward Cedar when the incoming prefix was fixed and the declaration changed from Cedar to Alder. Clearing all incoming matrices reversed this contrast for M1. It persisted for M3. The four native controls reproduced exactly. These are retrospective reads of one matched development opening.

| Assignment | Binding |
| --- | --- |
| Report / sequence | `docs/agent-reports/eld-owner-probe/WP-0031/001_2026-11-23_research_eld-owner-probe.md` · [WP-0031 / 001 reservation](https://github.com/jackgumpe/eledgercare/blob/74f23b10d428acc3477db6ce4af7eb663e28d9f4/INDEX.md#wp-0031-bounded-cpu-replay-at-the-write-8-owner-declaration) |
| Category / status | Research · ready for independent review |
| Author and publisher | eld-owner-probe · fresh native Codex task `/root/write8_author` · thread `01a20a79-b5d1-7cc0-9d1a-474e208698ec` |
| Actual configuration disclosure | The dispatcher supplied `gpt-6.2-astra` at `xhigh`. The session identifies itself as GPT-6. Its environment exposed the thread ID and did not separately expose the detailed model or effort. |
| Environment / timestamp | Windows 11, native Codex and PowerShell · 2026-11-23T22:20:50Z |
| Repository / branch / worktree | `jackgumpe/eledgercare` · `research/wp-0031-write8` · `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/w031-author` |
| Base / frozen source | `74f23b10d428acc3477db6ce4af7eb663e28d9f4` / `5e1a464a38ad4213b94b3b25695bd70d9054a6a3` |
| Evidence deliverable | `8f31cc66c4878ca086fa5da1498c4a73ed6a6306` |
| Previous / related records | First author report in this packet. [WP-0030 independent reproduction](https://github.com/jackgumpe/eledgercare/blob/e792840e6358ae2fe9a31dac1360383c0514f65c/docs/agent-reports/eld-rd-reviewer/WP-0030/002_2026-11-22_review_eld-rd-reviewer.md) · [WP-0030 precision correction](https://github.com/jackgumpe/eledgercare/blob/c76c313f06393b3172a06cdc4098130f3b8d5f2d/docs/agent-reports/eld-coordinator/WP-0030/004_2026-11-22_verification_eld-coordinator.md) |
| Next owner | eld-rd-reviewer, WP-0031 / 002, via eld-coordinator |

## Objective and acceptance criteria

Measure the declaration contrast at each original incoming state and the prefix contrast at each fixed declaration for M1 and M3. Each replay ends at the owner declaration on page 1, window 1, span index 7. Admission requires both native write-7 reads, both native write-8 controls, the frozen eventual query, the ordered owner anchors and distinct, immutable recipient states. The second binder length supplies an archived digest comparison for the shared opening. The signed margin is the score for literal Alder minus the score for literal Cedar. [Assignment](https://github.com/jackgumpe/eledgercare/blob/74f23b10d428acc3477db6ce4af7eb663e28d9f4/docs/coordination/WP-0031/assignment.md)

## Results

Within each cell the scores appear in literal order Alder, Cedar. The increment is the write-8 margin minus the write-7 margin in that row. AA and CC replay actual prefixes and declarations. AC and CA are interventions. Both owners were eligible, the controller depth was zero and the scope was clear for all post-write reads. All twelve reads fell below both original score and gap thresholds. Winner means the larger retrospective raw score. [M1 evidence](https://github.com/jackgumpe/eledgercare/blob/8f31cc66c4878ca086fa5da1498c4a73ed6a6306/docs/research/WP-0031/evidence/M1.json) · [M3 evidence](https://github.com/jackgumpe/eledgercare/blob/8f31cc66c4878ca086fa5da1498c4a73ed6a6306/docs/research/WP-0031/evidence/M3.json)

### M1

| Prefix and write-7 margin | Alder declaration | Cedar declaration |
| --- | --- | --- |
| Alder<br>+0.025722913444042206 | **AA** (Cedar first)<br>Scores -0.045244865119457245, 0.014514945447444916<br>Margin -0.05975981056690216<br>Increment -0.08548272401094437 | **AC** (Cedar first)<br>Scores 0.020283853635191917, 0.06048865616321564<br>Margin -0.04020480252802372<br>Increment -0.06592771597206593 |
| Cedar<br>+0.028679117560386658 | **CA** (Cedar first)<br>Scores -0.03879733383655548, 0.01913132146000862<br>Margin -0.0579286552965641<br>Increment -0.08660777285695076 | **CC** (Cedar first)<br>Scores 0.030345000326633453, 0.06809929758310318<br>Margin -0.03775429725646973<br>Increment -0.06643341481685638 |

### M3

| Prefix and write-7 margin | Alder declaration | Cedar declaration |
| --- | --- | --- |
| Alder<br>+0.0011497139930725098 | **AA** (Cedar first)<br>Scores 0.14160983264446259, 0.14292049407958984<br>Margin -0.0013106614351272583<br>Increment -0.002460375428199768 | **AC** (Alder first)<br>Scores 0.12284263968467712, 0.10693581402301788<br>Margin +0.01590682566165924<br>Increment +0.014757111668586731 |
| Cedar<br>+0.0020220577716827393 | **CA** (Cedar first)<br>Scores 0.142293781042099, 0.1432039588689804<br>Margin -0.0009101778268814087<br>Increment -0.002932235598564148 | **CC** (Alder first)<br>Scores 0.12342783063650131, 0.10698604583740234<br>Margin +0.01644178479909897<br>Increment +0.01441972702741623 |

### Declaration, prefix and interaction contrasts

The two declaration contrasts compare Alder with Cedar at a fixed row. The two prefix contrasts compare Alder with Cedar at a fixed column. The interaction equals both DA − DC and PA − PC. The native contrast equals AA − CC, DA + PC and PA + DC. All equalities held exactly after promoting each retained little-endian binary32 score to binary64.

| Probe | DA (AA − AC) | DC (CA − CC) | PA (AA − CA) | PC (AC − CC) | I | Native contrast |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| M1 | -0.01955500803887844 | -0.020174358040094376 | -0.0018311552703380585 | -0.0024505052715539932 | +0.0006193500012159348 | -0.022005513310432434 |
| M3 | -0.0172174870967865 | -0.017351962625980377 | -0.0004004836082458496 | -0.0005349591374397278 | +0.00013447552919387817 | -0.017752446234226227 |

Both donor contrasts were negative for both probes. The table gives each absolute interaction, its pre-specified inclusive limit of 0.05 × max(|DA|, |DC|), and the resulting donor contrast D0 on empty incoming matrices. Both probes qualified for the two additional reads. Every matrix lane was cleared. The discrete state used in these controls was identical across the original write-7 prefixes.

| Probe | Absolute interaction | 5% limit | D0 (0A − 0C) |
| --- | ---: | ---: | ---: |
| M1 | 0.0006193500012159348 | 0.0010087179020047189 | +0.052650585770606995 |
| M3 | 0.00013447552919387817 | 0.0008675981312990189 | -0.033937111496925354 |

| Empty cell | Alder score | Cedar score | Margin | First | Score bytes in ordered FP32 LE |
| --- | ---: | ---: | ---: | --- | --- |
| M1 0A | 0.24972456693649292 | 0.17397233843803406 | +0.07575222849845886 | Alder | `ccb77f3ece25323e` |
| M1 0C | 0.1952122151851654 | 0.17211057245731354 | +0.023101642727851868 | Alder | `b6e5473ec13d303e` |
| M3 0A | 0.09794218838214874 | 0.14458493888378143 | -0.04664275050163269 | Cedar | `ea95c83d130e143e` |
| M3 0C | 0.0666845366358757 | 0.07939017564058304 | -0.012705639004707336 | Cedar | `e791883d5197a23d` |

M1 ranked Cedar first in every populated cell. The same donor change shifted the margin toward Alder with empty matrices. For this opening, inspect how the incoming matrix combines with the declaration under the frozen write and normalized read. M3 switched winners with the declaration at either populated prefix. With empty matrices both donors ranked Cedar first, and the Alder donor moved the margin farther toward Cedar. This supports inspecting the complete declaration projection and its readout for M3. Neither empty-matrix result isolates the residual term. The prefix contrasts are smaller and nonzero. Even exact equality of the two donor contrasts would permit an additive prefix effect.

## Phase, identity and freeze decisions

- The replay authenticated the two original 16 × 1280 feature windows and used each full window in its own `Memory.project` call. Seven native writes per prefix preceded each snapshot. The pooled-row digest differed between twins on every one of those seven writes. Both owner names appeared in the registry at write 3. Each write-7 snapshot stores every FP32 matrix byte, controller fields, full registry sets including original schema tuples, and the replay state's ancillary fields. [Input bindings](https://github.com/jackgumpe/eledgercare/blob/8f31cc66c4878ca086fa5da1498c4a73ed6a6306/docs/research/WP-0031/evidence/inputs.json)
- The donor at (1, 1, 7) carried its own `OPEN_LEDGER` event, literal, box, feature and projected key, value, alpha and beta. The boxes were [53, 486, 339, 515] for Alder and [53, 487, 339, 515] for Cedar. Before each cell, the replay deep-copied the recipient and checked that each matrix had distinct storage from its source. It applied the donor event to controller and registry, checked the discrete and matrix digests, invoked the frozen write, then immediately read. Both stored source-state digests matched before and after every cell. Each donor's input digest is recorded separately. [Cell source](https://github.com/jackgumpe/eledgercare/blob/5e1a464a38ad4213b94b3b25695bd70d9054a6a3/docs/research/WP-0031/experiment.py)
- The packet PDF's page 4 display omits the decay on the old matrix. The pinned native operation computes `residual = v - a * (old @ k)` and `updated = a * old + b * torch.outer(residual, k)`. Every cell calls that exact operation with the recipient's matrices. The supplementary residual digest is observational. Clearing the old matrix sets the residual to the donor value. [Frozen Memory.write](https://github.com/jackgumpe/eledgercare/blob/7db67283a4ffd3e7a20bb8d80499572cc7118c71/docs/research/WP-0024/probe/matrix.py#L80-L97)
- Each twin restored its original eventual query from the archived lossless bytes and generated its ordered live anchors from the frozen weights. The step row identifies its run. The run's binding supplies the ordered anchor digest used for both twins. Both live and archived query and anchor identities agreed within each arm and across horizons. Every archived write-7 and diagonal read field matched, including raw score bytes, the read vector digest, full matrix and owner-column digests, registry choices and controller. M3 reproduced Cedar first on AA and Alder first on CC. AC and CA were gated on the native checks. [Steps](https://github.com/jackgumpe/eledgercare/blob/7d65875a1ff2d7ad8a008ea83f5484507dbd5db3/docs/reviews/WP-0030/evidence/steps.jsonl) · [Run bindings](https://github.com/jackgumpe/eledgercare/blob/7d65875a1ff2d7ad8a008ea83f5484507dbd5db3/docs/reviews/WP-0030/evidence/bindings.json)

## Change inventory and review map

All paths below were added under `docs/research/WP-0031/`. The report metadata added afterward consists solely of the reserved report path above. [Source diff](https://github.com/jackgumpe/eledgercare/compare/74f23b10d428acc3477db6ce4af7eb663e28d9f4...5e1a464a38ad4213b94b3b25695bd70d9054a6a3) · [Evidence diff](https://github.com/jackgumpe/eledgercare/compare/5e1a464a38ad4213b94b3b25695bd70d9054a6a3...8f31cc66c4878ca086fa5da1498c4a73ed6a6306)

| Paths | Contents |
| --- | --- |
| `inputs.py` | Pinned development archive, manifest, weight, query, ordered-anchor and archived trace bindings |
| `experiment.py` | `prepare_prefix`, `cell`, `read`, `run_arm`, state and gate checks, contrasts and the conditional controls |
| `replay.py` | Source freeze, pinned runtime admission, one-thread execution and evidence serialization |
| `evidence/M1.json`, `evidence/M3.json` | Native and crossed reads, donor tensors, per-cell input and state hashes, complete discrete snapshots, contrasts, trigger and empty cells |
| `evidence/M1-Alder-write7.f32`, `evidence/M1-Cedar-write7.f32` | Saved 1 × 128 × 128 matrices, little-endian FP32, 65,536 bytes each |
| `evidence/M3-Alder-write7.f32`, `evidence/M3-Cedar-write7.f32` | Saved 8 × 128 × 128 matrices, little-endian FP32, 524,288 bytes each |
| `evidence/inputs.json`, `evidence/runtime.json` | Archive, member and source hashes, execution receipt and output checksums |

## Verification and external effects

| Check / command | Revision and actual result |
| --- | --- |
| `Get-FileHash 'C:/Users/jackg/Downloads/Option A Release Order - Write-8 Bounded CPU Replay.pdf'`, read all six pages with pypdf | Order SHA-256 `2e77963afa6b49730f86957ad85ff6bd8597f264077c665769e3be01b5df4bb1` |
| `git status --short --branch`, `git rev-parse HEAD`, Python AST parse of the three source files, and `git diff --cached --check` | Clean assigned base at start. Syntax and staged whitespace checks passed before freeze. |
| `& 'C:/Users/jackg/eLedgerCare-Speed/WP-0030/runtime/venv/Scripts/python.exe' -I -B docs/research/WP-0031/replay.py 5e1a464a38ad4213b94b3b25695bd70d9054a6a3` | One decisive invocation, exit 0. Python 3.12.10, torch 2.13.0+cpu, NumPy 2.2.6, deterministic FP32, one intra-op and one inter-op thread. The Windows venv launcher records its underlying interpreter in `sys.orig_argv`. The executable path and SHA-256 of the pinned venv launcher were checked in the entry point. [Runtime receipt](https://github.com/jackgumpe/eledgercare/blob/8f31cc66c4878ca086fa5da1498c4a73ed6a6306/docs/research/WP-0031/evidence/runtime.json) |
| Stage, whitespace-check and commit the eight copied evidence files. Read committed blobs with `git cat-file blob` and inspect with Python stdlib `hashlib`, `struct` and `json`. | At `8f31cc66c4878ca086fa5da1498c4a73ed6a6306`, all eight blobs matched the scratch and checkout bytes. All seven payload hashes matched the receipt. Four matrix-file sizes and SHA-256 values matched their snapshot metadata. All 13 M1 and 14 M3 gate groups passed. Byte decoding reproduced the scores, signed margins and increments. Checks reproduced all six contrasts, both trigger outcomes, both D0 values and source-state invariance across twelve cells. |
| `& 'C:/Users/jackg/eLedgerCare-Speed/WP-0031/coordination/push.ps1' -ExpectedHead (git rev-parse HEAD)` | Published the evidence and its frozen parent on the owned branch. The script's remote check returned `8f31cc66c4878ca086fa5da1498c4a73ed6a6306`. The report publication SHA and final remote confirmation are returned to root after the report commit. |

The retained external scratch is `C:/Users/jackg/eLedgerCare-Speed/WP-0031/author/5e1a464a38ad4213b94b3b25695bd70d9054a6a3`. This run used the existing read-only CPU environment and synthetic development archives. It stopped before write 9. Held-out access, a new posting, GPU, OCR, tuning, production changes and an alternative update rule were outside the execution scope.

## Handoff and limitations

There were no blocked cells or CPU execution failures. Both original lengths share this one printed edit. The evidence supports a conditional statement about these donor bundles, prefixes and probes. It cannot establish which individual feature, box coordinate or mechanism caused the shift, or estimate accuracy on other documents. Independent author-code inspection and reproduction belong to eld-rd-reviewer at the pinned source and evidence revisions above. Coordinator disposition is pending.
