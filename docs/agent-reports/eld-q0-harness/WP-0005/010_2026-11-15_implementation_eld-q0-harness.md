# WP-0005 / 010: Narrow `COORD-Q0-02` PEP 508 requirement/marker canonicalization and read-only 32-wheel verification

- Report path: `docs/agent-reports/eld-q0-harness/WP-0005/010_2026-11-15_implementation_eld-q0-harness.md`
- Sequence reservation: main `INDEX.md`, WP-0005 `/010` row; authoritative kickoff `docs/kickoffs/WP-0005-eld-q0-harness-metadata-correction.md` (published at `ce28aaf3819f95a508d9776b06454d38da276a08`, updated with `/011` Phase A receipt; Phase B source review dispatched at `dc4de891cc5b3dd59bb8330cda370b6d813a7eec`)
- Category: implementation
- Author / agent ID: `eld-q0-harness`
- Actual model / effort: **Gemini 4 Carbon (High)** (selected `gemini-4-carbon-high` via existing `agy.exe`, explicit `high` effort) in same authorized Carbon author conversation **`bd92ddc3-af60-4096-b683-65386d81b718`**. Original `/002` implementation (`84cef5ef30685ffee46281fefc5fd1356dbc1876`, evidence `0331efd71ef17e5485adac5a53d864c6d96e8f4a`, report `2a52ea58fae2badcb4e9ef47d1cb416c006edca4`) remains attributed to stopped Claude Code Opus conversation `04e0efba-5292-4cae-b922-1517dee7bbed`; `/008` correction (`24a5866b505532fd03e7db62a4e57875e4c5a170`, evidence `b70ff45f2c7aa4b2e454429e76a15fa09887fa9d`, report `460e1d81de14c6f77ea4a026bc4b3ab36407bdf7`) and `/004` Stage B.3 stop checkpoint (`68855420b2dece941eb90c42c69de3c80b47aa06`) were authored in this same Carbon author session `bd92ddc3-af60-4096-b683-65386d81b718` and are preserved byte-for-byte. Separate uninvolved Carbon reviewer `0815536f-045a-4112-8a89-ebf0e0cc782f` (`eld-q0-reviewer`) was neither accessed nor reused; only its published `/011` Phase A receipt (`d211741bce3a341df70402679b4342b6aadb0ab3`) in main `INDEX.md` / kickoff was referenced.
- Execution environment: Antigravity CLI (`agy.exe`) on Windows 11 (`10.0.26200`), PowerShell shell; host CPython `3.12.10` (`C:\Users\jackg\AppData\Local\Programs\Python\Python312\python.exe`, stdlib only), read-only task `venv` CPython `3.12.10` (`C:\Users\jackg\eLedgerCare-Q0\WP-0005\venv\Scripts\python.exe`, `pip 25.0.1` only), and Git `2.55.0.windows.1` (`C:\Program Files\Git\cmd\git.exe`).
- Published by: author (normal owned-branch push)
- Timestamp: 2026-11-15T19:33:15Z
- Repository / branch: `https://github.com/jackgumpe/eledgercare` (private) / `qualification/wp-0005-harness`; owned worktree `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-q0-harness`
- Base revision: continuation base **`68855420b2dece941eb90c42c69de3c80b47aa06`** (`/004` Stage B.3 stop checkpoint; prior `/008` report `460e1d81de14c6f77ea4a026bc4b3ab36407bdf7`, accepted `/008` source `24a5866b505532fd03e7db62a4e57875e4c5a170`); original WP-0005 base **`df9a2b50894f01987d779d7f9ae805794503ce6f`**
- Deliverable revision: frozen `/010` candidate **`41d6204648e4115ab197507d1a22f6d5c7f3e784`** (harness tree `fb2c704c2c36504d79b5eb30fe2efb35b7b01793`); `/010` author evidence **`6dc2d01c84da99d751994cce00a2c82df053c215`**
- Previous report: `docs/agent-reports/eld-q0-harness/WP-0005/008_2026-11-15_implementation_eld-q0-harness.md` (`460e1d81de14c6f77ea4a026bc4b3ab36407bdf7`; canonical `/004` report `004_2026-11-15_verification_eld-q0-harness.md` remains unfilled/reserved)
- Related or reviewed reports:
  - Author `/004` Stage A–B.3 fail-closed stop checkpoint `68855420b2dece941eb90c42c69de3c80b47aa06:qualification/q0/harness/evidence/004-stage-b-stop/README.md`
  - WP-0005 `/009` independent acceptance `af81c9c67ddb4fb233cc93525481c4219d244f53:docs/agent-reports/eld-q0-reviewer/WP-0005/009_2026-11-15_review_eld-q0-reviewer.md` (evidence `6e12e55ce53827f7386889c945c33d524c92658f`, helper `a996543ed533393dc9857eb16f255880c8e08f56`)
  - WP-0005 `/011` Phase A independent all-wheel diagnosis `d211741bce3a341df70402679b4342b6aadb0ab3:docs/reviews/WP-0005/eld-q0-reviewer/metadata-correction/README.md` (helper `60a5e381703a0a723d8bc11b21fd2ed57807c87f` on `review/wp-0005-q0-carbon`)
  - Coordinator storage/install release records `b20a44554cbf356325ad329c1a66d2fb44b36033` and `4fb0ac86e4ca2f9e9b089bf9ae5647d3f7f53677`
- Status: ready-for-review (author verification only; not independent acceptance)
- Next owner: separate uninvolved `eld-q0-reviewer` (`0815536f-045a-4112-8a89-ebf0e0cc782f`) for reserved WP-0005 `/011` Phase B final review

## Summary

This narrow correction resolves **`COORD-Q0-02`** in `qualification/q0/harness/q0harness/locks.py` and verifies frozen candidate **`41d6204648e4115ab197507d1a22f6d5c7f3e784`** against both unit-level positive/negative PEP 508 canonicalization tests and read-only verification of all **32 actual downloaded wheels** (`1,974,477,651` bytes, `850` `Requires-Dist` edges) in both `stage_offline` (`build_stage_env(network=False)`) and stdlib-only bootstrap Python (`-I -B`).

During `/004` Stage B.3 (`68855420b2dece941eb90c42c69de3c80b47aa06`), accepted `/008` source `24a5866b505532fd03e7db62a4e57875e4c5a170` stopped fail-closed before package installation on `fsspec-2025.10.0-py3-none-any.whl`. Both the author's all-wheel audit (`68855420…`) and independent `/011` Phase A (`d211741bce3a341df70402679b4342b6aadb0ab3`) confirmed that all 32 wheel sizes and SHA-256 digests match, both CUDA PEP 658 `METADATA` digests match, `29/32` wheels already pass, and the remaining `3` wheels (`fsspec` ×1, `psutil` ×2, `urllib3` ×2) differ solely by redundant singleton parentheses around comparison atoms in inactive extra-gated PEP 508 markers (`(python_version < "3.14") and extra == "test-full"` vs `python_version < "3.14" and extra == "test-full"`), because `_req_norm` previously stripped whitespace and unified quotes across the raw marker text without parsing PEP 508 boolean grouping.

Candidate `41d6204648e4115ab197507d1a22f6d5c7f3e784` replaces that naïve marker string rewrite with a compact, stdlib-only PEP 508 requirement and marker canonicalizer (`_tokenize_marker`, `_marker_norm`, `_req_norm`, plus fail-closed `unparsed` rejection in `verify_wheel_metadata` and `check_local_record`):

1. Parses PEP 508 markers into a precedence-aware boolean AST (`or` precedence `1`, `and` precedence `2`, comparison atom precedence `3`), unwrapping semantically redundant outer, singleton, associative, and higher-precedence parentheses while retaining parentheses around `or` subtrees inside `and` (`(a or b) and c` $\neq$ `a or (b and c)`).
2. Tokenizes quoted string literals without altering internal characters and serializes string values via `json.dumps(val, ensure_ascii=False)`, preserving literal internal whitespace (`'Windows NT'` $\neq$ `'WindowsNT'`), literal parentheses (`'(dev)'` $\neq$ `'dev'`), and embedded quotes (`"'a'"` $\neq$ `'"a"'`).
3. Preserves exact left-to-right operand order, exact comparison operators (`===`, `==`, `!=`, `<=`, `>=`, `~=`, `<`, `>`, `in`, `not in`), sorted deduplicated extras, sorted PEP 440 specifier clauses (unwrapping balanced outer specifier parentheses), and the full `Counter` multiset of all `850` `Requires-Dist` headers (never skipping inactive `extra == ...` edges and catching any duplicate, missing, or unparseable requirement).

**External runtime state remained 100% read-only and untouched:** `C:\Users\jackg\eLedgerCare-Q0\WP-0005` had `893` files, `1,986,484,301` bytes, `0` reparse points, and `venv` holding only `pip 25.0.1` both before and after verification. No package installation, wheel redownload, `venv` recreation, model download, `torch`/`transformers` import, or GPU execution occurred.

All frozen protocol, dependency-lock, and model-manifest blobs remain **byte-identical** to `/002` (`84cef5ef…`) and `/008` (`24a5866b…`):

- `qualification/q0/harness/protocol.json`: **`dd8a7dc38c2a0c46103f6667f522656a2dddf5882727c18bf7b6b5426c5e2309`**
- `qualification/q0/harness/locks/dependency-lock.json`: **`d8eeaf0fe838d9df5728f17fcbacc8b504d98b79644a524b4faa705d97c49e6e`**
- `qualification/q0/harness/manifests/model-files.json`: **`085ac7ba1e25a7300846de18bdac19c7f9612bf417041643beff6a9cab6b8ea8`**

## Objective and acceptance criteria

Authorized scope from `docs/kickoffs/WP-0005-eld-q0-harness-metadata-correction.md`:

| Requirement | Where met |
| --- | --- |
| Narrowly resolve `COORD-Q0-02` in `q0harness/locks.py`, lock tests, and necessary harness README docs only | `68855420..41d62046` touches only `locks.py`, `test_locks_preflight.py`, and `README.md` (`3` files) |
| Accept semantically redundant singleton/associative/precedence marker parentheses while preserving real `AND`/`OR` grouping | `_marker_norm` AST (`or` prec 1, `and` prec 2, `cmp` prec 3); verified on all 23 parenthesized edges across the 32 wheels and negative grouping tests |
| Preserve literal whitespace, parentheses, and embedded quotes inside quoted strings, plus exact operands, operators, specifiers, extras, and full `Requires-Dist` multiset | `_tokenize_marker`, `json.dumps` string serialization, `_req_norm`, `Counter` comparison, and explicit `unparsed` rejection |
| Keep stdlib-only bootstrap verification working without third-party parsers; preserve exact wheel size/SHA-256 and PEP 658 checks | `verify_wheelhouse` verified in both `stage_offline` task `venv` (`-s -B -P -X utf8`) and stdlib host Python (`-I -B`) across all 32 wheels (`1,974,477,651` B) |
| Freeze candidate first, publish promptly for `/011` Phase B, run decisive checks on clean candidate, keep runtime root strictly read-only, commit `/010` evidence second, publish `/010` report third | Candidate `41d62046…` -> evidence `6dc2d01c…` -> this `/010` report; `C:\Users\jackg\eLedgerCare-Q0\WP-0005` unchanged (`893` files, `1,986,484,301` B) |

## Change inventory

### Continuation base to frozen `/010` candidate (`68855420b2dece941eb90c42c69de3c80b47aa06..41d6204648e4115ab197507d1a22f6d5c7f3e784` — 3 paths)

All 3 candidate changes lie inside `qualification/q0/harness/` (`3` modified, `0` added/deleted):

| Action | Exact path | What changed and why | Relevant symbols |
| --- | --- | --- | --- |
| Modified | `qualification/q0/harness/q0harness/locks.py` | Replace space-stripping marker string rewrite with stdlib PEP 508 requirement/marker tokenizer & precedence-aware AST canonicalizer; reject unparseable requirements fail-closed in `verify_wheel_metadata` and `check_local_record` | `_EXTRA_NAME`, `_VER_CLAUSE`, `_MARKER_IDENT`, `_SIMPLE_OPS`, `_MAX_MARKER_DEPTH`, `_MarkerSyntaxError`, `_tokenize_marker`, `_marker_norm`, `_strip_balanced_outer_parens`, `_req_norm`, `verify_wheel_metadata`, `check_local_record` |
| Modified | `qualification/q0/harness/tests/test_locks_preflight.py` | Expand positive/negative unit tests covering the 5 exact `fsspec`/`psutil`/`urllib3` wheel edges, real `AND`/`OR` grouping differences, literal whitespace/parentheses/embedded quotes inside strings, operand/operator flips, malformed markers/specifiers, and multiset duplicate/missing/inactive-edge guards | `EveryWheelMetadata.test_normalizer`, `EveryWheelMetadata.test_coord_q0_02_wheel_forms_grouping_and_multiset_guards` |
| Modified | `qualification/q0/harness/README.md` | Document stdlib PEP 508 `Requires-Dist` canonicalization alongside wheel SHA-256 and PEP 658 `METADATA` checks | Key capabilities summary |

### Frozen `/010` candidate to `/010` evidence (`41d6204648e4115ab197507d1a22f6d5c7f3e784..6dc2d01c84da99d751994cce00a2c82df053c215` — 12 paths)

All 12 additions lie under `qualification/q0/harness/evidence/010-metadata-normalization/`:

- `.gitattributes` (`* -text`), `README.md`, `run_010_checks.py`, `verify_32_wheels_readonly.py` (`4` files)
- `41d62046/01-unittest-locks-preflight.txt` through `41d62046/06b-readonly-32-wheel-verify-stdlib-host.txt` and `41d62046/summary.json` (`8` raw output/summary files)

Cumulative path counts verified via `git diff --name-only`:

- `68855420..41d62046`: `3` paths
- `41d62046..6dc2d01c`: `12` paths
- `68855420..6dc2d01c`: `15` paths
- `df9a2b50..6dc2d01c`: `141` paths

### Metadata committed afterward and external effects

- **Report metadata committed afterward:** only this file (`docs/agent-reports/eld-q0-harness/WP-0005/010_2026-11-15_implementation_eld-q0-harness.md`).
- **Ignored local scratch:** `.scratch/010-metadata-correction/` (`run_010_checks.py`, `verify_32_wheels_readonly.py`, `outputs/`) and `.scratch/msg-010-*.txt` inside this worktree's untracked `.scratch/` (prior `.scratch/` artifacts preserved untouched).
- **External effects:** normal push of owned branch `qualification/wp-0005-harness` to `origin`; read-only verification against `C:\Users\jackg\eLedgerCare-Q0\WP-0005\wheelhouse` (`32` wheels, `1,974,477,651` B) and read-only `venv\Scripts\python.exe -s -B` invocations. `C:\Users\jackg\eLedgerCare-Q0\WP-0005` remained identical (`893` files, `1,986,484,301` B, `0` reparse points, `pip 25.0.1` only). No coordinator file, reviewer worktree, package installation, model download, or GPU resource was touched.

## Decisions and rationale

1. **Precedence-aware boolean AST instead of parenthesis stripping or marker evaluation.** Blanket parenthesis stripping would conflate `(a or b) and c` with `a or (b and c)` and alter `(dev)` inside quoted literals, while evaluating markers against the current environment would skip inactive `extra == ...` edges (`792` of the `850` locked edges have markers, including extra-gated dependencies). Parsing PEP 508 `or` / `and` / comparison atoms into an explicit AST and serializing with minimal precedence-preserving parentheses resolves all 5 redundant singleton-parenthesis edges (`fsspec`, `psutil`, `urllib3`) and handles compound parenthesized markers already present in `pillow` and `setuptools` (`python_version >= "3.10" and (sys_platform == "darwin" or platform_system != "Darwin")`) without losing grouping semantics.
2. **Injective string-literal serialization and token-level validation.** Previously `s.replace(" ", "").replace("'", '"')` ran across the entire marker and specifier substrings, which mutated spaces inside quoted strings (`'Windows NT'` -> `"WindowsNT"`), collapsed non-escaped embedded quotes (`"'a'"` and `'"a"'` both -> `"""a"""`), and accepted malformed internal spaces (`pkg>=1. 0`). `_tokenize_marker` now scans quoted strings verbatim (rejecting unterminated or multi-line strings) and `_marker_norm` emits `json.dumps(val, ensure_ascii=False)` so distinct string values never collide, while `_EXTRA_NAME` and `_VER_CLAUSE` validate extras and PEP 440 specifiers per token without stripping spaces inside identifiers or version numbers.
3. **Fail-closed `!unparsed:` guard.** Any requirement or marker failing syntax validation returns `"!unparsed:" + s`, and both `verify_wheel_metadata` and `check_local_record` now check `unparsed` explicitly (`ok = (... and not unparsed)`) so malformed `Requires-Dist` headers fail closed even if synthetically duplicated on both sides.
4. **Full 32-wheel audit before freezing.** Prior to freezing `41d6204648e4115ab197507d1a22f6d5c7f3e784`, all `850` wheel `Requires-Dist` headers and all `850` frozen `graph_requires` entries across the 32 wheels in `C:\Users\jackg\eLedgerCare-Q0\WP-0005\wheelhouse` (including all `23` parenthesized marker occurrences across `fsspec`, `mpmath`, `pillow`, `psutil`, `setuptools`, and `urllib3`) were inspected read-only to ensure zero remaining normalization edge cases.

## Verification

Decisive checks executed on clean frozen candidate **`41d6204648e4115ab197507d1a22f6d5c7f3e784`** between `2026-11-15T19:30:56.730638Z` and `2026-11-15T19:31:13.935504Z`, committed at **`6dc2d01c84da99d751994cce00a2c82df053c215`**. Every staged evidence blob was verified via `git cat-file blob` against `summary.json` SHA-256 digests before commit.

| Check / exact command | Environment & revision | Actual result | Evidence location |
| --- | --- | --- | --- |
| `python.exe -I -B .scratch/010-metadata-correction/run_010_checks.py 41d6204648e4115ab197507d1a22f6d5c7f3e784` | Host Python `3.12.10` orchestrating `host` and `stage_offline` checks on clean `41d62046` | Exit `0`: `status: "pass"`, `head_and_worktree_unchanged: true`, `runtime_root_unchanged: true` (`893` files, `1,986,484,301` B), `venv_unchanged: true` (`pip 25.0.1` only), `scratch_test_dirs_left: []` | `evidence/010-metadata-normalization/41d62046/summary.json` (`e7ad31ac…`) |
| ↳ `-m unittest discover -s qualification/q0/harness/tests -t qualification/q0/harness/tests -p test_locks_preflight.py -v` | Host Python `3.12.10` (`-I -B`) on `41d62046` | Exit `0` (`5.641s`): **18/18 tests passed**, including all 30 PyPI packages in normalized & raw forms, 2 real CUDA `METADATA` blobs, the 5 `fsspec`/`psutil`/`urllib3` edges, and negative grouping/quote/whitespace/multiset/unparsed guards | `41d62046/01-unittest-locks-preflight.txt` (`bea97354…`) |
| ↳ `-m unittest discover -s qualification/q0/harness/tests -t qualification/q0/harness/tests -p test_isolated_git_subprocess.py -v` | Host Python `3.12.10` (`-I -B`) + spawned isolated subprocesses on `41d62046` | Exit `0` (`5.734s`): **4/4 real isolated-subprocess Git tests passed** | `41d62046/02-unittest-isolated-git-subprocess.txt` (`bf58350c…`) |
| ↳ `venv\Scripts\python.exe -s -B q0.py lock-check` | `stage_offline` (`build_stage_env(network=False)`) on `41d62046` | Exit `0` (`0.250s`): `lock_sha256` `d8eeaf0f…`, 32 artifacts, 850 edges, all receipt checks `true` | `41d62046/03-lock-check-stage-offline.txt` (`e1769d40…`) |
| ↳ `venv\Scripts\python.exe -s -B q0.py status` | `stage_offline` on `41d62046` | Exit `0` (`0.328s`): `code_identity` `41d6204648e4115ab197507d1a22f6d5c7f3e784` (`harness_clean: true`), `storage_root_exists: true` | `41d62046/04-status-stage-offline.txt` (`3988188a…`) |
| ↳ `venv\Scripts\python.exe -s -B q0.py verify-wheelhouse <wheelhouse> --release <old author-install.json>` | `stage_offline` on `41d62046` | Exit `2` (expected, `0.328s`): `BLOCKED` (`EXECUTION_NOT_RELEASED`, `harness_commit/clean` against prior `460e1d81`-bound release) | `41d62046/05-verify-wheelhouse-stale-release-refused.txt` (`22e67d5e…`) |
| ↳ `venv\Scripts\python.exe -s -B -P -X utf8 verify_32_wheels_readonly.py ... stage_offline` | `stage_offline` (`audit_stage_env` verified) on `41d62046` | Exit `0` (`2.094s`): **`metadata_checked: 32`, `total_payload_bytes: 1974477651`, `all_payloads_ok: true`, `all_metadata_ok: true`, `torch` & `torchvision` PEP 658 digests `true`**, `torch`/`transformers` not imported | `41d62046/06-readonly-32-wheel-verify-stage-offline.txt` (`dd3b6cd0…`) |
| ↳ `python.exe -I -B verify_32_wheels_readonly.py ... stdlib_host` | Host stdlib bootstrap Python `3.12.10` (`-I -B`) on `41d62046` | Exit `0` (`2.188s`): **`metadata_checked: 32`, `total_payload_bytes: 1974477651`, `all_payloads_ok: true`, `all_metadata_ok: true`, both PEP 658 digests `true`** | `41d62046/06b-readonly-32-wheel-verify-stdlib-host.txt` (`aff74a6b…`) |

### Pre-freeze development failure (disclosed and resolved before freeze)

During local authoring before `41d6204648e4115ab197507d1a22f6d5c7f3e784` was committed, an initial pre-freeze run of `test_locks_preflight.py` passed `17/18` tests and failed one subTest (`test_every_pypi_artifact_in_both_forms (n='mpmath', raw=True)`): `mpmath`'s frozen `graph_requires` already stores parenthesized specifiers `(>=4.6)` and `(>=2.1.0a4)`, and `synth_metadata(..., raw_style=True)` wraps `specs` in `({specs})`, emitting `pytest ((>=4.6))`. The initial draft unwrapped only a single outer pair of specifier parentheses. Resolved before freeze in `locks._strip_balanced_outer_parens` (unwrapping balanced outer specifier parentheses while rejecting empty `()`, unbalanced `(==1.0` / `==1.0)`, and multi-group `(==1.0)(==2.0)`), then re-verified (`18/18` and `4/4` passed) prior to committing `41d6204648e4115ab197507d1a22f6d5c7f3e784`.

### Checks not run

- Unrelated unit test modules not affected by `locks.py` (`test_environment_writer_memory.py`, `test_host_model_env.py`, `test_session.py`, etc., per kickoff instruction to run only justified tests rather than a full unrelated suite rerun; `test_isolated_git_subprocess.py` was included to confirm stage subprocess lock checks).
- CLI `q0.py verify-wheelhouse` pass with a `41d62046`-bound coordinator install release (none exists until after `/011` acceptance; stale-release refusal was verified).
- Offline package installation (`pip install --no-index --require-hashes`), `pip check`, installed `venv` `<240` path-length walk, model-shard download/verification, 4-page CPU PDF raster preflight, `torch`/`transformers` import, and GPU qualification (all held for resumed `/004` after `/011` acceptance and coordinator release rebinding).

## Review map

- **Pinned diffs:**
  - Candidate source/test/doc diff (`3` paths): `68855420b2dece941eb90c42c69de3c80b47aa06..41d6204648e4115ab197507d1a22f6d5c7f3e784`
  - Author `/010` evidence diff (`12` paths): `41d6204648e4115ab197507d1a22f6d5c7f3e784..6dc2d01c84da99d751994cce00a2c82df053c215`
- **Primary files to inspect:**
  - `qualification/q0/harness/q0harness/locks.py` (`_tokenize_marker`, `_marker_norm`, `_strip_balanced_outer_parens`, `_req_norm`, `verify_wheel_metadata`, `check_local_record`)
  - `qualification/q0/harness/tests/test_locks_preflight.py` (`test_normalizer`, `test_coord_q0_02_wheel_forms_grouping_and_multiset_guards`)
  - `qualification/q0/harness/evidence/010-metadata-normalization/` (`README.md`, `run_010_checks.py`, `verify_32_wheels_readonly.py`, `41d62046/summary.json`, `41d62046/06-readonly-32-wheel-verify-stage-offline.txt`)

## Risks, disagreements, and unfinished work

- **No open disagreements.** Independent `/011` Phase A (`d211741bce3a341df70402679b4342b6aadb0ab3`) and the author's `/004` stage audit (`68855420b2dece941eb90c42c69de3c80b47aa06`) reached identical factual conclusions across all 32 wheels and 850 edges.
- **Bounded PEP 508 scope.** `_req_norm` intentionally does not accept direct-URL `@ https://...` requirements unless identically matched or needed; none of the 850 locked requirements use direct-URL `Requires-Dist` syntax, and any malformed/unexpected syntax fails closed via `!unparsed:`.
- **Resumed `/004` stages remain pending.** After independent `/011` acceptance and a newly bound coordinator `author-install.json`, `/004` will resume at Stage B.3 (`q0.py write-requirements` / `q0.py verify-wheelhouse` / offline `pip install`) reusing the existing verified `venv` (`pip 25.0.1`) and `wheelhouse` (`32` wheels, `1,974,477,651` B) without redownloading or recreating `venv`, followed by Stages C–D and (only after separate execute release / GPU lease) Stage E.

## Handoff

- **Next action & owner:** Independent non-author Phase B completion and canonical **`WP-0005 /011`** publication by separate Carbon reviewer **`eld-q0-reviewer`** (`0815536f-045a-4112-8a89-ebf0e0cc782f`), followed by **`eld-coordinator`** disposition and rebound `author-install.json` for resumed `/004`.
- **Pinned revisions for `INDEX.md` / `/011` binding:**
  - Owned branch: `qualification/wp-0005-harness`
  - Continuation base: **`68855420b2dece941eb90c42c69de3c80b47aa06`** (original WP-0005 base `df9a2b50894f01987d779d7f9ae805794503ce6f`)
  - Frozen `/010` candidate SHA: **`41d6204648e4115ab197507d1a22f6d5c7f3e784`** (harness tree `fb2c704c2c36504d79b5eb30fe2efb35b7b01793`)
  - Author `/010` evidence SHA: **`6dc2d01c84da99d751994cce00a2c82df053c215`**
  - Canonical `/010` report path: `docs/agent-reports/eld-q0-harness/WP-0005/010_2026-11-15_implementation_eld-q0-harness.md` (its publication commit SHA is supplied in the handoff message after commit and `origin` verification; this report does not claim to contain its own commit SHA).
- **Publication receipt:** Candidate `41d6204648e4115ab197507d1a22f6d5c7f3e784` is already pushed and verified on `origin/qualification/wp-0005-harness`; evidence `6dc2d01c84da99d751994cce00a2c82df053c215` and this canonical `/010` report are pushed immediately after commit and verified via `git ls-remote origin refs/heads/qualification/wp-0005-harness`. No runtime installation, model download, or GPU stage is released by this publication.
