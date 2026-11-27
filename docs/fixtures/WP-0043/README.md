# WP-0043 CPU challenge suite and independent oracle

Owner: eld-fixture-claude (Claude Code session 1177d67f-9d36-4f5c-b116-177da65cdc8d, launch request claude-opus-5-5/high). Standard-library Python only (written against 3.12.10). There is no model, tensor library, CUDA, network or candidate code.

The suite asks whether a stock-observer recorder and offline scorer can pass a wrong phase, support, ownership or continuation. Every case is a starting scenario plus an injection schedule. Cases never contain the expected answer. Expectations come from a separately written oracle and are frozen in a later commit, before any candidate output is seen.

| File | Role |
| --- | --- |
| `build_fixtures.py` | Generator and **reference recorder**. A CPU stock analogue mirrors the native decode step (modeling_unlimitedocr.py 1166-1182, guards 583-605 and 608-623), working in place on one little-endian FP32 buffer per step. It writes everything under `generated/`. |
| `oracle.py` | **Independent oracle**. It shares no code with the generator and uses bit-pattern words, set-algebra masks and replay from the written contract. `expect` writes `expected/`; `score` applies its evidence-only reference scorer to any evidence bundle. |
| `compare.py` | Joins frozen expectations with machine observations on `run_id`/`case_id`. It never computes verdicts. |
| `generated/` | `cases.jsonl`, `contracts/`, `evidence/`, `inputs/` (raw ground truth), `blobs/` (captured bytes) and `manifest.json` (bytes + SHA-256 of every file). |
| `expected/` | `expected.jsonl` (one oracle record per case) and `facts.json` (global semantic facts and the source binding). This directory is frozen in its own commit. |

## Commands

```
python -I build_fixtures.py                 # regenerate generated/ (deterministic)
python -I build_fixtures.py --check         # verify generated/ against manifest.json
python -I oracle.py expect --native-source <path>/modeling_unlimitedocr.py
python -I oracle.py score --contract generated/contracts/<run>.json --evidence <evidence.json> --blobs <blob dir>
python -I compare.py --expected expected/expected.jsonl --observed <observations.jsonl> \
       --cases generated/cases.jsonl --out <comparison.jsonl> --summary <summary.json>
```

`--native-source` is optional. When given, the file is read as bytes and hashed, never imported.

## Freeze protocol

1. Commit A freezes `build_fixtures.py`, `oracle.py`, `compare.py`, this README and all of `generated/`. Before that commit the oracle has never been executed.
2. `oracle.py expect` is run once on commit A and its outputs are committed as commit B, before any candidate exposure. If the first execution exposes an oracle defect, the fix is a separate visible commit A′ made before B, and the run is repeated.
3. Integration (driver/adapter for the candidate's normal recorder and scorer CLI) starts only after B. Any later schema-only translation is generic, separately versioned, and cannot change predictions.

## Interchange schema (v1)

### Case (`generated/cases.jsonl`, `wp0043.case.v1`)
`case_id` (stable key), `fixture`, `subcase`, `title`, `run_id` (opaque, `r` + 12 hex of SHA-256 of the case id), `contract_path`, `reference_evidence_path`, `scenario`, `injection`.

`scenario` contains:
- `vocab`: `{"kind":"dense","size":N}` or `{"kind":"sparse","ids":[sorted IDs]}`.
- `eos_id`, `page_id` (1, 128827), `prompt_ids`, `page_count_guard`. Expected pages e = count of `page_id` in the prompt, as in native line 1141.
- `max_page_tokens` c, `ngram` `{order, window, whitelist}`.
- `generated_prefix` H0: IDs emitted by earlier, unobserved native steps.
- `initial_guard_state`: native replay of one guard call per earlier step j with history H0[:j].
- `max_new_tokens`, `rows`: analogue steps that are observed rows.
- `raw`: one object per step with `default`, `values` (ID → FP32 literal), `input` (path), `sha256`, `nbytes`. The raw vector is ground truth and is never a scorer input.

Analogue step s operates on history H0 ‖ emitted[:s], and n = |H0| + s. Each step runs head result, then no-repeat guard (when order > 0), then page guard (when e > 0), then first-index greedy argmax. EOS is tested before append. The run ends with `stop` (EOS) or `length` (budget). `max_length` is not modelled.

### Contract (`generated/contracts/<run>.json`, `wp0043.contract.v1`) — scorer input
The scenario projection without raw values, names or injections. It also carries `dtype`, `byteorder`, `sentinel_le` (`000080ff`), `phase_map` `{C0_raw: PRE_REP, C1_post_rep: POST_REP, C2_post_page: POST_PAGE}` and `required_origin` `native_copy`.

### Evidence (`generated/evidence/<run>.json`, `wp0043.evidence.v1`) — scorer input
`run_id`, `contract_sha256` (SHA-256 of the contract file bytes), and `arms.untouched.public` and `arms.observed.public`, each `{token_ids (H0 included), finish_reason, terminal_observed}`. `arms.observed.rows[]` holds `{row, step, history_len, consumed_id, entry.guard_state{marker_cum,scanned,page_len}, captures{C0_raw,C1_post_rep,C2_post_page}, guard_calls{ngram,page}, selected_id, exit{guard_state, appended, gen_len_after, finish}}`.

A capture record holds `{bc_offset, event_seq, copy_id, origin, dtype, byteorder, declared_len, complete, blob, nbytes}`. `blob` names `blobs/<sha256>.bin`, the vector in the vocabulary's compact order. Any field may be absent; absence is evidence of missingness, never a default.

### Byte offsets
For token ID t at compact index i and byte lane λ (0 = least significant byte), the **dense token-ID offset** is 4t+λ. That is the logical native address in a full 129,280-entry vector. The **compact physical offset** is 4i+λ, the actual offset in the blob file. For dense vocabularies the two agree. The sparse `ids` list is the index map.

### Observation (`wp0043.observation.v1`) — scorer output, the comparison input
`run_id`, `verdict` (M/U/P), `first`, `conflicts[]`, `missing[]` and optional `row_verdicts`, `counts`, `scorer`. A key is `{row, step, phase, object, check, slot_id, phase_from, row_from, step_from, detail}`. Causal phase order within a step is CFG < ROW < B_entry < C0_raw < C1_post_rep < C2_post_page < Y_select < D_exit < PUB < TERM. Steps order first. A pairwise conflict, such as duplicate copy IDs or non-increasing `event_seq`, is the interval `phase_from..phase`.

### Injection operations
Execution of the observed arm: `copy_schedule` (ordered `R <phase> *|[ids]`, `W_N` and `W_P` events, so a copy reads the live buffer at that point), `guard_state_override` (record `actual` or `omit_fields`), `guard_reinvoke`, `ngram_window_delta`, `ngram_include_prompt`, `select_rule`, `perturb_raw`, `max_new_tokens` and `interrupt`. Recorder output: `drop`, `truncate`, `set_word`, `strip_provenance`, `label`, `swap` (`move_with_bytes` / `stay_with_phase` / `strip`), `duplicate` and `recompute` (`honest` / `forged` labels).

## Case catalogue

| Family | Cases | Mechanism |
| --- | --- | --- |
| F0 pristine | active_sparse, active_dense | Companion p.6 history (PAGE)‖p‖(7)‖p with r₁=8, r₇=9, r₈=4. Dense is native size 129,280. |
| F1 active first guard | pristine, late_raw, dense_late_raw, all_late, recompute_honest, recompute_forged | Hook timing, and single capture with offline synthesis. |
| F2 forced but forbidden | valid_force, forced_banned | Page cap c=34 forces PAGE; p‖PAGE‖p bans it (reachable history). |
| F3 tie/zero/NaN | tie_pass, tie_last, zero_flip, nan_masked | Selection failure vs byte-preservation failure; NaN masked by the repetition guard. |
| F4 phase/completeness | pristine, a, b, c×2, d, e, f, g, h, i, j | Memo 4a/4b on equal bytes, undetectable swaps, missing, interrupted, false-complete, missing+conflict. |
| F5 continuation | pristine, later_id, terminal_reason, interrupt_after_field, interrupt_with_conflict, interrupt_in_field | F07-shaped: five field rows (6, 1449, 16, 1328, 128822), two later PAGE markers, then EOS. |
| F6 ownership | owned, alias_end, zN_alias_late, torn_raw | Same-buffer alias races on a controlled CPU schedule. |
| F7a cursor | valid, reset_recorded, reset_unrecorded, reinvoke_idempotent | Two observed steps, c=4, e=2. |
| F7b window | out, in, prompt, out_window_minus1, in_window_plus1, prompt_included | n=1060, w=1024, a=36. |
| F7c specials | pos_inf_raw, neg_zero_pass, neg_zero_canonicalised, neg_zero_pick_last | +inf raw word and a winning −0.0 tie. |

## Limits

These are CPU constructions. They exercise ordering *models*, not CUDA streams, allocators or native kernels. No GPU measurement exists or is claimed here. The analogue omits head arithmetic, caches, routing and B/D cache payloads; the guard state is the only entry/exit state represented. NaN reaching selection is out of scope because the torch tie rule with NaN is unpinned here. Some prompt IDs (PAGE markers in F4/F7c) are outside the compact score vocabulary. They only set e.
