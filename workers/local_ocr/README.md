# eLedgerCare Production Local OCR Worker (`workers/local_ocr/`)

Self-contained production Python child worker for feature F2 ([`docs/design/F2-local-extraction.md`](../../docs/design/F2-local-extraction.md)).

## Boundaries

- Invoked exclusively by `ELedgerCare.Infrastructure` (`LocalPythonOcrWorkerRunner`) inside a race-free Windows Job Object (`CREATE_SUSPENDED` -> `AssignProcessToJobObject` with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` -> `ResumeThread`), using `ArgumentList = ["-I", "-B", "-X", "utf8", "-u", "<repo>/workers/local_ocr/run_worker.py", "--request", "<runDir>/request.json"]` with `UseShellExecute = false`.
- Receives **no** database credentials, user-supplied file paths, network access (`HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `HF_HUB_DISABLE_XET=1`, `PIP_NO_INDEX=1`), or shell-interpolated arguments.
- Reuses `C:\Users\jackg\eLedgerCare-Q0\WP-0005` (`venv`, `models\Unlimited_OCR_2_04809669`, `notices\...`) strictly **read-only**; all module caches (`HF_MODULES_CACHE`), Hugging Face / Torch / CUDA caches, temp directories, heartbeats, raw outputs, and `eledgercare.local-extraction/1` result envelopes are written inside the attempt's owned directory under configured `WritableRuntimeRoot`.
- Zero imports, file reads, `git.exe` calls, or subprocess invocations target `qualification/`, `research/`, or `evaluation/`. No accuracy scorer or OCR mock exists here.
