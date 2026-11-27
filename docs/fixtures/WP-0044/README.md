# WP-0044 fixtures and sealed oracle commitment

Owner: eld-fixture-claude (Claude Code, requested and actual model claude-opus-5-5; effort not exposed beyond the INDEX request "high"). These fixtures use only the Python standard library and were written against CPython 3.12.10. No process launch, model, OCR, GPU, network or candidate code is involved. Nothing in this directory came from eld-owner-probe or eld-rd-reviewer material.

This directory holds the **public** half of the challenge. The exact oracle code and its expected results for all 33 rows stay **sealed** outside Git, under the owner's private WP-0044 scratch directory. `oracle-commitment.json`, committed separately after these fixtures, records their SHA-256 digests. Each sealed file embeds a random 256-bit nonce, so a guessed expectation cannot be confirmed against the digest. The files will be opened only on coordinator authorization, after both implementations freeze and their blind results are committed.

| File | Role |
| --- | --- |
| `build_fixtures.py` | Deterministic generator. It writes `inputs/` and `manifest.json`. `--check` re-derives every byte and reports any mismatched or unexpected file. |
| `inputs/constructed/<sha16>.json` | 16 blinded constructed records (`wp0044.record.v1`). Each file is named by the first 16 hex characters of its own SHA-256. |
| `inputs/math/<sha16>.json` | 4 mathematical-control inputs (`wp0044.margin.v1`, `wp0044.fp32.v1`, `wp0044.linked.v1`). |
| `manifest.json` | Versioned manifest `wp0044.fixtures.v1`. It lists all 33 scheduled rows in schedule order with interface and input path/SHA-256/bytes. Live rows carry their construction text and payload. Archive rows carry the pinned path, digest and commit. It also binds the generator digest and every file digest. |
| `compare.py` | Joins frozen expectations with one route's observations by row ID. It reports per-field agreement and q = matched/33, and it never computes a verdict. Absent, duplicated or incomplete rows fail and stay in the denominator. |
| `oracle-commitment.json` | (Separate later commit.) SHA-256 and size of the sealed oracle, its self-test and its expected JSON. |

## Commands

```
python -I build_fixtures.py            # regenerate (deterministic)
python -I build_fixtures.py --check    # verify all 21 generated files byte-for-byte
python -I compare.py --expected <expected.json> --observed <route.json> --manifest manifest.json --out <cmp.json>
# at opening only:
python -I oracle.py --fixtures docs/fixtures/WP-0044 --repo <worktree> --out expected.json
```

## Constructed record interface (`wp0044.record.v1`)

UTF-8 JSON object `{schema, expected, observed, sources}`. The record contains no case ID, injection label or expectation. The row-to-file mapping exists only in `manifest.json`.

- `expected` is a flat map from all 27 canonical keys to JSON values. It holds the frozen contract value or relation for that record: `L.image, I.image, E.launcher, E.parent, E.order, E.instance, E.job, A.script, A.args, C.pyvenv, C.include_system, C.pth, C.sitecustomize, C.PYTHONHOME, C.PYTHONPATH, C.PYTHONSAFEPATH, C.CUBLAS_WORKSPACE_CONFIG, C.CUDA_VISIBLE_DEVICES, C.prefix, C.modules, B.writer, B.seal, B.protection, B.direct, B.origin, B.members, content.bytes`.
- `observed` is a flat map over the same keys. **Omission means unobserved.** `null` is a witnessed absence (for example an unset variable). `""` and `[]` are witnessed empty values. Equality is type-strict JSON equality: `false` ≠ `0`, list order is significant, and object member order is not.
- `sources` maps each *observed* key to `{method, seq}`. `method` names the observation method. `seq` is an opaque ordinal in actual observation order, and its absolute values differ between records. A `sources` entry is a description and never substitutes for an observed value.
- Identities are compared by relationship inside one record. Opaque process keys `{pid, created}` (creation FILETIME), file identities `{volume_serial, file_index}`, arm IDs and receipt digests are regenerated per record. `E.parent` is expected to equal the observed launcher instance. `E.instance` is the interpreter's creation-scoped key, and a different `created` under the same `pid` is a different instance. `B.writer` and `B.members` are sorted lists (writers by `pid, created`; members by `name`).
- All digests are synthetic (`sha256:` of fixed labels). All paths are placeholders under `X:\wp0044\…`, one of them non-ASCII. No host path appears.

## Mathematical inputs

- `wp0044.margin.v1`: `queries[]` of `{scores:[[token_id, decimal]], delta:[[token_id, decimal]]}` with `tie_rule: first_index` (ties go to the smallest token ID). Values are exact decimals.
- `wp0044.fp32.v1`: `queries[]` of `{words_le:[8-hex FP32 little-endian words]}`.
- `wp0044.linked.v1`: scalar-cache recurrence. Z(q) = base + q·slope over `support`, starting at `q0`. After each step the stock path writes `stock_write` and the private path writes `private_write`; the run lasts `steps` steps.

Archive rows read the pinned `docs/coordination/WP-0043/native-evidence.json` (SHA-256 `66eb8bd4…42218bb`, byte-identical in commit 13753c13 and inside the pinned reference-checks.zip).

## Expected row shape (`wp0044.expected.v1`, values sealed)

Provenance rows (live and constructed) carry these fields:

- `coordinates{L,I,E,A,C,B}`, `custody`, `joint` and `content`, each M/U/P with M < U < P.
- `origin{class, unresolved[]}`, where class ∈ {verified, wrong_origin, integrity, unresolved}.
- `conflicts[]` of `{key, coordinate, phase, subtype, source}`.
- `missing[]` of `{key, coordinate, phase, subtype, source}`.
- `earliest{kind, phase, keys[]}`, or `null`.
- `extras{}`.

Phases are launch < image < edge < command < configuration < writer < seal < acquisition < score. Archive and mathematical rows carry `result`. The subtype and source strings come from the oracle's own vocabulary, and both route outputs will need a separately versioned, schema-only crosswalk at opening. The crosswalk cannot change any prediction.

## Freeze protocol

1. Commit A freezes this directory: generator, 20 input files, manifest, comparator and README. The oracle was written after the generator reached its final form. It was first executed against exactly these input and manifest bytes, and neither the generator nor any input changed after any oracle execution.
2. Commit B adds `oracle-commitment.json`, which binds the sealed oracle, self-test and expected-JSON digests to commit A's manifest digest. It is committed before any candidate exposure.
3. The sealed files open only on coordinator authorization, after both implementations freeze and their blind results are committed. At opening, rerunning the oracle on commit A must reproduce the committed expected-JSON digest byte for byte.

## Coverage matrix and limits

| Family | Native live rows | Constructed rows | Native obligation **not** exercised live |
| --- | --- | --- | --- |
| W1 genuine arms | W1.A, W1.B | none | none |
| W2 anchor / direct edge | W2.other | W2.helper | helper process inside the direct edge |
| W3 parent / order / reuse | none | W3.missing, W3.late_missing, W3.reuse | missing parent receipt, child creation after launcher exit, numeric PID reuse |
| W4 images / replacement | W4.denied | W4.bad_I, W4.no_I, W4.bad_L | swap of the loaded interpreter image, removed live image association, launcher digest mismatch |
| W5 command / configuration | none | W5.args, W5.script, W5.config, W5.empty, W5.unobserved | any live command or configuration variation |
| W6 containment / writer | none | W6.escape, W6.writer | job escape, same-job sibling with an unauthorized writable handle |
| B1–B5 output custody | B1.original, B2.other, B3.copy, B4.invalid, B4.unavailable, B5.reopen | B5.member_missing, B5.writer_missing | differing sealed member, unexpected writer |
| Archive | none | none | 3 read-only rows: archive.gaps, archive.support, archive.verdict |
| Mathematical | none | none | 4 rows: math.shift, math.tie, math.signed_zero, math.linked |

The per-route totals are 10 native, 16 constructed, 3 archive and 4 mathematical rows, 33 in all.

Limits:

- Constructed records test the scorer at its normal input only. They cannot satisfy a native Windows obligation, and the native column above lists every obligation that remains untested live.
- The live-row expectations come from ideal-observer scenario models inside the sealed oracle. They bind the diagnosis (coordinates, verdicts, keys, subtypes, phases and sources), not run-specific identifiers or timing. The oracle records the key-level interpretation choices it makes for live rows, and those choices are disclosed at opening. An implementation that differs on one of them goes to coordinator reconciliation; it is not silently corrected.
- `W5.config` models one physical edit of pyvenv.cfg, so the record changes both `C.include_system` and the `C.pyvenv` digest. `B5.member_missing` adds an unexpected sealed member and leaves the primary payload unchanged.
- The mathematical rows check exact arithmetic on constructed scores. They do not run the reader, and they estimate neither a replay or recovery rate nor any fault distribution.
