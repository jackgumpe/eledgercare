# WP-0015 / 002: Independent Carbon OCR architecture position for scanned maintenance packets

- Report path: `docs/agent-reports/eld-rd-carbon/WP-0015/002_2026-11-18_research_eld-rd-carbon.md`
- Sequence reservation: [INDEX.md](../../../../INDEX.md#wp-0015-scanned-packet-ocr-architecture-trial) (`WP-0015 / 002`) and [assignment.md](../../../coordination/WP-0015/assignment.md) at `c4d7734d0be6302e667d290698bc671631c71ce9`
- Category: research
- Author / agent ID: `eld-rd-carbon`
- Actual model / effort: Gemini 4 Carbon (High) — requested `high`; underlying backend checkpoint and applied effort beyond client selection are not exposed
- Execution environment: CLI (`Antigravity CLI` on Windows `AMD64`, PowerShell, fresh session `b77309ad-1878-4b25-9ab8-956303d35086`; CPU-only file/hash inspection plus read-only `C:\Users\jackg\eLedgerCare-Q0\WP-0005\venv\Scripts\python.exe -I -B` with `CUDA_VISIBLE_DEVICES=""` for `tokenizers==0.21.4` token-class counting and `.pyi` stub checks; `torch` never imported)
- Published by: `eld-rd-carbon`
- Timestamp: 2026-11-18T03:28:30Z
- Repository / branch: `https://github.com/jackgumpe/eledgercare` (private) / `research/wp-0015-carbon` (isolated worktree `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\speed-carbon`)
- Base revision: `c4d7734d0be6302e667d290698bc671631c71ce9` (derived from product integration base `178ce88b80384fc7def703d9e78769427d9b2528`)
- Deliverable revision: `8acea1ca42aa23ad48a752c642107b9e9f883f47`
- Previous report: none in `WP-0015`
- Related or reviewed reports: [WP-0014 / 003](../../eld-coordinator/WP-0014/003_2026-11-18_verification_eld-coordinator.md), [WP-0014 / 001](../../eld-latency-author/WP-0014/001_2026-11-18_research_eld-latency-author.md), and [WP-0014 / 002](../../eld-latency-reviewer/WP-0014/002_2026-11-18_review_eld-latency-reviewer.md) (at `178ce88b80384fc7def703d9e78769427d9b2528`). `WP-0015 / 001` (`eld-rd-astra`), sealed custody material, and all non-owned branches/worktrees were **not inspected**.
- Status: ready-for-review
- Next owner: `eld-coordinator`

## Summary

Completed `eld-rd-carbon`'s independent CPU-only architectural assessment and published the frozen one-page position at [position.md](../../../research/WP-0015/carbon/position.md) in deliverable commit `8acea1ca42aa23ad48a752c642107b9e9f883f47` prior to committing this report. Directory owner (`eld-rd-carbon`), filename suffix (`eld-rd-carbon`), and author metadata match. This is an **author research position (`ready-for-review`)**, not independent review or live GPU benchmark evidence.

**Upstream authorship disclosure:** An earlier Gemini Carbon web session authored `Baidu OCR Optimization.pdf` (`SHA-256: 6c7f5199fb971eff0953f24c6a00b1af8f7c44c407df9c08c4363938c2d6567b`), while the cloud senior coordinator authored `eLedgerCare-OCR-Architecture-Review.md` (`SHA-256: a6442154f4c65fa0994b7d9b9229cc4d5e1169336dff39f5e17da44f18533099`) and `eLedgerCare-Next-Lane-OCR-Speed-Trial.md` (`SHA-256: 5b46d5317c0e8579ea5015d357a38ea4f73cae622f235a92dd3173a4e27c83eb`). After auditing both briefs against WP-0014's verified resident probe and the pinned `baidu/Unlimited-OCR-2` (`0480966938291445591f69f08a13b041c073a96a`) Python source, this fresh `eld-rd-carbon` session departs from both briefs' primary bets and selects a team-originated third mechanism: a **Sync-Free Packed-MoE & Gather-Sparse BF16 Decode Engine (CUDA-Graphed)** over the unmodified BF16 checkpoint and unchanged `<PAGE><BLOCK>...<FORK>` output contract. Candidate reconciliation (`<= 2` challengers), prototype implementation, custodian evaluation freeze, and GPU execution remain held pending coordinator release.

## Objective and acceptance criteria

Per [assignment.md](../../../coordination/WP-0015/assignment.md) and `eLedgerCare-Next-Lane-OCR-Speed-Trial.md`:

1. Read governance (`START_HERE.md`, `AGENTS.md`, `CURRENT.md`, `INDEX.md`, `docs/coordination/WP-0015/assignment.md`), all three brief files in `C:/Users/jackg/eLedgerCare-Speed/WP-0015/briefs/`, WP-0014's resident probe, and the read-only Q0 model/environment metadata without accessing `eld-rd-astra`'s position, sealed evaluation custody, or another branch, and without touching the GPU.
2. Record actual WP-0014 resident-probe kernels, tokenization, request limits, model/runtime pins, and renderer identity.
3. Independently answer which mechanism buys the most completed, correctly attributed scanned pages per minute on Jack's RTX 5070 Ti (`16 GB`) and specify the cheapest fair experiment that could falsify that choice, stating measured bottleneck, challenger, matched comparator, expected signatures by document type, material improvement, strongest downside, and abandonment condition, with full model/effort/upstream-authorship disclosure.
4. Write the one-page position to `docs/research/WP-0015/carbon/position.md`, commit it first, then commit reserved report `WP-0015 / 002` separately and push `research/wp-0015-carbon` normally without `--force`.

## Change inventory

### Deliverable diff (`c4d7734d0be6302e667d290698bc671631c71ce9..8acea1ca42aa23ad48a752c642107b9e9f883f47`)

| Action | Exact path | What changed and why | Relevant symbols / sections |
| --- | --- | --- | --- |
| Added | `docs/research/WP-0015/carbon/position.md` | Added `eld-rd-carbon`'s independent one-page WP-0015 architecture position (`10,468` bytes, Git blob `323f3ca34fb84dda0640d76ff7e7d528bf9b41e3`, SHA-256 `9aecef8277f06dfebf28cdd2e76b81fb985c7c906769a05d04368b64201d02ec`). | `§1 Direct Answer`, `§2 Measured Bottleneck & Host/Source Evidence`, `§3 Challenger, Comparator & Expected Signatures`, `§4 Material Improvement, Strongest Downside & Cheapest Fair Falsifier` |

### Report metadata committed afterward

- Added `docs/agent-reports/eld-rd-carbon/WP-0015/002_2026-11-18_research_eld-rd-carbon.md` in a separate commit atop `8acea1ca42aa23ad48a752c642107b9e9f883f47`. Per `AGENTS.md`, this report pins `8acea1ca42aa23ad48a752c642107b9e9f883f47` and does not claim to contain its own commit SHA. `INDEX.md`, `CURRENT.md`, `src/`, `workers/`, and `C:\Users\jackg\eLedgerCare-Q0\WP-0005` were untouched.

### External effects

- None on host services, databases, GPU state, or `Q0`. Normal push of owned branch `research/wp-0015-carbon` to `origin` (`https://github.com/jackgumpe/eledgercare`).

## Decisions and rationale

1. **Host bottleneck attribution (`105.16 ms/token` vs `1.29 ms/token` bandwidth floor):**
   - WP-0014's resident BF16 runner (`instrument.py`, `summary.json`) cut 57-token short-scan latency to `6.650 s` median (`0.071–0.090 s` `pypdfium2` 300-DPI RGB render, `0.032–0.036 s` SAM+CLIP+projector vision, `0.376–0.435 s` TTFT, `9.16–10.02 tok/s` post-first-token), while structured work order `S` (`1,122` tokens) took `118.670 s` warm (`0.381 s` TTFT, `117.994 s` post-first-token = `99.4%` of elapsed time, `9.51 tok/s` / `105.16 ms/token`, `0.51 pages/min`).
   - Active BF16 weights read per token (`layer 0` dense MLP `52.6 MB` + `11` shared-expert MLPs `151.4 MB` + `11 × 6` routed experts `454.2 MB` + `12` attention/router layers `165.2 MB` + `lm_head` `331.0 MB` ≈ `1.15 GB`) require `~1.29 ms` at `896 GB/s` GDDR7 (`1.2%` of `105.16 ms`). Thus **>97% of decode latency is host-device sync and Python/eager dispatch overhead**, specifically:
     - `_sparse_base_impl.py:790-802` (`DeepseekV2MoE.moe_infer`): `tokens_per_expert.cpu().numpy()` forces **11 synchronous WDDM GPU→CPU pipeline flushes per token** plus a 64-expert Python loop launching `198` unbatched `[1, 1280]` `nn.Linear` kernels/token.
     - `modeling_deepseekv2.py:381-531` (`_dash_decode_forward` / `_decode_attend`): reallocates `DynamicCache` and `_dash_idx_k` via `torch.cat`, recomputes `head_cls` summaries across all `nblk` blocks, and casts full-sequence `k_all.float(), v_all.float()` (`[1, 10, S, 128]`) for dense `O(S)` FP32 attention despite DASH selecting `<= 512` keys (`12 × 32` same-page image tokens `∪` `128` local tokens).
     - `modeling_unlimitedocr.py:1155-1195` (`_uocr_generate`): `eval_mode=False` invokes `TextStreamer` (`decode`+`print`) every token, runs CPU Python 35-gram tuple loops, and synchronizes at `int(torch.argmax(logits))`.
2. **Rejection of both upstream briefs' primary first moves:**
   - *Upstream Carbon (`Baidu OCR Optimization.pdf`):* Relies on absent/forbidden Triton (`triton_policy="absent"` in `dependency-lock.json`) and blocked SGLang (`sglang-kernel==0.4.7` Linux-only, AMD SVM disabled). Quantizing routed experts to FP8 saves `<0.3 ms/token` until sync/dispatch stalls are removed and forfeits BF16 weight parity.
   - *Speculative drafters (`SS-SED` and Cloud Review's cheap-reader + markup-template drafter) & HTML stripping:* In `04809669`, incremental verification (`q_len > 1` with non-empty `past_kv`) misroutes into prefill (`modeling_deepseekv2.py:232`, `modeling_unlimitedocr.py:499`, `_sparse_base_impl.py:1457`), corrupting `_uocr_pg`/`_dash_idx_k` and shape-crashing `_forward_dense`; even patched, verifying 6 tokens on the Python MoE loop activates `~28` experts/layer (`~84` linear launches/layer). Furthermore, tokenizing WP-0014's `S` output (`1,122` tokens) with `04809669/tokenizer.json` shows **`541` tokens (`48.2%`) are `<PAGE>` + 36 `<BLOCK>label[x1,y1,x2,y2]<FORK>` headers**, **only `56` tokens (`5.0%`) are HTML table tags**, and `525` (`46.8%`) are visible text—meaning templates cover `5%`, external cheap OCR cannot predict Baidu's quantized `0..999` box integers (`144` numbers on `S`), and stripping HTML tags without fixing `9.51 tok/s` decode still leaves `S` at `~61 s/page`.
3. **Selected challenger & falsifier:** Pack the 64 routed experts per layer in-place into contiguous BF16 `[64, 1792, 1280]` and `[64, 1280, 896]` tensors (`index_select + bmm` static `[6, ...]` decode, `torch._grouped_mm` prefill), replace `torch.cat` / dense FP32 full-KV decode with static BF16 caches + incremental tail `k_bar` + gather-only `<= 512`-key sparse decode attention, move 35-gram/`<PAGE>` guards onto GPU tensors with `TextStreamer` disabled, and capture the 1-token step in `torch.cuda.CUDAGraph`. Test against matched Resident Native BF16 (`WP-0014`) in `< 10` GPU-minutes on `A`, `S`, and the 3-page boundary dev packet, with immediate abandonment if `S` fails to improve `>= 5×` (`< 23.7 s`) or violates VRAM/completeness/quality gates.

## Verification

### Executed CPU checks

| Check / exact command or tool operation | Environment and revision | Actual result | Evidence location |
| --- | --- | --- | --- |
| `git status -sb; git rev-parse HEAD; git branch --show-current` | PowerShell, `speed-carbon` @ `c4d7734d0be6302e667d290698bc671631c71ce9` | Clean branch `research/wp-0015-carbon` at `c4d7734d0be6302e667d290698bc671631c71ce9`. | Git history |
| `Get-FileHash -Algorithm SHA256 ...` on the three WP-0015 briefs | PowerShell, `speed-carbon` @ `c4d7734d` | Failed (`exit 1`, `CommandNotFoundException`: `Get-FileHash` cmdlet module not autoloaded in restricted shell). Replaced immediately by `certutil -hashfile ... SHA256`. | Reported above |
| `certutil -hashfile ... SHA256` on `Baidu OCR Optimization.pdf`, `eLedgerCare-OCR-Architecture-Review.md`, `eLedgerCare-Next-Lane-OCR-Speed-Trial.md` | PowerShell, `C:\Users\jackg\eLedgerCare-Speed\WP-0015\briefs` | All 3 SHA-256 digests matched [assignment.md](../../../coordination/WP-0015/assignment.md) exactly (`6c7f5199...`, `a6442154...`, `5b46d531...`). | [assignment.md](../../../coordination/WP-0015/assignment.md) |
| Read-only source inspection of WP-0014 probe/reports and Q0 `Unlimited_OCR_2_04809669` (`config.json`, `modeling_unlimitedocr.py`, `modeling_deepseekv2.py`, `dash_attention.py`, `_sparse_base_impl.py`, `conversation.py`, `README.md`) | `read_file` on owned worktree and read-only `C:\Users\jackg\eLedgerCare-Q0\WP-0005` | Verified exact runtime/model/renderer/limit pins, `moe_infer` `.cpu().numpy()` sync, `_decode_attend` full-KV FP32 upcast, `TextStreamer` default, and `q_len > 1` prefill misrouting. | [position.md](../../../research/WP-0015/carbon/position.md) |
| `$env:CUDA_VISIBLE_DEVICES=""; & "C:\Users\jackg\eLedgerCare-Q0\WP-0005\venv\Scripts\python.exe" -I -B -c "..."` (`tokenizers.Tokenizer.from_file` on WP-0012/0014 `S` `raw_output.utf8.bin`, `assert 'torch' not in sys.modules`) | CPU-only Q0 Python `3.12.10` (`tokenizers==0.21.4`), `torch` not imported | `exit 0`: `1,122` total tokens = `541` `<PAGE>`/`<BLOCK>...<FORK>` header+box tokens (`36` blocks) + `56` HTML table-tag tokens (`76` tags) + `525` plain-text tokens; `torch imported: False`. | [position.md](../../../research/WP-0015/carbon/position.md) |
| Static stub check on `torch\_C\_VariableFunctions.pyi` and `torch\cuda\graphs.py` (`assert 'torch' not in sys.modules`) | CPU-only Q0 Python `3.12.10`, `torch` not imported | `exit 0`: confirmed `def _grouped_mm(`, `bmm`, `index_select`, `gather`, and `torch.cuda.graphs` exist in `torch==2.13.0+cu130`. | [position.md](../../../research/WP-0015/carbon/position.md) |
| Deliverable commit & digest check (`git commit`, `git rev-parse HEAD`, `git ls-tree HEAD`, `certutil -hashfile ... SHA256`, `git cat-file -s`) | PowerShell, `research/wp-0015-carbon` @ `8acea1ca42aa23ad48a752c642107b9e9f883f47` | `exit 0`: 1 file added (`10,468` B LF in working tree and Git blob `323f3ca34fb84dda0640d76ff7e7d528bf9b41e3`, SHA-256 `9aecef8277f06dfebf28cdd2e76b81fb985c7c906769a05d04368b64201d02ec`). | Git commit `8acea1ca` |

### Checks not run and why

- **Live GPU / CUDA execution, `torch` import, `CUDAGraph` capture, and model inference:** Not run. This initial position assignment is strictly **CPU-only**; GPU execution requires candidate selection, custodian protocol/dev freeze, and a separate coordinator-bound exclusive GPU lease.
- **Cross-branch / peer / sealed-corpus checks:** Intentionally not run per independence and custody rules (`eld-rd-astra` and sealed evaluation directories untouched).

## Review map

- Deliverable position: [docs/research/WP-0015/carbon/position.md](../../../research/WP-0015/carbon/position.md) (deliverable commit `8acea1ca42aa23ad48a752c642107b9e9f883f47`)
- Controlling packet assignment: [docs/coordination/WP-0015/assignment.md](../../../coordination/WP-0015/assignment.md)
- Baseline probe & evidence inspected: [instrument.py](../../../research/WP-0014/eld-latency-author/instrument.py), [probe.py](../../../research/WP-0014/eld-latency-author/probe.py), [summary.json](../../../research/WP-0014/eld-latency-author/evidence/summary.json), [cpu.json](../../../research/WP-0014/eld-latency-author/evidence/cpu/cpu.json), [protocol.py](../../../../workers/local_ocr/local_ocr/protocol.py), [dependency-lock.json](../../../../workers/local_ocr/manifests/dependency-lock.json), [model-files.json](../../../../workers/local_ocr/manifests/model-files.json)

## Risks, disagreements, and unfinished work

- **Single-token bandwidth ceiling on all-dense packets:** Even at `~250–320 tok/s`, 60 pages averaging `1,122` tokens/page (`67,320` tokens) require `~210–270 s` (`13–17 pages/min`). If the target packet distribution is uniformly dense rather than mixed (`~350–550` tok/page), the second challenger slot should test multi-token drafting (`SS-SED` or compact span emission) *on top of* this sync-free engine rather than atop the `9.51 tok/s` Python loop.
- **BF16 accumulation ULP & WDDM `CUDAGraph` behavior:** Packed `bmm`/`_grouped_mm` may shift `0..999` box coordinates by `±1` relative to sequential `nn.Linear` (just as warm vs cold native BF16 shifted `15/36` boxes on `S` in WP-0014), shifting evaluation from `Exact` token-ID parity to the predeclared `Changed-Output` budget (`<= +0.01` CER, `>= -0.02` cell accuracy, zero new unflagged critical errors). Static `S_max` buffer sizing on WDDM must be verified under an actual GPU lease.
- **Unfinished packet work:** Reveal/reconcile with `eld-rd-astra` (`WP-0015 / 001`), agree on at most two materially different challengers, integrate custodian dev bundle/scorer (`WP-0015 / 003`), implement CPU-tested prototype, and await coordinator GPU lease (`WP-0015 / 004`–`005`) and independent Opus replay (`WP-0015 / 006`).

## Handoff

- **Next owner:** `eld-coordinator`
- **Branch:** `research/wp-0015-carbon`
- **Base revision:** `c4d7734d0be6302e667d290698bc671631c71ce9`
- **Deliverable revision:** `8acea1ca42aa23ad48a752c642107b9e9f883f47` (`docs/research/WP-0015/carbon/position.md`)
- **Canonical report path:** `docs/agent-reports/eld-rd-carbon/WP-0015/002_2026-11-18_research_eld-rd-carbon.md` (publication commit SHA supplied in the handoff response after committing and pushing this report)
- **Next action:** Verify remote objects on `origin/research/wp-0015-carbon`; once `eld-rd-astra` (`WP-0015 / 001`) is frozen, reveal both positions for candidate selection (`<= 2` challengers) and subsequent custodian/GPU binding. Remote confirmation is executed immediately upon committing this report and reported in the turn response without rewriting this immutable file.
