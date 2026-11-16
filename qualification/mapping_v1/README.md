# WP-0009 mapping v1 and finite paired evaluation

This research-only namespace implements one selected quality change: **guarded immediate-right-neighbor field association in otherwise unmapped native tables**. It also prepares a separately gated finite runtime adapter. Nothing imports it from product code. Baseline/Q0 source, vocabulary, parsing, scoring, typed conversion, corpus and historical evidence remain immutable.

Authority: `c30d360380fb9816b251acbb6ad53ba4de0e10dc`. Independent diagnosis /002: `ca96f769c822b1b5ef28b377e27d665e2f1f8b98`. Fresh public reservation predates implementation at `7513a9a86e6af55a6d8ca7f5a8dc0f80f054ba0b`; admission /004 is `3e5d305d0cdcb2666ba56912ba6c06dc19d74c8b`. Only public hashes, opaque IDs, counts and schema types were read. No fresh source/expected/native data or identifying layout was opened. This source is a CPU candidate for independent /006, not permission to unseal or execute.

## Exact mapping delta

`mapper.py:extract_prediction` is derived from `qualification/baseline/native.py` at `522f15f1f6e399c36b9c6c107fc08f51862f1fc1`, accepted baseline tree `deae8e826f4770e880374c68e6a56c8c65b6f8a3`. It uses unchanged B0 `norm`, `parse_native` and `mapping.json`; all existing field/table/anchor/unmapped extraction remains copied unchanged apart from the guarded choice below. No expected answers, fixture IDs, known document values, diagnostic boxes, aliases, fuzzy repair or learned parameters enter prediction.

Only when no recognized data table is active and a cell exactly matches an existing known label (B0's trailing-colon handling), use its immediate right cell if **all** conditions hold:

1. The mapped field identity has exactly one B0-recognized label occurrence on that native page. Counting includes aliases and inline matches in all cells/blocks. This is deliberately conservative: recognized words in prose can make a page ambiguous. Separate pages retain separate occurrences.
2. A right cell exists and every cell in the current row has unit colspan and rowspan. Spans in other rows are not expanded; the current row must be structurally simple.
3. The right cell is nonempty after B0 normalization, does not end in a colon, and contains no B0-recognized label match. Unknown colon-ending labels and strings containing known labels are rejected.
4. A further immediate cell to the right does not supply another nonempty plain value. A label-like cell is a boundary; a second plain value is ambiguous.
5. The next row's cell in the label's column does not also provide a nonempty plain value. A label-like below cell is a boundary; another plain value makes orientation ambiguous.

Otherwise preserve B0's existing below-row/inline behavior exactly. Rejection does not retroactively correct old associations. Accepted pairs emit once through an exclusive branch and retain label `location`, plus `association='immediate_right_neighbor'` and `value_location` for audit. Existing duplicate candidates are preserved by fallback; they are not silently deduplicated. Recognized data-table rows and existing non-table coordinate rules are unchanged.

The 27 diagnosis opportunities are not hard-coded or a score target. The decisive comparison reports all actual changes, gains and losses, including any guard-caused shortfall. Primary metric: printed field exact-match equal-family mean using original B0 aggregation. Typed fields, tables, text, page, absence and unmatched diagnostics remain separate. Gains are mapper effects on saved raw bytes, not recognition or model-latency improvements. Unsupported unit grammar and numeric-only quantity comparison remain unchanged.

## CPU checks and regression

Freeze all source/test helpers in Git, with a clean tree, before:

```powershell
python -I -B qualification/mapping_v1/run_checks.py --out docs/evidence/WP-0009/eld-mapping-author/005/attempt-1
```

Use a fresh output directory for every attempt. Capture launch stdout/stderr in ignored owned `.scratch` until completion so the clean-source check is meaningful; copy them into that attempt afterward. Preserve failures and freeze any corrected source before rerun.

The runner installs an import blocker for torch/transformers/triton/PDFium and the model backend. It executes crafted mapping positives/negatives, release/schedule/schema rejection, mocked supervisor failures and an actual short Windows job cleanup test using only two owned standard-library Python children. The unrelated owned test child must survive closing the joined child's job and is then separately cleaned up. No real GPU observer, model, service or released runtime root is used by tests.

Both mappers then consume the same 25 retained primary raw outputs plus the unavailable original failure; original full score objects/summaries must reproduce before comparison. All26 primary rows stay, and the completed parse-invalid recovery stays separate. The runner keeps every field change and full candidate score, verifies unchanged table/cell/row/absence/text/page/link objects, and fails if a previously correct printed or typed field loses credit. Original correct cells are protected by full object equality. Inputs and imported repository source are hashed. The old heldout split is exposed regression data.

## Finite operational adapter

`runtime.py` is an explicitly attributed operational adaptation of accepted B0 `runtime.py` at the same source revision. Unchanged `directory_size`, `guard_reason`, `supervisor_diagnostic`, `q0_imports` and `winjob` are imported read-only. The qualified Q0 environment/session/backend/render/telemetry/lock/model verification primitives are reused unchanged and imported lazily **only after release validation and owned job joining**. `common.py` rejects conflicting B0 module origins. No monkeypatch changes comparator behavior; test-only process/observer fault injection does not execute in runtime code.

Adaptation changes are operational: new release/input namespace, finite public schedule, new owned job prefix, parent plan/job binding, no calls after first failure, retained later anomalous observations, a fail-closed idle-device observation before child launch, explicit lease expiry during supervision/before calls, and unknown/finalization failure preservation. It preserves original log/raw/storage/time/stall bounds, child environment isolation, kill-on-job-close and cleanup by owned handles. It never stops another owner's process.

The protocol freezes exactly two excluded historical warmups per cold load, `SYN-WO-01-v0-clean` then `SYN-MP-01-v0-clean`. Author then measures each of four opaque fresh fixtures once in public reservation order. Reviewer measures only preselected three-page **WP09-F04-v0** once after the same warmups. No retries, repeated primary calls, result-based sentinel choice or replacement. A first failure ends calls, keeping later scheduled rows as `not_run_after_failure`; all four author primary denominators remain. Any later supplement requires separate root authority and cannot replace first outcomes.

One genuine native extraction feeds both mappers. `scoring.py` calls unchanged B0 `score_document`/`summarize` with unchanged typed conversion. It loads canonical expected/reference objects only on the reference side; predictions receive raw/native data and frozen mapping rules only. Schema-only confirmation establishes `pages:list[str]`, `coverage:object` and B0 expected keys. Additional reference `runs`/bbox/quantity metadata never enters prediction. No metric or normalized target is redefined.

The future publication prefix is **evaluation/mapping_v1/**, preserving sealed relative paths such as `corpus/r1/...`. Public per-role sizes/SHA256 must match exact future worktree bytes and the root-bound corpus commit. Existing `evaluation/` files are not changed. Fresh content is read only after authenticating source acceptance, corpus admission, exact root unseal and runtime release. No runtime root is created by validation.

## Later root release contract

No usable release is included. Root must create an immutable JSON under `docs/coordination/WP-0009/releases/`, supplied by exact full authority commit. Required keys are validated in `release.py`:

- `schema='eld-mapping-v1-release/1'`, owner, exact clean `executing_head`, accepted `source_commit`, new namespace `source_tree`, `protocol_sha256`, unchanged `comparator_tree` and `q0_core_tree`.
- `reservation_sha256`, exact future `corpus_commit`, fixed owned runtime root, and the complete exact schedule from `schedule(protocol, owner)`.
- `source_review`, `admission_review`, and `unseal`: each `{commit,path,sha256}`. Admission is pinned to published /004; /006 path is fixed and its accepted publication is bound by root. Review/unseal bytes are verified from immutable Git objects.
- Unseal object must be coordinator-owned and contain `schema='eld-mapping-v1-unseal/1'`, `allow_content=true`, the exact `source_commit`, `source_review_commit`, and `reservation_sha256`. Root binds it only after independently accepted /006.
- `lease={id,owner,gpu_uuid,sole_lease:true,observations:[{commit,path,sha256},...]}` with retained immutable resource observations, aware UTC `issued_utc`/`expires_utc` no more than six hours apart, and `torchvision_local_sha256_TOFU_accepted=true`. Missing/wrong/future/expired releases fail before fresh reads or filesystem mutation. Runtime also requires successful expected-GPU and empty compute-process observations immediately before launch; unreadable/busy output is not interpreted as idle.

Qualified model/protocol/lock/18-object manifest/notice, accepted renderer300dpi, native prompt `Multi page parsing.`, kwargs, tokens/page and ngram windows are unchanged. Existing torch2.13.0+cu130/torchvision0.28.0+cu130/transformers4.52.1/PDFium are verified through the original lock; no install/download is allowed. Read-only Q0 root is reused; future author/reviewer roots are exactly the protocol paths, 4GiB cap, 20GiB floor, six-hour ceiling, sole fixed RTX5070Ti UUID. Old model/runtime telemetry limits and the torchvision local-SHA TOFU exception remain disclosed.

After root release only, CLI entry points are `execute`, owned internal `worker`, and CPU `score-run`, each requiring exact authority/path/owner. Scoring may occur after lease expiry because it performs no inference, but still verifies immutable source/review/admission/unseal/input bindings. Source/worktree identity stays exact. A failed unseal/runtime gate is not permission to change source or open data. `/007` remains held until all independent and root gates pass.
