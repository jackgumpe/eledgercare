# COORD-Q0-01: isolated worker cannot find Git

Coordinator observation on unchanged harness candidate 84cef5ef30685ffee46281fefc5fd1356dbc1876, read from clean author publication 2a52ea58fae2badcb4e9ef47d1cb416c006edca4. This is a harness integration defect, not a model result or independent acceptance verdict.

Helper frozen at **73b5ba98d1e3834cc8c58768ff269730b867ee4c**, path [worker-git-check.py](worker-git-check.py), SHA-256 **a2125bdc42bfdbf3aa84056f9f0736f438d9d272dfaa085dd2a58b9f036b1c52**. Executed on 2026-11-15T17:37:36Z with the existing CPython 3.12.10 interpreter:

`C:\Users\jackg\AppData\Local\Programs\Python\Python312\python.exe -I -B docs\coordination\WP-0005\diagnostics\worker-git-check.py`

[Recorded output](worker-git-observation.json): a separately spawned Python process using either build_stage_env(network=False) or build_child_env reports shutil.which('git') = null. Calling the unchanged q0harness.release.code_identity(repo) inside that process raises FileNotFoundError / WinError 2. The diagnostic exits 0 because it records the caught exception; this is not a passing identity check. No external runtime root, packages, model or GPU was created.

The environment builders intentionally replace PATH with the venv Scripts directory and Windows system directories. The harness still invokes bare git in code_identity and locks.git_blob_reader. The installation preflight and runtime child therefore cannot perform their required Git-based identity/metadata checks in the very environments specified by the protocol. Parent-environment CPU tests do not exercise this boundary.

Author action: make the required Git operations available through an explicit, scoped mechanism while retaining the clean environment, source/lock verification and credential stripping. Do not inherit the entire parent environment or change global PATH/settings. Add a meaningful real-child regression check under both generated environments, using existing Python/Git and no model/install/GPU work. Freeze the changed harness before decisive validation. Model/custom source/weights, package pins and input contract stay unchanged. The independent reviewer must validate the correction before runtime release.

An internal relay from the availability probe was rejected because it belonged to another AGY project; no message was delivered by that attempt. A subsequent sender scoped to the existing review project timed out before any observed tool call (0 tokens reported, delivery unconfirmed). No bypass flag, cross-project grant or global setting change was applied. This published finding and the bound follow-up assignment are the authoritative handoff.
