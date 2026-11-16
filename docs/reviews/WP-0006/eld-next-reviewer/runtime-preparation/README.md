# WP-0006 Independent Reviewer Runtime-Preparation Checkpoint (`eld-next-reviewer`)

> **Ordinary Reviewer Runtime-Preparation Checkpoint (NOT Canonical `WP-0006 /004`)**
> **Disposition**: **INDEPENDENT REVIEWER RUNTIME PROCEDURE & DRIVER FROZEN (`863fcd3a94188aa5a09b4e53f0f7192022950cbd`) AND CPU-ONLY VALIDATION PASSED (`3 / 3` DECISIVE COMMANDS `EXIT 0`, `17 / 17` VALIDATOR TEST METHODS PASSED).**
> Canonical `WP-0006 /004` (`docs/agent-reports/eld-next-reviewer/WP-0006/004_2026-11-16_review_eld-next-reviewer.md`) remains **held** until `eld-coordinator` binds the published tip SHA of this checkpoint in a fresh sole reviewer GPU runtime release after the active `WP-0007` lease returns and `eld-f2-implementer` completes actual `WP-0006` runtime + `/003`.

## 1. Reviewer Identity, Lineage, and Exact Revisions

| Field | Value |
| --- | --- |
| Reviewer agent ID | `eld-next-reviewer` |
| Conversation / session ID | `101b19cf-3133-4ead-91cb-9ca6068e3e72` |
| Disclosed actual model / effort | Google DeepMind **Gemini 4 Carbon (High)** (`gemini-4-carbon-high`, `High` effort) |
| Repository | `https://github.com/jackgumpe/eledgercare` (private) |
| Owned branch | `review/wp-0006-0007-next-tracks` |
| Owned worktree | `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-next-reviewer` |
| Coordinator preparation authority | `0e16cfd473b1dab3b6109c6fba8e7425e91c4ae5` ([WP-0006-eld-next-reviewer-runtime-preparation.md](../../../../../docs/kickoffs/WP-0006-eld-next-reviewer-runtime-preparation.md), [source-reconciliation-acceptance-audit.json](../../../../../docs/coordination/WP-0006/source-reconciliation-acceptance-audit.json)) |
| Clean starting reviewer base | `82e8f732afbf038bfb5b6c560f1b1219aaa4e40f` (accepted Stage 1 source/CPU/child/PostgreSQL reconciliation; prior reviewer CLI finished `SUCCESS` / `exit 0`) |
| Accepted design review `/002` SHA | `e2452e1ab3d8937868c07ffb30ce430715b5be78` ([002_2026-11-16_review_eld-next-reviewer.md](../../../../../docs/agent-reports/eld-next-reviewer/WP-0006/002_2026-11-16_review_eld-next-reviewer.md), immutable) |
| Unchanged accepted product source | `8a73b7a5dab51e3ccf803aceedded4929529dd35` (`0` product/worker/test/web/deploy files modified) |
| Inspected author `v2` prep & freeze | `882438d037fdb754df487c1d20a8bc958f81aeb2` / `5b33924b0a95db02731dcfa344131592e31fce30` ([runtime-corrected-preparation/README.md](../../../../../docs/implementation/WP-0006/runtime-corrected-preparation/README.md); normal-merged with full author attribution preserved) |
| Reviewer normal merge commits | `45cc0864e3dfb2d8cae7fd82a576e74160d8f360` (`0e16cfd4...`), `4f99123daf8474e42357a3b2d9a269feb2b17f8a` (`882438d0...`) |
| Retained initial helper candidate | `0de423c66b9af041f2211cfeeebc6e996961da8f` (helper-only diff-base check compared immutable reviewer folders against `8a73b7a5...` instead of `82e8f732...`; retained at [01-validate-prep-0de423c.log](retained-failures/01-validate-prep-0de423c.log)) |
| **Frozen helper & procedure commit** | **`863fcd3a94188aa5a09b4e53f0f7192022950cbd`** ([PROCEDURE.md](PROCEDURE.md), [helpers/run_f2_reviewer_runtime.py](helpers/run_f2_reviewer_runtime.py), [helpers/verify_ui_reviewer_real_results.mjs](helpers/verify_ui_reviewer_real_results.mjs), [helpers/validate_reviewer_runtime_prep_cpu.py](helpers/validate_reviewer_runtime_prep_cpu.py)) |
| **Post-freeze validation evidence SHA** | **`e7733f9e8dde1a3db229bf9da5e0f5f90069c6f8`** ([validation-summary.json](validation-summary.json), `logs/01..03*.log`) |
| Next owner | `eld-coordinator` (wait for active `WP-0007` lease return, actual `WP-0006` author runtime + `/003`, and fresh reviewer runtime release binding; zero user permission pending) |

---

## 2. Independent Reviewer Runtime Architecture & Release Validation Guarantees

1. **Separate Clean Executing HEAD, Ancestry, and Exact Product/Immutable Tree Verification**:
   - Consumes `--release-commit <40-hex-sha> --release-path <git-rel-path>` strictly from Git objects (`git cat-file -p`), rejecting historical/returned/preparation commits (`d106db76...`, `9ae311e3...`, `97e65bed...`, `717a7689...`, `2c549274...`, `2ce3366d...`, `35e2f44d...`, `0e16cfd4...`) and author/returned/`WP-0007` leases.
   - Replaces immediate-parent assumptions with `git merge-base --is-ancestor` checks for `source_commit` (`8a73b7a5...`), `accepted_design_review` (`e2452e1a...`), and `accepted_source_review` (`82e8f732...`), paired with exact Git tree/blob OID verification across `src`, `workers/local_ocr`, `workers/ocr`, `web`, `tests`, `deploy`, `ELedgerCare.slnx`, `qualification/q0`, `research`, `evaluation`, and all prior immutable `eld-next-reviewer` folders (`design`, `preparation`, `implementation`, `source-reconciliation`, `/002`), while confirming canonical `/004` does not yet exist.
2. **Actual Completed Author Runtime Evidence & Canonical `/003` Bindings**:
   - Requires a valid 40-hex `author_runtime_evidence` commit SHA in Git (rejecting pre-model failure `7280463a...`, Stage 1 `6faec9bf...`, source-response `386d5c30...`, and prep-only `5b33924b...` / `882438d0...`) and a valid 40-hex `author_003` commit SHA containing `docs/agent-reports/eld-f2-implementer/WP-0006/003_2026-11-16_implementation_eld-f2-implementer.md` (with explicit support if the coordinator sets `allow_bounded_sequencing_without_003_prose: true` for runtime start while keeping final `/004` held for `/003`).
3. **Reviewer Resource Isolation, Finite 4-Attempt Matrix (`F2-01..07`), & Safe Evidence Packaging**:
   - Enforces `owner == "eld-next-reviewer"`, `conversation_id == "101b19cf-3133-4ead-91cb-9ca6068e3e72"`, reviewer loopback ports `5290` (API) / `4310` (UI) / `55435` (PostgreSQL `18.7`), fresh DB `eledgercare_f2_runtime_reviewer`, future writable root `C:\Users\jackg\eLedgerCare-F2\WP-0006\reviewer`, read-only Q0 root `C:\Users\jackg\eLedgerCare-Q0\WP-0005`, `worker_source_sha256 == c1c324c36e27f57c3c4ac4a1462984fbe586ad43ab82af3a2883bb7eac4c0d54`, `<= 4 GiB` / `>= 20 GiB` storage guards, `1,800 s` / `3,600 s` / `300 s` / `6 h` timeout ceilings, and `max_model_attempts == 4` (`[1, 1, 2, 0]`, zero warmups, zero auto-retries, zero holdouts).
   - Independently verifies real `bytea` `sha256(raw_output_bytes)` SQL parity, real OS `(launcher_pid, worker_pid)` creation filetimes and non-zero inference durations (refusing mocks or fake inserts), single-process supervisor `TerminateProcess` + Job Object child cleanup + `2.5 s` zero-auto-retry verification, clean `pg_ctl` fast restart + `LocalOcr:Enabled=false` Edge UI reopen (`0` forbidden DOM tags or `on*=` attributes, `0` trigger/retry buttons on completed docs), descriptive cross-checks against Q0 `F07.warm1.raw.txt` (`893bf578...`) and author `/003` raw SHA-256s, and secret/holdout-guarded `--package-evidence` export.

---

## 3. Protected Product & Immutable Reviewer Git Object Identities Verified

| Path | Git Tree / Blob OID |
| --- | --- |
| `src` | `73d0146b3624ab4928a4d2cda7806d7d6166906e` |
| `workers/local_ocr` | `1ed609368ca4c6bff8b92231362be2d802ae8baf` |
| `workers/ocr` | `493935fad8163ec9242b396232a55564446a52e6` |
| `web` | `f0877a006922818bf731d5f87603a368ed782487` |
| `tests` | `5ad9bd15f41ab24bd5851ca02bfa0d8054dc1453` |
| `deploy` | `dade6a38e165b5cc2ba81ba895bd9d3c572d26f2` |
| `ELedgerCare.slnx` | `c00c2bc5ef46019fb4452fdf0bba7ca2271fc976` |
| `qualification/q0` | `5ca1507d0fb3f5905c9af1cb358642972e9c15dc` |
| `research` | `5036d17e55f96af3bdeea82a20a32eb54a26ddca` |
| `evaluation` | `60fcc7fa1741b6c44489bb9cf8484e03a4cbf019` |
| `docs/agent-reports/eld-next-reviewer/WP-0006/002_2026-11-16_review_eld-next-reviewer.md` | `10729efdedd954983153b4a6a93ef9e9d10753d7` |
| `docs/reviews/WP-0006/eld-next-reviewer/design` | `c1a059a16b06d07d3d026c7b396029498cdd9b64` |
| `docs/reviews/WP-0006/eld-next-reviewer/preparation` | `99ea0d2b1282eaf7ee32e9909c170c1587ad634c` |
| `docs/reviews/WP-0006/eld-next-reviewer/implementation` | `41b4611dbb71185e8dd94b544596749f36741fc8` |
| `docs/reviews/WP-0006/eld-next-reviewer/source-reconciliation` | `49318ac139f771339b787fc9c83d26d87c8a2488` |

---

## 4. Decisive CPU-Only Post-Freeze Validation (`863fcd3a94188aa5a09b4e53f0f7192022950cbd`)

Executed on clean frozen `HEAD = 863fcd3a94188aa5a09b4e53f0f7192022950cbd` via [helpers/validate_reviewer_runtime_prep_cpu.py](helpers/validate_reviewer_runtime_prep_cpu.py) using clearly labeled `TEST_FIXTURE_ONLY` synthetic inputs (see [validation-summary.json](validation-summary.json) and [inventory.json](inventory.json)):

| Step | Check | Result | Duration |
| --- | --- | --- | --- |
| `01` | Python `py_compile`, AST forbidden-import & zero-`HEAD~1` guard, `9` local digest checks, `15` Git tree/blob OID checks, canonical `/004` & external reviewer root absence checks ([logs/01-python-compile-ast-and-tree-guard.log](logs/01-python-compile-ast-and-tree-guard.log)) | `EXIT 0` | `1,235 ms` |
| `02` | `node --check verify_ui_reviewer_real_results.mjs` ([logs/02-node-syntax-check.log](logs/02-node-syntax-check.log)) | `EXIT 0` | `85 ms` |
| `03` | `17` focused `unittest` & CLI subprocess release-validator and evidence-packager test methods ([logs/03-reviewer-release-validator-tests.log](logs/03-reviewer-release-validator-tests.log)) | `EXIT 0` (**`17 / 17` passed**) | `47,381 ms` |

## 5. Checks Intentionally Held for Released Runtime

- **GPU / CUDA / ML model imports, `nvidia-smi` queries, or inference**: Forbidden during preparation (`0` executed; `eld-rd-astra` holds active sole lease `WP-0007-author-heldout-20261116T145544Z`).
- **PostgreSQL (`55435`), `ELedgerCare.Api` (`5290`), and Angular/Edge (`4310`) startup**: Forbidden during preparation; reviewer ports verified unbound (`false`) before and after validation.
- **External `C:\Users\jackg\eLedgerCare-F2\WP-0006\reviewer` and `C:\Users\jackg\eLedgerCare-Q0\WP-0005`**: Untouched; `C:\Users\jackg\eLedgerCare-F2\WP-0006\reviewer` verified absent (`false`) before and after validation.
