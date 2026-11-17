# Retained Failures & Reproduced Pre-Fix Findings (`WP-0012 / 006`, `eld-f4-implementer`)

All prior `WP-0012 / 001` retained helper failures remain preserved untouched under [../../retained-failures/README.md](../../retained-failures/README.md) (`51cf3ecc-02-dotnet-build-flag.log` and `7a1bdea9-07-model-manifest-size-key.log`), and independent reviewer `WP-0012 / 002` reproductions remain preserved untouched under [../../../../../reviews/WP-0012/eld-f4-reviewer/author-001-review/observations/author-001-and-v3-verification.json](../../../../../reviews/WP-0012/eld-f4-reviewer/author-001-review/observations/author-001-and-v3-verification.json).

## Reproduced Pre-Fix `/001` Helper Defects vs. Corrected `/006` Proofs

During `WP-0012 / 006` verification ([validate_wp0012_correction_006_cpu.py](../helpers/validate_wp0012_correction_006_cpu.py), `Wp0012Correction006GuardTests` `test_01`..`test_10`), the preserved `/001` helper (`ad5202a029a7a86bea5fa3e3d97760d0a9cc673a`) and corrected `/006` helper ([run_wp0012_rehearsal.py](../helpers/run_wp0012_rehearsal.py) & [drive_rehearsal_edge.mjs](../helpers/drive_rehearsal_edge.mjs)) are exercised side-by-side on CPU using short-lived owned fake CPU child processes and temporary scratch directories:

1. **`F12-B1` (`start_api_and_ui` partial-startup orphan process & open handle leak):**
   - Preserved `/001` helper leaves `api_proc` alive and `api_fh` open on `ui_proc` early exit (`test_01`) and `api_proc` alive on `45s` bind timeout (`test_02`); the test harness immediately reaps its own short-lived test child via Win32 `PID + CreateFileTime`.
   - Corrected `/006` helper terminates every spawned owned child (`api_proc` and `ui_proc` across `test_01`..`test_03`), closes every log handle, and scrubs any credentials written to startup logs.
2. **`F12-B2` (`execute_live_rehearsal` failure-path cleanup, secret scrubbing, `owner-lease-return.json`, & output overwrite guard):**
   - Preserved `/001` helper bypasses `count_ocr_worker_processes()` and `owner-lease-return.json` when Phase A stops on first failure (`test_05`).
   - Corrected `/006` helper refuses pre-existing decisive output directories (`test_07`), stops immediately with `0` retries on Phase A failure, queries `persisted_attempts`, checks worker/launcher/port/model state, scrubs secrets across `ev_out_dir`, and writes `owner-lease-return.json` (`status: "failed_stopped"`, `test_05` & `test_06`).
3. **`F12-B3` & `/007` review gate (`_extract_accepting_preparation_review_sha` & `validate_release_contract`):**
   - Preserved `/001` helper rejects `"independent_preparation_review_002_sha"`, whereas corrected `/006` helper accepts all documented keys (`test_08`) while explicitly rejecting `changes-requested` `WP-0012 / 002` (`379d8c5d607fd248d7f272e412b4ed4a97bc64f6`) and all pre-`/006` or self-review SHAs (`test_09`).
4. **`F12-D4` (`drive_rehearsal_edge.mjs` Phase B `workerEnabled === false` assertion):**
   - Against an ephemeral loopback HTTP server (`127.0.0.1:0`, `test_10`), `workerEnabled: true` exits `1` with `F12-D4 workerEnabled mismatch`, and `workerEnabled: false` exits `0`.

## Retained Pre-Freeze `/006` Dry-Run Failure

- [pre-freeze-01-mock-popen-and-short-secret.log](pre-freeze-01-mock-popen-and-short-secret.log): Initial pre-freeze dry-run of `Wp0012Correction006GuardTests` caught two test-harness mock scoping issues (`subprocess.Popen` patch intercepting `taskkill`'s internal `PIPE` `stdout=-1` in `test_01`..`03` and `poll` `StopIteration` in `test_04`) and a genuine short-token over-redaction in `load_local_secrets` when synthetic `"appPassword": "p"` replaced `"p"` inside `"failed_stopped"` (`test_06`). Fixed before freeze by restricting `fake_popen_*` to `dotnet`/`node` spawns and tightening `load_local_secrets` in [run_wp0012_rehearsal.py](../helpers/run_wp0012_rehearsal.py) to `len(val) >= 4` (while preserving regex `Password=...` scrubbing).
