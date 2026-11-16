# WP-0009 /011: F006-01 sentinel policy correction

Author: eld-mapping-author, same native Codex /root/mapping_author session, requested xhigh; actual backend identity/effort not separately exposed. CPU-only author verification, pending independent /006 reconciliation.

Root authority **35c095943e71f76b8bfe4f9d6a76e38dd55182e0** authorizes only the declarative sentinel correction and consistency test. Initial clean /005 publication **8942eb843c635ef381da11d9d5ce95524eeb979e** is unchanged. A normal conflict-free authority merge produced work base **213bd0d509a8db3518946d64293e7d183dc06d40**. Independent initial finding **93dd59606c39f2cd7dca77c7773ffac0b2eb0e81**, `docs/reviews/WP-0009/eld-mapping-reviewer/006/initial-findings.md`, was read as an exact Git object; its evidence remains unchanged.

Frozen corrected source/helper: **23e023045b335540d830ce01b75be247552a63f1**. Mapping namespace tree: **59f66d0d3d9be145a43efcc9258eb260d3ef2f00**. Protocol SHA256: **f54214cc42307eb955f44f4c6470311f01ff7cf93887ea21d024feaa08a63e42**.

Only `qualification/mapping_v1/protocol.json:sentinel_policy` and `qualification/mapping_v1/tests/test_release.py` changed. The policy now requires only `multi_page`, declares one measured document with three pages and clean-digital-only scope, and explicitly excludes single-page and raster/hybrid sentinel coverage. Existing opaque sentinel `WP09-F04-v0` and all executable schedules remain unchanged. The new test derives the reviewer measured entries and page categories from the actual finite schedule and fixture metadata, then checks policy count/page/category/scope, excluded warmups and preselection binding. It would reject the inherited three-category declaration. No production validation behavior was added or removed.

The unchanged frozen CPU runner executed:

```text
python -I -B qualification/mapping_v1/run_checks.py --out docs/evidence/WP-0009/eld-mapping-author/011/attempt-1
```

On Windows / CPython 3.12.10, from clean source, 2026-11-16T20:28:52.0774666Z through 20:29:00.4821798Z: **exit 0; 23 tests, zero failures/errors/skips; all 26 original full B0 scores and the separate recovery score reproduced; 27 printed and typed field gains, zero losses; 123 consumed inputs recorded.** All 361 primary field and 1801 cell denominators remain, including the original failed primary document. Recovery remains supplemental. This is unchanged exposed-data mapping evidence, not new generalization or model accuracy evidence.

All prior guard, ambiguity, duplicate, provenance, parser-limit, comparator-independence, runtime fault-injection and real owned Windows-job cleanup checks ran again. Intentional mocked failures remain visible in stdout with their expected failure statuses and preserved denominators. A temporary owned standard-library Python child joined the owned Windows job; its termination and an unrelated owned child's continued life were observed, then that other test child was separately cleaned. No other owner's process was terminated.

The seven retained attempt files are [comparison.json](../../../../evidence/WP-0009/eld-mapping-author/011/attempt-1/comparison.json), [execution.json](../../../../evidence/WP-0009/eld-mapping-author/011/attempt-1/execution.json), [input-inventory.json](../../../../evidence/WP-0009/eld-mapping-author/011/attempt-1/input-inventory.json), [stderr.txt](../../../../evidence/WP-0009/eld-mapping-author/011/attempt-1/stderr.txt), [stdout.txt](../../../../evidence/WP-0009/eld-mapping-author/011/attempt-1/stdout.txt), [summary.md](../../../../evidence/WP-0009/eld-mapping-author/011/attempt-1/summary.md), and [tests.json](../../../../evidence/WP-0009/eld-mapping-author/011/attempt-1/tests.json).

[verify_correction.py](verify_correction.py) is committed with the deliverable before its inventory run. It checks every work-base file outside the two permitted source paths, unchanged critical /005 source blobs, the complete comparison payload against /005 except source identities, all 123 consumed input hashes, and every changed path. Its later `deliverable-verification.json` records published/worktree byte hashes separately so ordinary Git newline normalization is explicit. Report metadata follows those deliverable/inventory commits separately.

No CPU test failed in this correction. Setup retained two routine command failures: a kickoff read before the new authority was merged could not find the file; `git merge --ff-only` rejected divergent history. The subsequent authorized normal merge was conflict-free; no reset/rebase or historical rewrite occurred. Prior /005 attempts and the reviewer's initial F006-01/AST-helper failure evidence are unchanged.

No fresh sealed/published document content, source labels/layouts/answers, model/GPU queries/imports/inference, services, downloads or external runtime roots were accessed/created. Ignored test scratch remains within this owned worktree. No mapper/scorer/typed/parser change or new treatment/call is included. Actual fresh release loading, model preflight and runtime remain unrun pending independent /006 acceptance and exact root release; root alone owns future unsealing and GPU lease.
