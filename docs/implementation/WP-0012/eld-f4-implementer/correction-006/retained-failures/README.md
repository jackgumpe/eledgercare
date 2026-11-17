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

- [pre-freeze-01-mock-popen-and-short-secret.log](pre-freeze-01-mock-popen-and-short-secret.log): Initial pre-freeze dry-run of `Wp0012Correction006GuardTests` caught two test-harness mock scoping issues (`subprocess.Popen` patch intercepting `taskkill`'s internal `PIPE` `stdout=-1` in `test_01`..`03` and `poll` `StopIteration` in `test_04`) and a genuine short-token over-redaction in `load_local_secrets` when synthetic `"appPassword": "p"` replaced `"p"` inside `"failed_stopped"` (`test_06`). Carbon amended its partial draft by restricting `fake_popen_*` to `dotnet`/`node` spawns and tightening `load_local_secrets` in [run_wp0012_rehearsal.py](../helpers/run_wp0012_rehearsal.py) to `len(val) >= 4`. Native inspection found that this omitted short secrets and skipped the connection-password regex when no long secrets existed; the continuation retains all secrets, replaces short whole tokens, and always scrubs `Password=...`. Tests 27–31 cover follow-on cleanup exceptions, taskkill failure fallback, absent `/007` reports, short secrets and output-path safety.

## Native continuation checkpoints

The original failure above and all twelve Carbon partial files were checked byte-for-byte against handoff authority `3bc2ba5cf5db6698d71c99fccc957e54936fb6c2` and committed unmodified as `d9de3bf1719384c8f6801d78278438a3fdde2e22`. That checkpoint is not a passing candidate. The Carbon provider error was low credits; its wrapper exited 3.

Preparatory native checks are retained at [pre-freeze-02](../retained-checks/pre-freeze-02-native-inherited-tests.log) (26 tests passed) and [pre-freeze-03](../retained-checks/pre-freeze-03-native-cleanup-tests.log) (4 additional tests passed). These ran before the final source freeze and are not decisive evidence. Frozen execution is recorded separately under the chosen new evidence directory. The helper's original deletion of existing evidence and broad live smoke rerun were removed before any native decisive execution.

## Independent return-state finding after first native freeze

Reviewer frozen probe `24b19113715dbc3f4ec5672525de9236783285c5` exercised candidate `6d055395b2a4cf22a7926f1728bc31dbe2f315a3`. Its `final/candidate-6d055395-return-01/return-probe.json` records seven cleanup-failure simulations with `clean_return_verified=false` but non-null `returned_utc` and no explicit `lease_returned`. Root released a narrow correction before canonical `/006` publication: always emit `receipt_utc`, set `lease_returned` to the verified cleanup result, and populate `returned_utc` only when true. Tests05/06/27 now assert clean and unreturned states. The original 31-test passing evidence is preserved under `evidence/`; it did not assert this missing distinction. Follow-on verification and inventory use new names, never replacing initial records.

The native [prose-edit error](native-prose-edit-error.log) records an intermediate Windows cp1252 decode failure while editing the runbook. Code/test/inventory changes had already succeeded and were committed at `56d87ffee753708ec7689d8c1d786ef75f8952a6`; no decisive checks ran there. Forward metadata repair uses explicit UTF-8, restores runbook/sample Unicode and corrects the runbook's stale Carbon-only author line. This was an editing failure, not a model or service attempt.
