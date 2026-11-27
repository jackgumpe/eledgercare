# WP-0043 integration bridge (wire v1)

Owner: eld-fixture-claude. These files exercise the frozen suite (freeze B `3f7a53cbf971eb8434507ef3622eb5d089c5de57`) through the candidate's normal CPU entries, `stock.py capture` and `stock.py score` (wire v1, candidate release `6101a75dc372fc6e2944b004343fa278d5d98907`). Nothing in `generated/`, `expected/`, `compare.py` or `oracle.py` changes.

| File | Role |
| --- | --- |
| `bridge.py plan` | Converts each frozen scenario and injection into a wire CASE/CONTRACT, or an explicit rejection naming the needed neutral op. It reads `generated/` only and never `expected/`. Per-stage live words for the copy-schedule mapping come from the frozen generator `build_fixtures.py`. |
| `bridge.py run` | Runs the candidate's normal CLI serially, `python -B <export>/stock.py capture` then `score`, from a Git-object export of the released `docs/research/WP-0043/*` placed in private scratch. It records argv, exit status, stdout/stderr bytes and digests. |
| `bridge.py fidelity` | Compares the candidate's captured bytes, selected ID and page states with the frozen reference evidence. This shows what the transport delivered, independent of any verdict. |
| `semantic_compare.py` | v2 comparison, run only after results exist. It matches individual conflicts and missing atoms through `crosswalk-v1.json`, checks words, lanes and dense/compact offsets, and classifies every difference. |
| `plan-transport.jsonl` | The frozen plan: wire ops, substitutions, notes and CASE/CONTRACT digests per case. |

## Mapping rules (generic, by injection type)

- **Copy schedule.** A uniform read stage becomes `capture_at` an earlier or later real cut. A later-suffix split becomes `torn`. Otherwise the bridge uses a byte-equivalent prefix/suffix with the fewest slots moved to another stage, and discloses it. If none exists, the case is rejected.
  - Copies stay owned, at real instruction cuts with genuine ledger events. The bridge never sets witness or phase flags.
- **Recorder edits.**
  - `drop`, `truncate` (4·words), `strip_provenance`→`unwitness`, `duplicate` and swap-with-bytes→`swap` map directly.
  - A swap of byte-identical records that keeps labels is the identity.
  - A C2 word edit becomes a live `write` before the final copy, only if selection is unchanged.
  - A label edit is accepted only when it restates the genuine ledger count.
  - Honest recompute becomes `recompute` with ancestry `absent`. Forged recompute is rejected by design.
- **Execution.** `cursor` (+`omit_state`), `reenter_page`, `ngram_start` (same sign: start = n − w + δ), `include_prompt`, `lastmax`.
  - Post-field perturbation, budget and interruption appear only through the observed document.
  - Interruption before a scheduled row is rejected (needs `omit_row`).
- **Documents.** Both public documents are fixture-supplied frozen reference trajectories: untouched goes into `contract.document`, observed into `CASE.document`. The candidate CPU capture copies them; it does **not** execute any continuation. A native run is a separate, unreleased device arm.
- **Visibility.** The candidate scorer also receives `contract.raw_words` (true raw scores) and genuine copy-event receipts. The frozen oracle had neither, so some candidate detections are visibility differences, not disagreements. Fully forged receipts cannot be expressed by the candidate and cannot be seen by the oracle.

## Byte-lane correction carried in v2

The frozen expected rows list `dense_token_offset_candidates` for non-finite raw words. Those are the exponent lanes (2 or 3) where any finite word *must* differ. They do not bound the *first* differing lane, which against an unknown finite word can be any of 0–3 (dense 4·id … 4·id+3). v1 `compare.py` read them as first-lane candidates. v2 instead checks candidate lanes against the frozen ground-truth word pair when one exists, and otherwise marks the detail unchecked. Freeze B is unchanged.

## Commands (decisive run)

```
python -I bridge/bridge.py plan --out <scratch>/run
python -I bridge/bridge.py run --plan <scratch>/run --candidate-dir <scratch>/cand-<sha>
python -I bridge/bridge.py fidelity --plan <scratch>/run
python -I bridge/semantic_compare.py --expected expected/expected.jsonl --plan <scratch>/run \
       --out <scratch>/run/semantic.jsonl --summary <scratch>/run/semantic-summary.json
```
