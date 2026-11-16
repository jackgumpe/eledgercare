# First dev run: bounded CPU diagnosis

Independent owner `eld-baseline-reviewer`; actual model/effort not exposed. Authority `7d8a9d1052caca53312db76aa54b09a6182a9e4a`, starting reviewer HEAD `c3e1ac810d911a5722b2d29c5035327cdfb8e381`. The accepted source remains `f807e0ac737df4e9e0aeeb96f716afec57f58ff6`, baseline tree `df44162c62641596032df04bc834754da38a5f7b`. This concerns the new runtime incident; earlier /003 findings remain closed.

The already-frozen /005 `reproduce.py` is run under the exact kickoff command against immutable evidence `1d6a681f09b0eaf233f838c54465c36a042ec326` (checkpoint `69ee8796b9b86e7c0090ae91d9efc27999088a7a`), original runtime authority `a6f8f2a17fc8f3db68e11d2971423f78b2dc7861`, release `docs/coordination/WP-0007/releases/author-dev.json`, split `dev`, without a holdout flag. Its output is `../005/dev-first-run/reproduction.json`.

Freeze the following helpers before decisive execution. From the owned worktree, run the probe first while clean, followed by the capture audit:

```powershell
python -I -B docs/reviews/WP-0007/eld-baseline-reviewer/runtime-incident/probe.py --output docs/reviews/WP-0007/eld-baseline-reviewer/runtime-incident/probe-results.json
python -I -B docs/reviews/WP-0007/eld-baseline-reviewer/005/dev-first-run/audit_capture.py --output docs/reviews/WP-0007/eld-baseline-reviewer/005/dev-first-run/capture-audit.json
```

`probe.py` calls the exact accepted `directory_size` and Q0 `Heartbeat`. It checks stable byte counting, injects disappearance after enumeration and after `is_file`, then runs an unpatched concurrent heartbeat writer against repeated directory scans for at most five seconds. The concurrent test accelerates overlap; it is not a reproduction of the original five-second heartbeat cadence. All temporary writes/deletions occur in a newly created owned `.scratch/runtime-incident-*` directory; the writer is joined before exit. Model imports are explicitly blocked. A captured `FileNotFoundError` proves a latent source defect, not the original failing call stack, which lacks filename and traceback.

`audit_capture.py` reads all published blobs under the exact completed run prefix, verifies all capture inventory sizes/hashes, and checks archived model/renderer/input/native/page-marker/phase/exit records. It does not open recorded external paths, rerun measurements or promote partial stdout into completed output. Fresh model/GPU execution, heldout content and final /005 acceptance remain separately gated. No baseline, Q0, scorer, protocol, corpus or product files are changed.
