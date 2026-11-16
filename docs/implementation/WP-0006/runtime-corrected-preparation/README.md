# WP-0006 F2 Versioned Corrected Runtime Driver Preparation Checkpoint (`eld-f2-implementer`)

> **Disposition**: **VERSIONED ACCEPTANCE DRIVER `v2` FROZEN (`5b33924b0a95db02731dcfa344131592e31fce30`) AND CPU-ONLY VALIDATION PASSED (`3 / 3` DECISIVE COMMANDS `EXIT 0`, `16 / 16` VALIDATOR ASSERTIONS PASSED).**
>
> Ready for `eld-coordinator` to bind the published tip SHA of this checkpoint as `executing_head` in a fresh sole-GPU runtime release **after** `eld-next-reviewer` (`101b19cf-3133-4ead-91cb-9ca6068e3e72`) completes independent source reconciliation on `8a73b7a5dab51e3ccf803aceedded4929529dd35` and `eld-rd-astra` returns the active WP-0007 heldout GPU lease. Canonical `docs/agent-reports/eld-f2-implementer/WP-0006/003_2026-11-16_implementation_eld-f2-implementer.md` remains held.

## 1. Identity, Lineage, and CLI Disclosures

- **Author / Session / Model**: `eld-f2-implementer` · Antigravity CLI `2b6861af-031b-4e8b-9ce9-2a6d476f9da0` · **Gemini 4 Carbon (High)** (`High` effort)
- **Prior CLI Wrapper Disclosures**: Earlier Stage 1 (`6faec9b...`), initial runtime-failure (`7280463...`), mid-edit (`3d12dcd...`), and resumed source-response (`386d5c30...`) public CLI runs ended with stream idle timeout or transient network error (`ERROR`, wrapper exit `0` after valid publication where applicable); none of those wrapper runs is claimed as `SUCCESS`.
- **Governing Coordinator Preparation Authority**: `35e2f44d788a99ad1b2d10d1af95536cf1d1981a` (`docs/kickoffs/WP-0006-eld-f2-corrected-runtime-preparation.md`)
- **Starting Clean Branch Base**: `386d5c30809c3c04d6640d9433eb4263306ac126` (`docs/implementation/WP-0006/source-response/**`)
- **Unchanged Corrected Product Source**: **`8a73b7a5dab51e3ccf803aceedded4929529dd35`** (`0` product/test/worker/web/deploy files modified)
- **Retained Initial Helper-Validator Candidate**: `d65a2c99447bd10ee7699190e62f6852d1238a38` (validator's naive line filter matched `HEAD~1` inside the multi-line module docstring of `run_f2_author_runtime_v2.py`; exact failure preserved at [`retained-failures/01-validate-driver-v2-cpu-d65a2c9.log`](retained-failures/01-validate-driver-v2-cpu-d65a2c9.log))
- **Frozen Helper & Procedure Commit**: **`5b33924b0a95db02731dcfa344131592e31fce30`** ([`PROCEDURE.md`](PROCEDURE.md), [`helpers/run_f2_author_runtime_v2.py`](helpers/run_f2_author_runtime_v2.py), [`helpers/verify_ui_real_results_v2.mjs`](helpers/verify_ui_real_results_v2.mjs), [`helpers/validate_driver_v2_cpu.py`](helpers/validate_driver_v2_cpu.py))

## 2. What Changed vs. Retained Initial Driver (`v1` -> `v2`)

1. **Preserves Historical Artifacts Untouched**: Original `docs/implementation/WP-0006/runtime-author/**` (`72bb7157...`), `.scratch/stage2-runtime/**`, PostgreSQL database `eledgercare_f2_runtime_author`, and retained initial failed run directory `attempt-01a1e316-879e-737e-b222-cf9ebea58b09` remain immutable. `v2` writes scratch artifacts only to `.scratch/stage2-runtime-v2/**` and uses clean database `eledgercare_f2_runtime_author_v2`.
2. **Consumes Future Coordinator Release Explicitly**: Requires `--release-commit <40-hex-sha> --release-path <git-rel-path>`, reads the release JSON and pre-lease observation blobs strictly from immutable Git objects (`git cat-file -p`), and rejects historical/returned/preparation commits (`d106db76...`, `717a7689...`, `2c549274...`, `2ce3366d...`, `35e2f44d...`) and returned lease `WP-0006-author-runtime-20261116T062318Z`.
3. **Separates Reviewed Product Source from Later Helper/Evidence Commits**: Replaces `v1`'s `HEAD~1 == source_commit` check with `git merge-base --is-ancestor 8a73b7a5dab51e3ccf803aceedded4929529dd35 HEAD`, path-diff guards, and exact Git tree-object comparisons at both `source_commit` and `executing_head`.
4. **Validates Design & Independent Source-Review Bindings + Updated Worker Digest**: Verifies `accepted_design_review == "e2452e1ab3d8937868c07ffb30ce430715b5be78"`, requires an accepted independent source-reconciliation commit SHA (rejecting unaccepted `10193e2c904f99cfc23c97367f1e5d881b0630f2`), and binds `worker_source_sha256 == c1c324c36e27f57c3c4ac4a1462984fbe586ad43ab82af3a2883bb7eac4c0d54` alongside unchanged model/lock/config/fixture SHA-256s.
5. **Preserves Exact 4-Model-Attempt Acceptance Flow & Retained-Prior Separation**: Keeps the identical 4-attempt real product matrix (`SYN-WO-01` 1p complete -> `SYN-MP-01` 3p complete -> fresh `SYN-WO-01` 1p live-inference single-process supervisor kill + Job Object child exit + explicit retry complete -> API + PostgreSQL fast restart + `LocalOcr:Enabled=false` HTTP & headless Edge saved-result reopen), zero warmups, zero extra retries, and snapshots/protects any retained `attempt-01a1e316-879e-737e-b222-cf9ebea58b09` directory while counting the `<= 4` new model attempts separately.

## 3. Protected Product & Historical Tree Identities Verified Unchanged

| Tree Path | Git Tree OID |
|---|---|
| `src` | `73d0146b3624ab4928a4d2cda7806d7d6166906e` |
| `workers/local_ocr` | `1ed609368ca4c6bff8b92231362be2d802ae8baf` |
| `workers/ocr` | `493935fad8163ec9242b396232a55564446a52e6` |
| `web` | `f0877a006922818bf731d5f87603a368ed782487` |
| `tests` | `5ad9bd15f41ab24bd5851ca02bfa0d8054dc1453` |
| `deploy` | `dade6a38e165b5cc2ba81ba895bd9d3c572d26f2` |
| `qualification` | `b5918e65cb20b45cad83506b80d8a8bc611807ec` |
| `research` | `5036d17e55f96af3bdeea82a20a32eb54a26ddca` |
| `evaluation` | `60fcc7fa1741b6c44489bb9cf8484e03a4cbf019` |
| `docs/agent-reports` | `189807c0e6bd8ab4cc9b2dcd048db21afc51cdfd` |
| `docs/implementation/WP-0006/stage1-checkpoint` | `4acac7f102826f445687693190a34098d640bb6c` |
| `docs/implementation/WP-0006/runtime-author` | `72bb71576a88506d486c78d6ce0d3e0b4f66ebf0` |
| `docs/implementation/WP-0006/source-response` | `352d356920a7cc0b2b6c3c40d63ad246db441822` |

## 4. Decisive CPU-Only Post-Freeze Validation (`5b33924b0a95db02731dcfa344131592e31fce30`)

Executed on clean `HEAD = 5b33924b0a95db02731dcfa344131592e31fce30` via [`helpers/validate_driver_v2_cpu.py`](helpers/validate_driver_v2_cpu.py) (see [`validation-summary.json`](validation-summary.json) and [`inventory.json`](inventory.json)):

| Step | Check | Result | Duration |
|---|---|---|---|
| `01` | Python `py_compile`, AST forbidden-import & `HEAD~1` guard, 9 local digest checks, 12 Git tree OID checks ([`logs/01-python-compile-and-ast-guard.log`](logs/01-python-compile-and-ast-guard.log)) | `EXIT 0` | `917 ms` |
| `02` | `node --check verify_ui_real_results_v2.mjs` ([`logs/02-node-syntax-check.log`](logs/02-node-syntax-check.log)) | `EXIT 0` | `65 ms` |
| `03` | 16 focused `unittest` & CLI subprocess release-validator tests ([`logs/03-driver-release-validator-tests.log`](logs/03-driver-release-validator-tests.log)) | `EXIT 0` (**`16 / 16` passed**) | `23,703 ms` |

## 5. Checks Intentionally Not Run During Preparation

- **Real GPU / CUDA / ML model execution or `nvidia-smi` queries**: Forbidden during CPU-only preparation; B0 author holds the active WP-0007 heldout GPU lease.
- **PostgreSQL (`55434`), `ELedgerCare.Api` (`5190`), and Angular/Edge (`4210`) live service startup**: Forbidden during preparation; ports verified unbound (`false`) before and after validation.
- **External `C:\Users\jackg\eLedgerCare-F2` and `C:\Users\jackg\eLedgerCare-Q0` reads/writes**: Untouched during preparation.
