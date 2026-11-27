# Admission-01 plan digest

Run from the reviewer worktree containing Git object e95b754bd4dedd44da6f7ab8366843907e676f7c. The script imports only the versioned plan helper and executes the normal read-only stock.py plan command. The scorer and two model arms are outside this check.

```powershell
& 'C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe' -B docs/reviews/WP-0043/review_plan_hash.py 'C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/w043-author/docs/research/WP-0043'
```

The source-checked operation was native.bytes_json(native.plan()) on the actual owner path at 4e699157a0bd62f60dd145c09394438aa84fe1d5. The independent first run used an identical script in reviewer scratch. It returned 0. The in-memory digest from native admission is 60318641e36666d69139aeb4f3e2691f4d15b13ed6ee2539fc1fe7aa4d894072. The reference release used e10c57de22b1e56a872ffbe560256fe4ab2aff836197ca0451078d7073fd2d4e. This hashes the same plan *after* JSON round-trip. The integer bytecode offset keys then sort lexicographically. Both payloads have 6,573 bytes and their first distinguishing byte is 280. The stored plan, original printed plan and independently generated in-memory plan compare equal after parsing. See plan-hash-01.json for keys and raw CLI output SHA-256. Torch was absent from the process, the output path was absent, and source inspection confirms the plan comparison precedes device lock and worker launch. The offline native scorer independently reconstructs the parsed plan for object equality and the original in-memory digest when testing the release hash.
