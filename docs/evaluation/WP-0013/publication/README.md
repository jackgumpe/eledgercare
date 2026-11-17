# WP-0013 unchanged admitted corpus publication

All **120 admitted tracked files / 5,270,705 bytes** are copied unchanged to [evaluation/mapping_v2](../../../../evaluation/mapping_v2/) at corpus commit **`373106d94b56e619e2210308ca3bf237b45affc0`**. The complete public namespace has the same Git tree as the original sealed repository: **`af22f632c2b69531f61866ca467c6f04f386df7e`**. Relative paths, blob identities, modes and working bytes are identical. This is mechanical publication after accepted source review, not another corpus revision or inference run.

The [byte-copy manifest](byte-copy-manifest.json) maps all 120 private-relative paths to exact public paths, with bytes, SHA256, original blobs and modes. Its SHA256 is **`44d01a203e74ffc5babfdb5837a2e67d7fcd582500bcfec62607f7903ae09ec2`**. All 48 original PDF/expected/reference/policy descriptors and twelve actual one-page PDFs across four families were verified. All **4,056 preexisting authority entries** remain unchanged; [authority-tree.json](authority-tree.json) lists every protected path/mode/object.

## Exact authority and original custody

| Binding | Exact identity |
| --- | --- |
| Initial clean owned HEAD | `0adccecc3328fb367e8c8d79d7d29970c309f889`; fast-forwarded to the exact release below |
| Root authority / explicit unseal | `e5c926890ae8c275a8782c8325a15b7d391f23ec`; [unseal.json](../../../coordination/WP-0013/unseal.json) SHA256 `ae4b55fa7a2a23add62340a2adb23cb8bdacf66c2971440690057a4149684a94` |
| Accepted implementation / tree | `c0a1af638e807803b6014b3a93ecb7f9946ce6e1` / `4477104eb2a3c73f496ef451cef9578f54d96518` |
| Independent source /006 | `bb2a731ef6969a6f87508cad4960ca5dc2bafeb1`; [review](../../../agent-reports/eld-mapping-reviewer/WP-0013/006_2026-11-17_review_eld-mapping-reviewer.md) |
| Independent admission /004 | `321afab409989a1eafcb1b43f433d784d2658711`; [review](../../../agent-reports/eld-mapping-reviewer/WP-0013/004_2026-11-17_review_eld-mapping-reviewer.md) |
| Immutable custodian /003 | `0adccecc3328fb367e8c8d79d7d29970c309f889`; [report](../../../agent-reports/eld-eval-custodian/WP-0013/003_2026-11-17_verification_eld-eval-custodian.md) remains unchanged |
| Original public reservation | `b50b2a3bc22927890c8f391943f2a3fe9168d0da`; [reservation.json](../reservation/reservation.json) SHA256 `533f4be35fb89efd9e288c0470201457b5ab32373eab3112ae283b42febcfea5` |
| Original sealed custody | `C:/Users/jackg/eLedgerCare-Vocabulary/WP-0013/sealed`; branch `sealed/wp-0013`; clean, no remote, unchanged at `6bed5df03e161960ca088d4b4bb9417da11fee6a` |
| Original final inventory | `inventory/final-r1.json`; SHA256 `bfb7b818ced3992a28bff3dd7968ac5003b3c47367589817b99c5c2d74039ea0`; 118 entries plus itself and its execution receipt = 120 files |
| Original inventory execution receipt | SHA256 `c5e631ffa637d891113cd9d7101774f5c0e0867ca2772dc4f0e5a8f82b144bad` |
| Original core manifest / tree | SHA256 `91c4a38adeef4ceb2c3fb399eac525e141e4821e9a7dcdf0fb82803e89b86319` / `cca906b35b99362d5b4d0b842dd9981e9481229c` |

Publication is authored by `eld-eval-custodian`, continuing the native session originally requested `xhigh`; actual backend/effort are not exposed. Independent admission/source acceptance retain the reviewers' attribution. Root must independently audit and integrate this exact publication before any separately released finite runtime.

## Frozen verification and actual receipts

[publish.py](publish.py) froze at **`d942c89712769f61b29ca6b0d7ffd4643bd7205d`** before copying; SHA256 **`caacbe434256717b5c347be828ea386c5377511d87c09d8c048d599c821e6ed1`**. The existing Python 3.12.10 / pypdf 7.1.0 environment was used. Each receipt records the exact interpreter/command, timestamps, release bindings and full source mapping. Every operation uses an exclusive receipt; no attempt is overwritten.

| Executed operation | Actual result / evidence |
| --- | --- |
| `--mode copy --run-id copy-001` | First attempt passed, five groups; destination absent, all original disk/Git/inventory identities verified, exclusive copy and public disk equality. [Receipt](attempts/copy-001/receipt.json). |
| `--mode verify-index --run-id index-001` | First attempt passed, five groups; exactly 120 staged paths, all staged bytes equal originals and no text/filter transformation. [Receipt](attempts/index-001/receipt.json). |
| `--mode verify-commit --run-id commit-001 --candidate 373106d94b56e619e2210308ca3bf237b45affc0` | First attempt passed, five groups; all private/public blobs and modes, entire namespace tree, all old authority entries and copy-manifest identities verified. [Receipt](attempts/commit-001/receipt.json). |

All commands use `docs/evaluation/WP-0013/publication/publish.py --helper-commit d942c89712769f61b29ca6b0d7ffd4643bd7205d`. The subsequent inventory mode repeats those identity/preservation checks and inventories every corpus/helper/evidence addition from committed and working bytes; its exact source revision and execution result are in [publication-inventory.json](publication-inventory.json) and the [inventory receipt](attempts/inventory-001/receipt.json). The inventory excludes only its own later file and that inventory attempt receipt, both added in the final metadata commit. No new canonical report is requested or created.

The original corpus `.gitattributes` contains `* -text` and is preserved as one of the 120 admitted files. It disables inherited `eol=lf` normalization, so no root attribute change or additional corpus attribute file is necessary. A separate `* -text` rule preserves newly authored publication metadata. Staged whitespace checks use `cr-at-eol` to recognize retained CRLF; original bytes were never normalized. The copied original READMEs, scripts and receipts intentionally retain historical private paths and earlier pending-phase statements; the explicit unseal and this handoff describe the later state.

## Handoff and boundaries

Public additions are limited to the 120 admitted files and `docs/evaluation/WP-0013/publication/` helpers, mapping, receipts, complete changed/preserved inventories and this handoff. The original sealed repository and its history remain intact. Only tracked files were copied; Git databases, ignored scratch and caches were excluded. Reviewer-owned private admission evidence was not accessed. Canonical /003, the original reservation and all old public paths remain unchanged.

No generation, rendering, mapper/scorer execution, model/GPU/service/process query, dependency installation, download or inference occurred. This publication does not assert fresh mapper performance or grant a runtime lease. The now-exposed corpus is regression material for future work; a later blind evaluation requires another reservation. Normal owned push, exact-origin and clean-state verification follow the metadata commit; full corpus/evidence/inventory publication identities are sent to root without rewriting prior reports.
