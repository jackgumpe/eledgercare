# WP-0014 / 001 — Native short-page OCR latency

**Author** eld-latency-author, fresh native Codex session. Jack requested xhigh. The exact backend and applied effort were unexposed. **Status** ready for independent review by eld-latency-reviewer. **Published** 2026-11-18T02:01:44Z. **Category** research. First report in this packet.

**Repository** private `jackgumpe/eledgercare`, branch `research/wp-0014-ocr-latency`. Packet base `a8c13670c868997ceeb1f621c7954f031451a4b7`. Assignment `181c98568a5d1a0d4c5a5773f89be54af0effa73` reserves this path. Fresh probe `4ade03ee00e9701241770523d5df60df27da4b0c`. Resident probe `1d3f0f1922ac9dca6a87691e5718d3148aa52a5c`. Evidence `46657096c11befc72a4e629ca688ee7755a2fbc5`. [Reservation](../../../../INDEX.md#wp-0014-short-page-ocr-latency-investigation-2026-11-18-utc)

## Result

Two different, three-sentence scans took **52.539 and 52.039 seconds** from fresh worker launch to result availability. The four requests to an already-used model took **6.414–6.931 seconds**, median **6.650**. Matched speedups were **7.58–8.19×**, median **7.83×**. Every short result contained all three expected sentences in order with exact case and punctuation. Results met the predeclared 10-second and 2× short-request targets. The long page retained all previously correct checked content. A few geometry values changed. These measurements cover the local worker. Browser scheduling, database publication, true operator waits and alternate backends belong to other packet owners. [Measurements](../../../research/WP-0014/eld-latency-author/evidence/summary.json)

|Call|Output tokens|Result-ready seconds|Native first token s|Native post-first s|Subsequent visible tokens/s|
|---|---:|---:|---:|---:|---:|
|Fresh A|57|52.539|—|—|—|
|Fresh B|57|52.039|—|—|—|
|Fresh S|1,122|185.780|—|—|—|
|Resident process, first A|57|48.075 from launch, 47.878 in request|18.695|5.681|10.02|
|Warm B|57|6.622|0.396|5.894|9.67|
|Warm A|57|6.414|0.376|5.760|9.89|
|Warm B|57|6.677|0.386|6.006|9.49|
|Warm A|57|6.931|0.435|6.207|9.16|
|Warm S|1,122|118.670|0.381|117.994|9.51|

Fresh clocks stop at the first 40-ms parent poll that sees the atomic envelope. Fresh process-exit waits were 53.747, 53.208 and 186.910 seconds. Warm service includes input materialization, request, renderer, output checks, envelope and heartbeat completion. Native first token includes initial selection. The subsequent-emission rate uses N−1 visible token intervals. Native post-first also includes EOS selection and result construction. Dividing tokens by the entire infer call gives 2.33 tokens/s for resident-first A and 8.48–9.17 for warm short pages. Every instrumented input had 273 image tokens among 279 prompt tokens, and each returned one page. [Clock definitions](../../../research/WP-0014/eld-latency-author/README.md)

## Where the time went

Jack’s separate, operator-supplied metadata records **53.374 seconds** for 61 output tokens, including 0.182 render, 12.261 named load, 26.808 infer and 14.123 unitemized seconds. His document was never accessed. Fresh A/B worker totals were 52.309/51.804 seconds, including 0.171/0.168 rendering, 13.445/12.956 loading and 27.475/26.851 inference. The instrumented first A reconciles its own terms as follows. [Cold A phase events](../../../research/WP-0014/eld-latency-author/evidence/resident/1-A/events.json)

|Disjoint cold-worker component|Seconds|Measured detail|
|---|---:|---|
|Render|0.155|Includes PDFium import/identity, page-verified RGB rendering and raster digest|
|Named model load|11.737|Tokenizer 0.450, model construction/weights 7.202, CUDA transfer dispatch 4.075, final device synchronization <0.001|
|Inference|24.463|Native pre-first-token 18.695, native post-first 5.681, wrapper/input work accounts for most of the balance|
|Remaining worker time|11.516|Full model/notice verification and generation pin 6.445, Torch import 2.408, Transformers imports 2.217, other work and timer gaps 0.447|
|Worker total|47.871|Process launch to script entry 0.045 and script entry through imports 0.152 precede the request|

The verifier measured 4.802 and 1.595 seconds hashing the two weight shards totaling 6,688,305,576 bytes. The Windows child reported 6.916 GB of logical read transfer over the cold request. Storage caching precludes deduction of physical SSD traffic. Cold peak process working set reached 7.26 GB. CUDA peak allocated/reserved memory for A was 7.29/7.48 GB. Cold synchronized vision from SAM entry to projector return took 1.270 seconds, and subsequent short calls took 0.032–0.036 seconds. The rest of the cold native first-token span includes decoder prefill, first-use work and first selection. This probe cannot identify which individual operation incurred the remaining startup delay. The synchronized first-streamer callback arrived 18.776 seconds from first infer entry and 0.453–0.508 seconds on warm short calls. Each saw one infer_multi entry, one image-build, one SAM and one projector call. All used the accepted dense fallback. Timing attribution and kernel-level causality for Jack’s individual receipt remain open. [Native first-token record](../../../research/WP-0014/eld-latency-author/evidence/resident/1-A/native.json)

## Output, integrity and scope

The fresh B and both warm B raw byte strings matched. Fresh and resident-first A used box `[73,103,770,203]`. Both warm A results used `[73,104,770,203]`. Warm structured S changed 15 of 36 boxes. Removing only box coordinates made all paired full outputs byte-identical, including structured markup. S retained 15/15 checked printed field values and 18/19 cells at their expected table, row and column positions. Both versions read SKU `CAP-45-SMFD-440V` in place of `CAP-45-5MFD-440V`. All raster hashes matched. Distinct request IDs, independent result envelopes and alternating A/B text establish the observed separation. The model creates a fresh DynamicCache per generation and also assigns input IDs, page-RoPE metadata and decode allowances to shared layer objects on forward. Its finally block restores the inference controls. This experiment does not establish general state erasure or the cause of geometry drift. [Bounding-box comparison](../../../research/WP-0014/eld-latency-author/evidence/box-comparison.json) · [S score](../../../research/WP-0014/eld-latency-author/evidence/resident/6-S/score.json) · [Pinned model source](https://huggingface.co/baidu/Unlimited-OCR-2/blob/0480966938291445591f69f08a13b041c073a96a/modeling_unlimitedocr.py#L680)

The research resident holds Windows read-sharing handles on the verified model and notice files. It hashes before first use, verifies generation identity and namespace on each request and rechecks before raw publication. Five synthetic controls showed refusal on same-size write, unlink, added file, prior corruption and missing file. One-image 300-DPI rendering, per-document guards and native calls remain intact. Requests were serialized against a read-only Q0 installation on one RTX 5070 Ti. OS caches, device clocks and free system RAM were uncontrolled. Timing callbacks and CUDA boundaries apply only to the instrumented stage. Four warm short observations and one warm structured result do not establish population latency or geometry equivalence. [CPU controls and fixture identities](../../../research/WP-0014/eld-latency-author/evidence/cpu/cpu.json)

## Reproduction and handoff

The coordinator released fresh work at `eec24b8d3d33dffbaeec8f4550aca75ded069d99` and resident work at `655102ecc09aa9242db404d4c210e4391c90ecac`. Both used the unmodified worker tree `dc9b69e480f93db1e73ebdd65719efaa9aeab298` and model `0480966938291445591f69f08a13b041c073a96a`. Source/config/lock digests and environment pins appear in the CPU record. The three production processes and one research process exited 0. The coordinator received the sole lease back before packaging; the post-run observation showed 14,479 MiB free. No customer data, service changes, installs or changes to the model/venv occurred.

- Under `docs/research/WP-0014/eld-latency-author/` the source inventory is `.gitattributes`, `A.pdf`, `B.pdf`, `README.md`, `cases.py`, `collect.py`, `fixtures.py`, `generation.py`, `instrument.py`, `probe.py` and `summarize.py`. The evidence commit adds 56 inventoried files plus the inventory, aggregate summary and box comparison. The subsequent publication adds this report alone. [Evidence inventory](../../../research/WP-0014/eld-latency-author/evidence/inventory.json)
- From the owned worktree, `python -I -B docs/research/WP-0014/eld-latency-author/probe.py cpu trial1` ran on the fresh candidate, and `cpu guardfinal` passed on the final candidate. The same command with `fresh-A`, `fresh-B`, `fresh-S` and `resident`, label `trial1`, and `--gpu GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d` ran in sequence under the two releases. `summarize.py` recomputed the published JSON exactly. All 56 staged file digests and lengths matched and all six native event/token/vision counts agreed with their envelopes. The full run-local logs, caches and materializations persist under `C:\Users\jackg\eLedgerCare-Latency\WP-0014\author`. [Supervisor](../../../research/WP-0014/eld-latency-author/probe.py) · [Instrument](../../../research/WP-0014/eld-latency-author/instrument.py)
- Retaining one verified and warmed native worker is the measured next product candidate. Keep the existing fresh-worker path as fallback and account for readiness cost on the first click. The reviewer owns the matched fresh A and resident A→B→A repeat. The coordinator owns scheduling, browser/history checks, alternate-backend disposition and any separately reviewed product change.
