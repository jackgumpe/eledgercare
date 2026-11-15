# Independently Assessed Hypotheses and Rejected Complexity (WP-0004 / 002)

## 1. Challenge of Needless Complexity and Confounded Treatments

Before proposing experimental treatments, Carbon rejects three sources of needless complexity or confounding revealed by primary-source inspection:

1. **Rejected for initial scope — SGLang Cross-Chunk KV-Reuse Page-Window Scheduling (`SGLANG_UOCR_DOC_*_PAGE_WINDOW=10`):**
   - *Source:* `Unlimited-OCR-2.pdf` §3.4 (Algorithm 1, Fig. 4, Table 4) and HF `README.md` lines 132–178 (`0480966938291445591f69f08a13b041c073a96a`).
   - *Why rejected now:* Algorithm 1 partitions ultra-long books (`MarathonDocBench`, 103–300 pages) into $W=10$-page chunks inside a custom Linux-only SGLang wheel (`sglang-0.5.20.dev13+g75b9b06b02`) relying on `/dev/shm` IPC. Property maintenance work orders and invoices are typically 1–6 pages (and our starter corpus spans 1–3 pages). Whenever page count $N \le W$, Algorithm 1 sets $K=1$ (unsegmented), making page-window chunking a mathematical no-op. Artificially shrinking $W$ (e.g., $W=2$) on short invoices destroys cross-page block continuity (`README.md` line 176 explicitly notes smaller windows break cross-page merging) while requiring an unsupported Linux serving stack on a native Windows host.
2. **Rejected — Bundled Multi-Filter Image Preprocessing Pipelines:**
   - Applying unconditional Sauvola/Otsu binarization + CLAHE + morphological denoising simultaneously creates a coupled multi-variable treatment, erases thin grayscale table gridlines needed for `<table>` HTML recognition, and degrades clean digital renders. Any image intervention must isolate **one** transformation behind a measurable trigger and guarantee byte-identical pass-through on clean pages.
3. **Rejected — Local Architecture Edits, Router Retraining, or LoRA Fine-Tuning Before a Vanilla Baseline Exists:**
   - No local OCR baseline has been executed yet (`03-RD-BRIEF.md`), and training/architecture changes are out of scope. Do not treat an unmeasured baseline as zero accuracy.

---

## 2. Prioritized Hypothesis Cards (Maximum Three)

All three hypotheses below are **upstream-only / pre-baseline proposals** until local runtime qualification (`01-sources-and-qualification.md` §2.2) establishes a reproducible vanilla baseline on pinned revision `0480966938291445591f69f08a13b041c073a96a`. Comparisons must use **paired per-document differences** across the frozen `eval_holdout` family split (`03-corpus-and-candidates.md` §3), reporting exact per-document failures rather than assuming Gaussian score distributions or claiming statistical significance from $N=4$ held-out families.

---

### Hypothesis Card H-C1: Deterministic Born-Digital PDF Text-Layer Gate vs. Unconditional VLM Raster OCR

- **Observed or literature-supported limitation (source & applicability):**
  - Upstream `Unlimited-OCR-2` (`README.md` L200–210; `modeling_unlimitedocr.py` L1039–1108) unconditionally rasterizes every PDF page to an RGB bitmap and autoregressively decodes all tokens through a 3B MoE VLM (`DeepEncoder` + 12-layer decoder).
  - Many contractor invoices and property-management work orders arrive as born-digital PDFs exported directly from accounting/dispatch software (confirmed in both public candidates `sample-invoice.pdf` and `Invoice-6.pdf`, which carry embedded `BT..ET` vector text streams). Rasterizing clean vector text consumes multi-second GPU compute and ~7–12 GiB VRAM on a shared 16 GiB WDDM workstation while introducing non-zero risk of glyph substitution (`0`/`O`, `1`/`I`, decimal-point drift) or autoregressive repetition loops (`_uocr_no_repeat_ngram`, `modeling_unlimitedocr.py` L608–623).
- **Proposed single change and mechanism:**
  - Insert a deterministic CPU-only pre-OCR routing gate (`pypdf` / `pypdfium2`) ahead of VLM invocation. A PDF routes to deterministic vector text/coordinate table extraction **if and only if every page** satisfies all three checks:
    1. Extracted printable non-whitespace character count $\ge \tau_{\text{chars}}$ (calibrated on `dev`, e.g., $\ge 80$ chars/page);
    2. Zero Unicode replacement characters (`U+FFFD`) and zero unmapped CID/`/ToUnicode` failures (`unmapped_glyph_ratio == 0.0`);
    3. Embedded raster `/Subtype /Image` XObjects cover $< \tau_{\text{img\_area}}$ of page area (calibrated on `dev`, e.g., $< 15\%$, permitting small vendor header logos while forcing any page with scanned attachments, photo evidence, or rasterized stamps/signatures through full VLM OCR).
  - Any document failing any check on any page routes unchanged to the vanilla `Unlimited-OCR-2` VLM pipeline. Extracted output records explicit provenance (`source_mode: pdf_text_layer` vs. `ocr_vlm`) so text-layer extraction is never misrepresented as OCR model accuracy.
- **Vanilla baseline checkpoint / runtime / configuration:**
  - Unconditional VLM OCR on every PDF: `baidu/Unlimited-OCR-2` @ `0480966938291445591f69f08a13b041c073a96a`, native `Transformers` (`transformers==4.52.1`, `torch.bfloat16`), `pypdfium2` 300 DPI RGB PNG rendering, `temperature=0.0`, `page_count_guard=True`, `max_page_tokens=20000`, `save_results=False`, post-processed via `utils/process_unlimitedOCR2.py` (`3de5de31a7e5c925e84af68ef12b1b8d7db9e24a`) into the shared deterministic field/table normalizer.
- **Controlled variables and remaining confounders:**
  - *Controlled (held identical):* Input PDF byte streams, `dev`/`eval_holdout` family split, downstream field/line-item schema normalizer and `Decimal` arithmetic checker, host hardware.
  - *Potential confounders:* (1) Reading-order differences on multi-column headers (e.g., side-by-side `BILL TO` / `SHIP TO` / `SERVICE ADDRESS` blocks in `sample-invoice.pdf` or `SYN-WO-01`) if PDF stream order differs from visual xy-cut order—mitigated by sorting extracted PDF text spans by `(page, y_bucket, x_min)` using PDF bounding boxes; (2) hybrid PDFs containing vector form labels but a rasterized technician note—guarded by check #3 (`image_area_ratio`).
- **Predicted quality / completeness, latency, memory, or cost effect:**
  - *Quality/completeness:* `0` character transcription errors on born-digital text; `0` silent omissions on raster/scanned/hybrid variants (100% routed to VLM).
  - *Latency & memory:* `>95%` wall-clock latency reduction (`<100 ms/doc` CPU vs. multi-second GPU prefill+decode) and `0 MiB` GPU VRAM allocated for gated born-digital PDFs.
- **Metric and denominator, failure signal, and rejection criterion:**
  - *Metrics & explicit denominators:*
    1. **Hybrid/Scan Routing Safety:** `misrouted_non_digital_pages / total_scanned_or_hybrid_pages` (across all rasterized/degraded/hybrid variants in `eval_holdout`).
    2. **Paired Field & Table-Cell Exact Match:** `exact_matched_items / total_expected_items` per document on `eval_holdout` (where `total_expected_items` = sum of required header fields + table cells + cross-page identifiers in `source_record.json`).
    3. **Invoice Decimal Exactness:** `invoices_with_all_monetary_fields_exact / total_eval_invoices`.
    4. **Resource Cost:** Median and max per-document wall-clock latency (`ms`) and peak `torch.cuda.max_memory_reserved()` (`MiB`).
  - *Failure signal:* Any raster/hybrid page bypassing OCR (`misrouted_non_digital_pages >= 1`), or multi-column address/table cell scrambling in vector extraction causing fewer exact matches than vanilla VLM OCR on any born-digital document.
  - *Rejection criterion:* **Reject H-C1** if `misrouted_non_digital_pages > 0` on `dev` or `eval_holdout`, **OR** if any born-digital document in `eval_holdout` exhibits a negative paired accuracy delta (`matched_items_gate < matched_items_vlm`), **OR** if CPU gate + vector extraction latency exceeds `250 ms/page`.
- **Smallest execution needed and hardware / storage requirements:**
  - Gate accuracy and vector extraction against synthetic `source_record.json` ground truth can be dry-run on **CPU only** (`0` GPU VRAM, `<50 MiB` venv with `pypdf`/`pypdfium2`); full paired comparison against the VLM baseline requires one qualified local GPU session (`RTX 5070 Ti` 16 GiB, `~12–16 GiB` model/runtime disk).
- **Product relevance, risks, and promotion cost:**
  - High operational value for an on-premises intranet deployment sharing a single workstation GPU: eliminates GPU queue contention for born-digital vendor invoices while keeping honest method provenance in `ExtractionResult`. Low promotion cost (self-contained pre-OCR intake router in `workers/ocr/`).

---

### Hypothesis Card H-C2: Multi-Page Visual Encoding Mode (`infer` with `crop_mode=True` Gundam Tiling vs. `infer_multi` Default `crop_mode=False` Base Mode)

- **Observed or literature-supported limitation (source & applicability):**
  - Source-code audit reveals a direct discrepancy between upstream's documented Transformers multi-page entry point and upstream's benchmark script:
    - HF `README.md` lines 101–108 instruct Transformers callers to run `model.infer_multi(tokenizer, image_files=pages)`, and `modeling_unlimitedocr.py` lines 1110–1123 implement `infer_multi` with `kwargs.setdefault('crop_mode', False)` (**base mode**). Under `crop_mode=False` (`_uocr_build_inputs`, L531–580), each page is letterbox-padded into a single `1024x1024` tensor (`273` visual tokens/page) with **zero** local `640x640` crops—reducing an `8.5x11"` page to `~93` effective DPI (`~791x1024` active pixels).
    - Conversely, single-page `model.infer` (L541) and Baidu's own SGLang evaluation script (`infer.py` L74, blob `17b1e93f4e64a8a6924c8ee0e061e7a4837c8b43`) default multi-page documents to `crop_mode=True` (**gundam dynamic tiling**, up to `max_crops=16` `640x640` local tiles + `1024x1024` global view per page), falling back to `crop_mode=False` only when context approaches `131,072` tokens.
  - On 2–3 page maintenance invoices and work-order packets containing 8–10 pt SKU codes, unit numbers, serial numbers, and 2-decimal currency columns, `infer_multi`'s silent `crop_mode=False` confounds multi-page evaluation with severe spatial downsampling—while enabling `crop_mode=True` on native Windows without Triton (`_forward_dense`, `dash_attention.py` L1230–1260) risks exceeding 16 GiB WDDM physical VRAM headroom.
- **Proposed single change and mechanism:**
  - Change **one** boolean argument in multi-page native `Transformers` invocation (`UnlimitedOCRForCausalLM.infer` on ordered page lists of length $2 \le N \le 4$): set `crop_mode=True` (gundam dynamic tiling, keeping default `max_crops=16`, `base_size=1024`, `image_size=640`) instead of `infer_multi`'s default `crop_mode=False`. All other decoding, prompt, RoPE, and post-processing settings remain identical.
- **Vanilla baseline checkpoint / runtime / configuration:**
  - `UnlimitedOCRForCausalLM.infer(..., image_file=pages, crop_mode=False)` (exact behavior of documented `model.infer_multi`), checkpoint `0480966938291445591f69f08a13b041c073a96a`, `torch.bfloat16`, `pypdfium2` 300 DPI PNGs, prompt `"<PAGE><image>" * N + "Multi page parsing."`, `temperature=0.0`, `page_count_guard=True`, `max_page_tokens=20000`, `dash_topm=16`, `no_repeat_ngram_size=35`, `ngram_window=1024`, `save_results=False`, post-processed via `utils/process_unlimitedOCR2.py`.
- **Controlled variables and remaining confounders:**
  - *Controlled (held identical):* Checkpoint weights, exact 300-DPI PNG inputs per page, prompt template, `no_repeat_ngram_size=35` / `ngram_window=1024` (matching `README.md` L228–240), `dash_topm=16`, `page_count_guard=True`, `process_unlimitedOCR2.py` cross-page union-find table/text merger, and GPU host state.
  - *Potential confounders:* (1) Absence of Triton on Windows forces prefill through `_forward_dense` (`q_chunk=2048`), making peak prefill memory sensitive to total visual token count $S$; (2) concurrent desktop/browser WDDM VRAM consumption (`1,155 MiB` at preflight)—must record pre-run `nvidia-smi` baseline and enforce single-owner GPU lease during paired back-to-back execution.
- **Predicted quality / completeness, latency, memory, or cost effect:**
  - *Quality/completeness:* Improved exact character/digit recognition on dense multi-page table cells, part numbers, and cross-page serial/invoice identifiers, with unchanged `<PAGE>` ordering.
  - *Latency & memory:* Visual prefill tokens increase from `273/page` to `~1,500–2,800/page` (~5–10x), increasing prefill latency ~2–4x and raising peak CUDA reserved memory on 3-page documents toward `~10–14 GiB`.
- **Metric and denominator, failure signal, and rejection criterion:**
  - *Metrics & explicit denominators:*
    1. **Multi-Page Field & Table-Cell Exact Match:** `matched_items / total_expected_items` across multi-page families (`F07`, `F08` and multi-page raster variants; `F07` in `dev`, `F08` in `eval_holdout`, plus paired resolution check on dense single-page invoices `F05`/`F06` forced through `crop_mode=False` vs `crop_mode=True`).
    2. **Page-Order & `<PAGE>` Alignment Integrity:** `correctly_ordered_non_truncated_pages / total_input_pages` (`num_pages_out == expected_pages` and monotonic page-anchor match).
    3. **Cross-Page Continuation Accuracy:** `correctly_merged_cross_page_tables_and_ids / total_cross_page_links`.
    4. **VRAM & Latency Envelope:** Peak `torch.cuda.max_memory_reserved()` (`MiB`) and end-to-end seconds/document.
  - *Failure signal:* CUDA OOM, WDDM shared-memory thrashing (`max_memory_reserved > 14,500 MiB` accompanied by step-latency spike), `<PAGE>` count mismatch, or loss of cross-page table merging.
  - *Rejection criterion:* **Reject H-C2** (for direct multi-page `crop_mode=True`) if (1) peak CUDA reserved memory on a 3-page 300-DPI maintenance document exceeds `14,500 MiB` on the 16 GiB RTX 5070 Ti, **OR** (2) paired exact item match on `eval_holdout` improves by `<= 0` items over `crop_mode=False` while increasing wall-clock latency by `> 2.0x`, **OR** (3) any page-order or `<PAGE>` truncation failure occurs (`correctly_ordered_non_truncated_pages < total_input_pages`). *(Note: if rejected solely due to multi-page VRAM ceiling #1 while dense-glyph accuracy gain is confirmed on 1-page pages, a separate follow-up candidate—sequential 1-page `crop_mode=True` vs. batched `crop_mode=False`—must be registered as a distinct treatment rather than silently substituted here.)*
- **Smallest execution needed and hardware / storage requirements:**
  - Requires qualified GPU runtime on RTX 5070 Ti (`16 GiB`), running paired `crop_mode=False` vs `crop_mode=True` passes on rendered PNGs (`<30 MiB` scratch image storage).
- **Product relevance, risks, and promotion cost:**
  - Directly governs how `workers/ocr/` invokes `Unlimited-OCR-2` on 2–4 page maintenance packets without adopting SGLang. Trivial promotion cost (single configuration constant plus an explicit max-page guard).

---

### Hypothesis Card H-C3: Conditional Non-Binarizing Deskew Gate ($|\hat{\theta}| \ge 1.0^\circ$) vs. Raw Image Pass-Through

- **Observed or literature-supported limitation (source & applicability):**
  - Scanned or clipboard-photographed maintenance work orders and supplier delivery tickets frequently arrive with 2°–6° rotational skew from sheet-fed scanners or handheld capture.
  - In `modeling_unlimitedocr.py` (`dynamic_preprocess`, L229–267), `gundam` tiling slices each page along a rigid axis-aligned $640\times640$ grid (`resized_img.crop(box)`). A 4°–6° skew causes single horizontal table rows (item description on the left, unit price and line total on the right) to cross vertical tile boundaries and warps horizontal rule lines that anchor `<table>...</table>` block detection. Conversely, rotating already-straight pages ($<1^\circ$) introduces bicubic resampling blur on crisp 1-px table rules.
- **Proposed single change and mechanism:**
  - Add a **single-variable, conditional, non-binarizing deskew gate** ahead of `model.infer`:
    - Estimate dominant page skew angle $\hat{\theta} \in [-15^\circ, +15^\circ]$ deterministically on a grayscale downsample via projection-profile variance maximization / Hough line median over long horizontal text/table strokes.
    - **If $|\hat{\theta}| < 1.0^\circ$:** pass the original RGB PNG **byte-for-byte unmodified** (`0` resampling, `0` pixel diffs).
    - **If $|\hat{\theta}| \ge 1.0^\circ$:** rotate the RGB page image by $-\hat{\theta}$ using deterministic bicubic interpolation with constant white border fill `(255, 255, 255)`, preserving full 24-bit RGB/grayscale tones and table gridlines (no binarization, no CLAHE, no morphological filtering).
- **Vanilla baseline checkpoint / runtime / configuration:**
  - Qualified `Unlimited-OCR-2` @ `0480966938291445591f69f08a13b041c073a96a`, passing rendered/captured RGB PNGs directly into `model.infer` (`BasicImageTransform` only), with fixed `crop_mode` (`True` on single-page, fixed baseline mode on multi-page), `temperature=0.0`, `page_count_guard=True`, `save_results=False`, and `utils/process_unlimitedOCR2.py`.
- **Controlled variables and remaining confounders:**
  - *Controlled (held identical):* Checkpoint, `crop_mode`, DPI (`300`), decoding parameters, post-processing, and underlying synthetic ground-truth records (`source_record.json`) from which both clean (`0.0°`) and skewed (`±2.0°`, `±4.0°`, `±6.0°`) evaluation variants are deterministically generated within the same family split.
  - *Potential confounders:* (1) Diagonal watermarks or sparse layouts fooling angle estimation—mitigated by requiring minimum horizontal stroke support before triggering rotation and logging $\hat{\theta}$ vs. true synthetic rotation angle $\theta_{\text{true}}$; (2) corner clipping on tight margins during rotation—mitigated by expanding canvas bounds (`expand=True` with white fill) rather than cropping corners.
- **Predicted quality / completeness, latency, memory, or cost effect:**
  - *Quality/completeness:* Byte-identical outputs (`0` regressions) on clean `0.0°` scans/renders; fewer row-misalignment and digit errors on `2°–6°` skewed maintenance invoices and checklists.
  - *Latency & memory:* `<80 ms/page` CPU overhead, `0 MiB` additional GPU VRAM.
- **Metric and denominator, failure signal, and rejection criterion:**
  - *Metrics & explicit denominators:*
    1. **Clean Pass-Through Invariance:** `untriggered_clean_pages / total_clean_0deg_pages` (target `1.00`, zero false triggers).
    2. **Angle Estimation Error (Diagnostic):** $|\hat{\theta} - \theta_{\text{true}}|$ in degrees across synthetic skewed variants.
    3. **Paired Skewed-Variant Table & Field Exact Match:** `matched_items / total_expected_items` on skewed `eval_holdout` variants (`|\theta_{\text{true}}| \in \{2^\circ, 4^\circ, 6^\circ\}`), paired per document against raw pass-through.
    4. **Clean-Document Regression Count:** `clean_eval_docs_with_negative_delta / total_clean_eval_docs`.
  - *Failure signal:* Any false-positive trigger on `0.0°` clean pages, corner text clipping after rotation, or zero/negative cell-match gain on skewed tabular fixtures.
  - *Rejection criterion:* **Reject H-C3** if (1) `untriggered_clean_pages < total_clean_0deg_pages` (any false trigger on clean `0.0°` pages) or `clean_eval_docs_with_negative_delta > 0`, **OR** (2) `Unlimited-OCR-2`'s `DeepEncoder` (`sam_vit_b` + `clip-l`) proves natively rotation-tolerant at `2°–6°` such that paired item-match gain on skewed `eval_holdout` variants is `<= 0`, **OR** (3) CPU deskew latency exceeds `150 ms/page`.
- **Smallest execution needed and hardware / storage requirements:**
  - Trigger false-positive rate and angle recovery error $|\hat{\theta} - \theta_{\text{true}}|$ can be verified on **CPU only** (`0` GPU) as soon as corpus variants exist in `WP-0004 / 004`; end-to-end OCR benefit falsification requires one paired GPU pass over the skewed `eval_holdout` slice.
- **Product relevance, risks, and promotion cost:**
  - Protects extraction reliability on imperfectly scanned technician paperwork without risking clean-document degradation via destructive image filters. Low promotion cost (pure CPU pre-step in `workers/ocr/` with logged trigger telemetry).
