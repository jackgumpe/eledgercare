# WP-0045 blind fixtures and sealed-oracle commitment

Owner: eld-fixture-claude. Session: Claude Code, model `claude-opus-5-5`. INDEX requested effort "high"; the applied effort is not exposed. The fixtures use only the Python standard library and were checked with CPython 3.12.10 using `-I`. They involve no process launch, Windows trial, model, OCR, device, network access or candidate material. Nothing here came from eld-owner-probe, eld-depth-author or eld-rd-reviewer. The Gemini written review was read only as an advisory input.

This directory is the **public** half of the challenge. The executable oracle, its self-test and the full expected rows for all 32 scheduled IDs are **sealed** outside Git, in the owner's private `eLedgerCare-Speed/WP-0045/eld-fixture-claude/oracle/` directory. `oracle-commitment.json` is added in a separate later commit and binds their SHA-256 digests. Opening requires eld-coordinator authorization, and only after the blind author and reviewer results have been committed.

## Files

| File | Role |
| --- | --- |
| `build_fixtures.py` | Deterministic generator for `inputs/` and `manifest.json`. `--check` re-derives every byte and reports any mismatched or unexpected file. |
| `inputs/<sha16>.json` | 32 label-free inputs. Each name is the first 16 hex digits of the file's own SHA-256. No file contains a case ID, label, verdict or expected value. |
| `manifest.json` | `wp0045.fixtures.v1`. Lists the 32 rows in `schedule.json` order. Each row has `id`, `family`, `clause`, `repetitions`, and `input{path, sha256, bytes}`. The manifest also binds the generator digest and records the file inventory. |
| `compare.py` | Exact outer join on scheduled ID between the opened expected rows and one participant's returned rows. It computes q separately for Q1 (12), A1 (6), A2 (6) and C1 (8). It holds no expectations. |
| `oracle-commitment.json` | (Separate later commit.) Digests of the sealed oracle, its self-test and the expected manifest. |

## Row inventory (32)

| Family | IDs | Input |
| --- | --- | --- |
| Q1.live | N.A, N.B | Native external request `{"clause":"Q1","selection":0 or 1,"payload_hex":"4630370a"}` |
| Q1.constructed | Q.other_caller, Q.no_caller, Q.other_writer, Q.no_writer, Q.mixed, Q.other_original, Q.detached, Q.bad_seal, Q.unordered | `{"expected","observed","evidence"}` per wire.md |
| Q1.archive | H.old | `{"clause":"archive","packet":"WP-0044"}` |
| A1 | stock, duplicate_first, duplicate_second_private, duplicate_second_commit, literal, invalid | wire.md A1 object |
| A2 | clean, masked_nan, raw_inf, illegal_repeat, signed_zero, empty | wire.md A2 object |
| C1 | exact, uninformative, informative, duplicate, impossible, budget, threshold, tie | wire.md C1 object (one exact, seven noisy) |

The harness attaches the scheduled `id`, the `clause` (the manifest `clause` column) and the input SHA-256. A participant returns one unwrapped projected row per ID, plus a separate file that maps each returned ID to its verified input digest.

## Fixed encodings

- **Inputs.** Each file is UTF-8 `json.dumps(obj, ensure_ascii=False, separators=(",", ":"))` with the constructed member order, followed by one LF. Values are integers, strings, booleans, null, arrays and objects. Floats never appear. Rationals are canonical reduced strings (`"9/10"`, `"1"`). FP32 values are 8 lowercase hex digits in the wire's big-endian integer form.
- **Expected rows (sealed).** Each file holds one unwrapped row exactly as wire.md specifies: canonical JSON with `sort_keys`, separators `(",", ":")`, `ensure_ascii=False`, UTF-8 and one LF. The sealed `expected-manifest.json` maps every ID to `{path, sha256, bytes}`, embeds a random 256-bit nonce, and binds this directory's `manifest.json` digest. Only the nonce-bearing expected manifest and the sealed sources are committed publicly. Publishing per-row digests would let anyone confirm a guessed short row.
- **Comparison.** Comparison uses canonical typed JSON equality: `true` ≠ `1`, list order is significant, object member order is not, and a missing key differs from `null`.

## Frozen construction assumptions (inputs)

- C1. Every constructed Q1 record carries all 15 schedule atoms in `expected` and `evidence`. A witnessed atom has `{source: <schedule token>, at: <schedule checkpoint>}`. An atom omitted from `observed` whose prescribed cut was witnessed keeps that same token and checkpoint. Only an unwitnessed cut uses `{"source":"unobserved","at":null}`.
- C2. Identities are synthetic and regenerated for each record. A process identity is `{pid, created}`, where `created` is a creation FILETIME. A differing caller keeps the same numeric PID and has a different creation time. Paths are placeholders under `X:\wp0045\…`, one of them non-ASCII. Digests are synthetic.
- C3. In every constructed record, `observed` presents the nested members of `L.image`, `A.command` and `C.runtime` in a different order from `expected` while keeping equal values. `C.runtime` contains witnessed `null` values and a witnessed empty string.
- C4. Variations follow `schedule.json` `constructed_variations` exactly. A differing writer means the authorized writer list plus one unallowlisted writable alias. A differing origin means a different authenticated original with equal bytes. A differing seal changes only the tag.
- C5. A2 arrays are complete and the index lists are sorted, unique, valid and non-overlapping. Raw arrays deliberately include nonfinite words at masked and unmasked cells. A1 and C1 inputs stay inside the wire's finite, well-formed domain.

## Frozen interpretation choices on points the wire leaves silent

These were fixed before any candidate exposure and are applied by the sealed oracle. A differing reading goes to coordinator reconciliation. It is not silently translated.

- I1. `content.bytes` appears in `values`, `conflicts`/`missing`, `reason`, `first` and `source`. It is excluded from `coordinates`, `custody` and `status`.
- I2. `reason` and `first` range over every non-P atom.
- I3. For the live genuine rows, the expected row is the ideal compliant observation: every atom witnessed at its schedule cut, carrying its canonical source token and equal to its frozen expectation. Run-specific identifiers never enter the row.
- I4. H.old is derived from the pinned WP-0044 disposition, `git show 7f9281bd:docs/coordination/WP-0044/disposition.json` with SHA-256 `f0a12601…3a14`. It is byte-identical to the copy in Edition02-source.zip.
- I5. A1 duplicate. Both calls use input `a`, stock first. `decoded` retains both readouts in call order. The transition comes from the selected branch only. `commits` is 1 exactly when `commit` is true, and `history` contains the transition exactly then. In literal mode, call `kj` takes the previous call's output.
- I6. A2 conflict pairs use the phase labels `"raw"`, `"repeat"` and `"page"`. They are ordered by phase (raw < repeat < page, which is not lexical order), then by index, and `["support",-1]` comes last. Each nonfinite raw word gives one `["raw",i]`. A masked cell must equal exactly `ff800000`. An unmasked cell must equal, bit for bit, the immediately preceding supplied phase. `allowed` comes from the supplied masks alone, and `first` is the first element of `conflicts`.
- I7. C1 noisy. An observation whose action source is already in `used` is ignored entirely: no posterior change, no budget and no zero-marginal check. Otherwise a zero marginal gives MODEL_CONFLICT. Budget decreases only while it is positive. Decisions follow this order: ACCEPT (largest posterior ≥ threshold), then UNRESOLVED on exhausted budget, then action search. The action search covers actions whose source is unused after marking. An action is informative only when G > 0, and ties go to the smallest `id` regardless of listing order. In exact mode, an empty F gives CONFLICT and a singleton gives IDENTIFIED.

## Commands

```
python -I build_fixtures.py --check
python -I compare.py --manifest manifest.json --expected <opened dir> --observed <returned rows dir> --digests <id-to-digest.json> --out <comparison.json>
# at opening only (sealed files):
python -I oracle.py --fixtures docs/fixtures/WP-0045 --repo <worktree> --out <dir>      # must reproduce expected-manifest.json byte for byte
python -I selftest.py --fixtures docs/fixtures/WP-0045 --reference <Edition02 source dir>
```

## Limits

- Constructed Q1 records test the projection at its normal input only. They cannot satisfy any native Windows obligation. The live expected rows state what an ideal compliant direct-launch observation must yield. They are not predictions that a candidate will qualify.
- The A1, A2 and C1 rows exercise the wire's finite interfaces only. They do not run a model block, native score tensors or a real reader.
- The original 24 vectors and 448 checks stay a separate historical denominator. They are not part of these 32 rows.
