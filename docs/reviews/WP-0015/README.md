# WP-0015 independent replay preparation (eld-rd-reviewer)

Working notes for reservation 006. This is **not** the canonical report. No held-out input, key, GPU, model call or native trial output was accessed. Author: eld-rd-reviewer, Claude Code session on Opus 5.5 (`claude-opus-5-5`); applied effort is not exposed.

## Frozen inputs merged into `review/wp-0015-architecture`

| Item | Commit | Check |
| --- | --- | --- |
| Astra harness and position | `82206bc4b77654010ac02364adaaf589d1f36780` | `docs/research/WP-0015/astra` tree `ec0df9dd…` is identical at 82206bc, the review HEAD, `origin/research/wp-0015-astra` and `origin/coordination/bootstrap`. The WP-0014 probe (`f6738e9d…`) and `workers/local_ocr` (`dc9b69e4…`) trees are unchanged. |
| Custodian | `3db4b71fd6ef5f947eadd4d64b63108d8b1650e2` (custody source `7598bf4155452c4a1294b7421595009d39ea1bc9`) | After the freeze, 3db4b71 only adds `verification.json` and report 003. |
| Decision rules | `592a657645765ee458e7e19a105a22c4a4b41bfe:docs/coordination/WP-0015/analysis-plan.md` | Read only. Not merged. |
| Carbon position | `origin/research/wp-0015-carbon` (`2833673`) | Read only. Not merged. Carbon has no runnable mode in the frozen launcher. |

## Helpers (reviewer-authored, standard library only)

| File | Purpose |
| --- | --- |
| `precheck.py` | Pins dev, commitment, ciphertext and warm-up identities. Probes the frozen `score.py` and the native adapter `formats.native_page` with fabricated predictions. |
| `make_plans.py` | Writes immutable alternating-order plans (`ab`, `ba`, or `ab, ba, ba, ab`) for the frozen `launch.py`. Each plan has a warm-up on both engines, then the measured document, with the source SHA and every RGB pin. It refuses any PDF that differs from its commitment, and any path under scoring or custody. It prints exact commands. |
| `analyze.py` | Stage 1, after predictions: verifies the source, plan, process, durable files, RGB pins, page and window coverage, native token/page/stop reassembly, clocks, paired savings in both orders, control spread and native token parity. Stage 2, after the separate scoring release: checks the truth and rasters commitments and that the pins equal the released rasters. It then runs the frozen `score.py` in a separate process: Windows against its same-process native control, and the control repeat against the first control. It also adds reviewer-only diagnostics. |
| `selftest.py` | Fabricated run trees in the `trial.py` layout. A clean tree verifies. A tampered RGB, broken token reassembly, an edited prediction and reordered pages are each caught. |

## Executed CPU checks

The session cannot execute the Q0 interpreter: every invocation was auto-denied with no approval surface. The scorer and helpers ran instead with system CPython 3.12.10, which has no torch, numpy, PIL or pypdfium2.

| Command | Result |
| --- | --- |
| `python -B docs/evaluation/WP-0015/check_score.py` | 26/26 custodian controls pass. |
| `python -B docs/reviews/WP-0015/precheck.py --out docs/reviews/WP-0015/evidence/precheck-03.json` | Identity checks: all true. Probe results are below. |
| `python -B docs/reviews/WP-0015/make_plans.py --family boundary … --pairs 2 --prefix dryrun-boundary` | Four plans under `C:/Users/jackg/eLedgerCare-Speed/WP-0015/review/dryrun-plans-dev-boundary/`. The four page objects agree with the manifest. Public dev only, never launched. |
| `python -B docs/reviews/WP-0015/selftest.py <review>/selftest-02` | All assertions pass. |

**Not run:** `audit.py`, `development.py` rebuild, `prepare.py` and any PDFium rendering or RGB recomputation (no Q0 or PDFium in this session); the Windows recognizer; and any GPU or model step. The custodian's rebuild and raster records are matched by hash only.

## Findings that may affect acceptance

1. **Fabricated or duplicated critical values pass every frozen gate at 60-page scale.** The probes use public dev pages replicated to an A-like denominator of 7,949 characters and 294 cells, close to A's published 8,821 and 300.
   - S3: an extra, unprinted "Net total USD 57.33" off any printed line gives ΔCER +0.0025 and 0 critical errors. It passes both the quality budget and the unattended gate.
   - S4: an appended duplicate of a critical row (a double-counted amount) gives Δcell exactly −0.020, which the inclusive rule accepts, and passes as well. At A's 300 cells it would be −0.0196.
   - On H (570 characters, 20 cells) and the dev pages, only CER/cell dilution rejects them; no critical check fires.
   - Critical scoring checks only whether expected values are present at expected places. It never penalises an unsupported or surplus value.
   - My diagnostic (per-page multiset surplus of digit-bearing tokens, plus values printed on another page) catches S2–S5. I will report it separately; it does not change frozen outcomes.
2. **Flagged errors satisfy the unattended gate** (`score.py:285`). In S1, 24 of 24 critical values are wrong but flagged, and the gate is true. Both frozen adapters hard-code `flagged=False`, so this is not exploitable today. Flag counts will still be reported.
3. **`wrong_source` is structurally zero for this harness.** `trial.py:69` stamps `source_sha256` and `page` from request position, not from evidence.
   - Swapped page contents (S5) surface only as critical errors.
   - Page 4's critical values copied onto blank page 3 (S2) leave `packet_complete` and the unattended gate true, because `ink_on_blank` is non-blocking (`score.py:250`).
   - Provenance therefore has to come from raw RGB pins, `<PAGE>` token boundaries, window coverage and content alignment, which `analyze.py` checks.
4. **Native critical errors conflate misreading with block granularity.** In N2, exact text inside one multi-line paragraph block gives 2 of 2 unflagged critical errors (observed `null`), because the span is too tall for `on_line`.
   - Windows word boxes localise; native blocks may not. Critical counts are therefore asymmetric between arms.
   - `analyze.py` splits out "value present in page text but unlocalised".
5. **Cell accuracy cannot validate native geometry.** The adapter follows upstream's convention of 999 units over the original image (`modeling_unlimitedocr.py:161-165`), although the model input is `ImageOps.pad`-ed to a square (`:561`).
   - If the convention were the padded square, table IoU would be 0.742, still matched, and cells would still score 1.0. Only one prose critical moves (N3c).
   - Per-table IoU is reported.
6. **Ordering and process limits.**
   - A first-document failure re-raises (`trial.py:65,122`), so the rest of that plan, including the opposite arm, never runs, leaving an unmatched pair.
   - The native first page publishes only with its 3-page window, so first-page times are not comparable to the 1-page Windows window.
   - RGB pins are optional in `launch.py:68`. My plans always include them.
   - H's pins are in its scoring bundle, so the custodian must supply H's RGB digest list (digests only) before inference. Stage 2 re-checks it against the released `rasters.json`.
7. **Runtime guards.** During a run, `launch.py:90` enforces only the time and 20 GiB disk floors. VRAM and temperature are sampled every 5 s (`:93`) but not enforced; VRAM is checked only at admission.
8. **Quality noise in the control is unmeasured by the plan.** The changed-output budget compares against one control. If native repeats are not token-identical (Carbon cites earlier warm ±1 box shifts), the deltas include control variation. `analyze.py` reports cross-process native token parity and a control-vs-control score.

## Can decode profiling support causal claims?

Not with the frozen harness, and not by profiling alone.

**What the harness records.** `native.py` records stage marks:
- build_inputs, vision with `cuda.synchronize`, and generate;
- the first and last `TextStreamer.put`, one per generated token and never the prompt (upstream `:1183-1184`), so TTFT is valid;
- forward counts, upstream `time`/`prefill_time`, and Triton/dense counts.

This supports TTFT, decode wall time, mean tokens/s and forwards per token. It has no per-token timestamps or per-operation attribution.

**Why Carbon's attribution is not measured.** Carbon's ">97% sync/MoE-loop/FP32-upcast" comes from code reading plus a bandwidth roofline. The roofline shows the step is far from weight-bandwidth bound. It cannot divide the remainder among host synchronisation, launch latency, tiny-GEMV inefficiency and O(S) FP32 attention.

**Why profiling misattributes here.** Each step already blocks on `int(torch.argmax(logits))` (`:1176`). A profiler under asynchronous CUDA charges drained queued GPU work to whichever sync point waits, so "time in `.cpu()`" is not the cost of that sync. Adding events or synchronisation also changes the pipeline.

**What causal support needs.** One mechanism changed at a time, with token-identical output, measured in alternating fresh processes, with the saving larger than the control spread. Candidate single changes:
- the per-token streamer that prints to `stdout.txt`;
- the CPU n-gram guard (`:1169`);
- device-side MoE routing.

Removing the streamer also removes the harness's token marks, so instrumentation would no longer match. The frozen launcher has only `native` and `windows` modes, so Carbon's engine has no matched measurement in this packet.

**The O(S) claim.** Only weak evidence is available: per-window tokens/s for H's 3-page window against its 1-page window, confounded by content.

## Replay route (awaiting separate releases)

1. **Input release only.** The custodian runs `release.ps1 -Family H -Stage input` to a new directory under `C:/Users/jackg/eLedgerCare-Speed/WP-0015/review/inputs/H`, and separately supplies H's four RGB digests as `{"rgb_sha256": [...]}`.
2. **Generate plans** (CPU):
   `python -B docs/reviews/WP-0015/make_plans.py --family H --pdf C:/Users/jackg/eLedgerCare-Speed/WP-0015/review/inputs/H/source.pdf --rgb-pins <pins.json> --out C:/Users/jackg/eLedgerCare-Speed/WP-0015/review/plans-H --pairs 1|2 --seconds <released> --lease <released>`
3. **Launch each printed command sequentially** under the sole lease. Each is a separate process; `ab` is native first, `ba` is Windows first. The form is:
   `& 'C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe' -I -B '<worktree>/docs/research/WP-0015/astra/launch.py' --source 82206bc4b77654010ac02364adaaf589d1f36780 --plan '<plan>' --sha256 <plan sha> --owner review --run h-rN-<order> --seconds <released> --lease <released> --min-vram-mib 12000`
   Run directories are `C:/Users/jackg/eLedgerCare-Speed/WP-0015/review/runs/h-rN-<order>`, which are immutable.
4. **Stage 1:** `python -B docs/reviews/WP-0015/analyze.py --family H --runs <run dirs> --pins <pins.json> --out <new>`. Commit the predictions' hashes and the stage 1 output before requesting the key.
5. **Scoring release, then stage 2:** add `--truth <released>/truth.json --rasters <released>/rasters.json` with a new `--out`.

**Estimate per process:** cold load, plus about 7 s of native warm-up, plus about 139 s for H native (the custodian proxy), plus Windows time, which is unmeasured. Under 5 minutes is likely. One pair is about 10 minutes; two pairs are about 20 minutes. I suggest `--seconds 900` per process, but the actual value is the coordinator's to bind.
