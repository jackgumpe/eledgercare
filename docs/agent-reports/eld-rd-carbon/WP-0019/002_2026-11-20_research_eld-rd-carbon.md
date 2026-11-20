# WP-0019 / 002: Persistent local WinRT full/crop OCR worker and pixel-identity verification

- Report path: `docs/agent-reports/eld-rd-carbon/WP-0019/002_2026-11-20_research_eld-rd-carbon.md`
- Sequence reservation: [INDEX.md WP-0019 / 002](../../../../INDEX.md#wp-0019-windows-ocr-fixed-crop-trial) and [WP-0019 assignment](../../../coordination/WP-0019/assignment.md)
- Category: research
- Author / agent ID: `eld-rd-carbon`
- Actual model / effort: Gemini 4 Carbon (High), Antigravity CLI local subscription session `93c04c29-96da-466c-ae4c-83fe8d01da35`
- Execution environment: Windows 10 Home 26H2 (build `26300.9974`, `26100.1.amd64fre.ge_release.240331-1435`), 64-bit Windows PowerShell `5.1.26100.9818` (CLR `4.0.30319.42000`), read-only Q0 Python `3.12.10` (`Pillow 13.0.0`, `numpy 2.2.6`, `pypdfium2 5.15.2`), CPU-only local `Windows.Media.Ocr`
- Timestamp: 2026-11-20T19:39:00Z
- Repository / branch: `jackgumpe/eledgercare` (private) / `research/wp-0019-winrt-worker` (worktree `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\crop19-carbon`)
- Base revision: `fc15d1bd3af1b4c7dfbfbf1eac2680b9ae9ac1af`
- Deliverable revision: `793fbb7a2a5a3a9354bb753c39b29fcdda959160` (frozen executable source); `44ed3d2171ee49562fcd747bbe5c0f22eea1d1dc` (post-freeze synthetic verification evidence)
- Previous report: [WP-0017 / 002 (`eld-rd-carbon`)](../WP-0017/002_2026-11-18_research_eld-rd-carbon.md); packet predecessor [WP-0018 / 004 (`eld-coordinator`)](../../eld-coordinator/WP-0018/004_2026-11-20_verification_eld-coordinator.md)
- Related or reviewed reports: Upstream baseline reference sources [recognize.ps1](../../../research/WP-0015/astra/recognize.ps1) and [visual.py](../../../research/WP-0015/astra/visual.py)
- Status: ready-for-review
- Next owner: `eld-coordinator` (staged H/A connection) and `eld-rd-reviewer` (`WP-0019 / 003` independent verification)

## Summary

This author verification delivers the frozen WP-0019 persistent local WinRT `en-US` OCR worker in [`docs/research/WP-0019/carbon/engine.py`](../../../research/WP-0019/carbon/engine.py) and [`docs/research/WP-0019/carbon/worker.ps1`](../../../research/WP-0019/carbon/worker.ps1) at candidate commit `793fbb7a2a5a3a9354bb753c39b29fcdda959160`, followed by post-freeze synthetic verification evidence at `44ed3d2171ee49562fcd747bbe5c0f22eea1d1dc`.

`with Worker() as worker:` starts a single persistent 64-bit WinRT process holding one `Windows.Media.Ocr.OcrEngine` (`en-US`), dynamically hashes and inspects current Windows OCR system assets without brittle hardcoded refusals, decodes full-page lossless BMPs at native 1x via `BitmapDecoder.GetSoftwareBitmapAsync(BitmapPixelFormat.Bgra8, BitmapAlphaMode.Ignore)`, retains the decoded `SoftwareBitmap` and its exact BGRA8 pixel buffer in memory, and executes half-open `[left, top, right, bottom)` crops strictly in memory without disk scratch or per-call subprocesses. Before every crop recognition call, the worker reads back the live crop `SoftwareBitmap` buffer to cryptographically prove `bgra_sha256 == source_rectangle_sha256` and invokes the identical `OcrEngine.RecognizeAsync(SoftwareBitmap)` routine used by `full()`. Only synthetic smoke and pixel-identity verification were authorized and executed in this session; no H/A inputs, answer keys, GPU, Baidu, or sealed packets were accessed.

## Objective and acceptance criteria

Per [WP-0019 assignment](../../../coordination/WP-0019/assignment.md):

1. Provide `docs/research/WP-0019/carbon/engine.py` exposing `with Worker() as worker`, `worker.info`, `worker.full(bmp_path)`, and `worker.crop([left, top, right, bottom])` over a single persistent `en-US` WinRT process.
2. Decode complete lossless BMPs at native 1x (`Bgra8`, `Ignore` request) without resizing or pixel modification, retaining the current full-page bitmap in memory for subsequent half-open integer crops with zero image-disk scratch.
3. Route both `full()` and `crop()` through the same recognition operation, returning crop-local word boxes (`lines[{text, words[{text, bbox}]}]`, `text`, `angle`, `recognize_ms`), dimensions, `pixel_format`, `bgra_sha256`, `source_rectangle_sha256`, and `full_bgra_sha256` with explicitly bound byte semantics, proving pre-recognition byte equality on crops.
4. Inspect what `SoftwareBitmap` actually receives on 24-bit and 32-bit BMPs (preserving alpha and never silently altering glyph pixels), measure fresh current Windows OCR asset hashes/versions, and fail closed on invalid dimensions, out-of-bounds rectangles, or malformed BMP payloads.
5. Freeze and push executable source before decisive trials, emit `READY.json` in owned scratch, execute synthetic verification on the frozen source, and publish evidence and canonical report in separate commits.

## Change inventory

### Base-to-deliverable source diff (`fc15d1bd3af1b4c7dfbfbf1eac2680b9ae9ac1af..793fbb7a2a5a3a9354bb753c39b29fcdda959160`)

| Action | Exact path | What changed and why | Relevant symbols |
| --- | --- | --- | --- |
| Added | `docs/research/WP-0019/carbon/__init__.py` | Package export surface for `Worker` and independent BGRA8/BMP verification helpers. | `Worker`, `rgb_to_opaque_bgra_bytes`, `bmp_to_expected_bgra_bytes`, `slice_bgra_rect`, `inspect_bmp_header`, `sha256_hex` |
| Added | `docs/research/WP-0019/carbon/engine.py` | Python `Worker` context manager, fresh Windows OCR asset/version discovery, fail-closed BMP header and half-open crop validation, JSON-over-stdio RPC client, and independent byte-slice helpers. | `Worker`, `Worker.full`, `Worker.crop`, `Worker.close`, `inspect_bmp_header`, `validate_crop_rect`, `BYTE_SEMANTICS` |
| Added | `docs/research/WP-0019/carbon/worker.ps1` | Persistent 64-bit WinRT `en-US` OCR process with compiled C# `WinRtWorkerNative` helper for BMP validation, zero-disk BGRA8 rectangle slicing, pre-recognition `SoftwareBitmap` readback verification, shared `RecognizeAsync`, and ASCII-safe RFC 8259 JSON serialization. | `WinRtWorkerNative`, `ReadSoftwareBitmapBgra8`, `Invoke-SharedRecognize`, `Clear-HeldBitmap`, `Write-WorkerResponse` |
| Added | `docs/research/WP-0019/carbon/test_worker.py` | Self-contained synthetic test suite covering startup/assets, prime-dimension coordinate ramps, BMP row-stride sentinel padding, 24-bit/32-bit alpha semantics, `recognize.ps1` parity, standalone-vs-in-memory crop OCR equality, warm PID/disk-scratch checks, and fail-closed controls. | `run_all_tests`, `_run_worker_suite`, `_build_synthetic_maintenance_bmp` |
| Added | `docs/research/WP-0019/carbon/README.md` | Contract specification, bound BGRA8 byte semantics, usage snippet, and verification command. | — |

### Post-freeze evidence, report, and external scratch inventory

| Action | Exact path or external resource | Commit / persistence | Purpose |
| --- | --- | --- | --- |
| Added | `docs/research/WP-0019/carbon/evidence/smoke-verification.json` | Committed in `44ed3d2171ee49562fcd747bbe5c0f22eea1d1dc` | Post-freeze synthetic verification output generated against `793fbb7a2a5a3a9354bb753c39b29fcdda959160`. |
| Added | `docs/agent-reports/eld-rd-carbon/WP-0019/002_2026-11-20_research_eld-rd-carbon.md` | Committed immediately after `44ed3d2171ee49562fcd747bbe5c0f22eea1d1dc` | This immutable canonical `/002` research report. |
| External scratch | `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\wp0019-data\carbon\READY.json` | Retained in owned scratch (outside Git) | Machine-readable readiness manifest binding `793fbb7a2a5a3a9354bb753c39b29fcdda959160`, `44ed3d2171ee49562fcd747bbe5c0f22eea1d1dc`, API contract, and usage for coordinator staging. |
| External scratch | `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\wp0019-data\carbon\{probe,prefreeze_smoke,prefreeze_smoke2,frozen_smoke}` | Retained in owned scratch (outside Git) | Synthetic test BMPs and WinRT diagnostic scratch directories; zero H/A or product files touched. |

## Decisions and rationale

1. **Observed `SoftwareBitmap` format and alpha behavior (`Bgra8` / `Straight` with preserved bytes)**:
   - Direct inspection of `BitmapDecoder.GetSoftwareBitmapAsync(BitmapPixelFormat.Bgra8, BitmapAlphaMode.Ignore)` (the exact decode call in WP-0015 [`recognize.ps1`](../../../research/WP-0015/astra/recognize.ps1)) showed that WinRT returns a `SoftwareBitmap` with `BitmapPixelFormat == Bgra8` and `BitmapAlphaMode == Straight`:
     - On **24-bit uncompressed RGB BMPs** (`decoder_alpha_mode = "Ignore"`) and **40-byte `BITMAPINFOHEADER` `BI_RGB` 32-bit BGRX BMPs**, WIC populates every pixel's 4th byte with default opaque alpha `255` (`0xFF`) without altering `[B, G, R]`. The resulting top-to-bottom packed BGRA8 buffer matches canonical `rgb_to_opaque_bgra_bytes` SHA-256 digests (`manifest.json["bgra_sha256"]`) byte for byte.
     - On **32-bit `BITMAPV4HEADER` / `V5` `BI_BITFIELDS` alpha BMPs** (`decoder_alpha_mode = "Straight"`), WIC preserves exact `[B, G, R, A]` bytes (tested across `A in {0, 64, 128, 255}`) without premultiplying RGB, whereas `BitmapAlphaMode.Premultiplied` modifies RGB values whenever `A < 255`.
   - Accordingly, `worker.ps1` constructs each in-memory crop `SoftwareBitmap` using `($heldBitmap.BitmapPixelFormat, $cw, $ch, $heldBitmap.BitmapAlphaMode)` plus matching `DpiX`/`DpiY` and copies all 4 channels `[B, G, R, A]` verbatim via `WindowsRuntimeBufferExtensions.AsBuffer` + `CopyFromBuffer`. Both `requested_alpha_mode` (`"Ignore"`), actual `alpha_mode` (`"Straight"`), and measured `alpha_summary` (`min`, `max`, `all_opaque_255`) are recorded in every response.
2. **Pre-recognition cryptographic byte proof and zero disk scratch**:
   - On `crop([left, top, right, bottom])`, `WinRtWorkerNative.SliceRectBgra8` slices the half-open box `[left, right) x [top, bottom)` in memory from the retained full-page BGRA8 buffer (`source_rectangle_sha256`), writes the new `SoftwareBitmap`, and immediately reads the pixels *back* out of the live crop `SoftwareBitmap` via `CopyToBuffer` (`bgra_sha256`). If `bgra_sha256 != source_rectangle_sha256` or raw bytes differ, the worker aborts *before* calling `Invoke-SharedRecognize`.
3. **Fresh Windows OCR asset measurement instead of hardcoded refusal**:
   - `visual.py` previously aborted if `System32/Windows.Media.Ocr.dll` or `OCR/en-us/MsOcrRes.orp` differed from hardcoded constants. `engine.py` computes fresh SHA-256 digests, byte lengths, PE `FileVersion`/`ProductVersion`, and in-process loaded module metadata at startup, recording comparison flags (`historical_wp0015_assets_unchanged`, `historical_wp0015_changed_assets`) in `worker.info` without refusing OS updates. On the current host (`26300.9974`), `System32/Windows.Media.Ocr.dll` (`10.0.26100.9278`, `876,544` bytes, `0db8e48e4f27055f7b7e45412761839b492f5b120b6245edadae61f3fe357ea1`) and `OCR/en-us/MsOcrRes.orp` (`219,754` bytes, `81771d772d77d541e33f3b37e94c81f8a6f87e0b75e933a2389dbcc55715b908`) remain identical to WP-0015.
4. **Fail-closed state and ASCII-safe wire serialization**:
   - Both `engine.py` and `worker.ps1` clear any retained full-page bitmap *before* validating/decoding a new `full(bmp_path)` request, guaranteeing a failed `full()` call can never leave a previous page's bitmap active for subsequent `crop()` calls.
   - `WinRtWorkerNative` serializes OCR JSON in C# with RFC 8259 `\uXXXX` escaping for non-ASCII characters and round-trip `"R"` IEEE-754 formatting, eliminating PowerShell `ConvertTo-Json` array-unwrapping, `MaxJsonLength` caps, and console codepage corruption (verified on `•` `\u2022` bullets).

## Verification

### Executed checks

| Check / exact command | Environment and revision | Actual result | Evidence location |
| --- | --- | --- | --- |
| `& "C:\Users\jackg\eLedgerCare-Q0\WP-0005\venv\Scripts\python.exe" -I -B -W error docs/research/WP-0019/carbon/test_worker.py --scratch "C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\wp0019-data\carbon\frozen_smoke" --evidence-out "docs/research/WP-0019/carbon/evidence/smoke-verification.json"` | Read-only Q0 Python `3.12.10` + 64-bit Windows PowerShell `5.1.26100.9818` on frozen deliverable `793fbb7a2a5a3a9354bb753c39b29fcdda959160` | Exit `0` (`all_passed: true`, zero warnings under `-W error`). Passed all 6 test suites: **T1** startup/fresh asset & PE module inspection (`pid=2684`, `max_dimension=10000`, `startup_ms=604.73`); **T2** `317x211` 2D coordinate ramp full + 15 half-open crops including `1x1` corners, edges, `np.int64` coords, and 1-px boundary-shift sensitivity; **T3** 24-bit row-stride padding (`w in {64,65,66,67}` with `0xA5`/`0x5A` sentinel pad bytes), top-down vs bottom-up equality, 32-bit BGRX->255 alpha, and 32-bit `BITMAPV4HEADER` alpha (`0,64,128,255`) exact `[B,G,R,A]` preservation; **T4** `1600x1200` 300-DPI synthetic maintenance page exact parity with WP-0015 `recognize.ps1`, drop-in `visual.layout` compatibility, and 6/6 non-origin crops matching standalone `full(cropped_bmp)` byte-for-byte and OCR-for-OCR; **T5** persistent warm PID + unchanged OS `process_create_filetime` (`134396770530586532`) and `0` files created/modified in monitored `cwd` and isolated `TEMP`/`TMP` across crops; **T6** 14 invalid crop rectangles, 6 invalid/corrupt/oversized BMP `full()` inputs (confirming retained-bitmap clearing), `fr-FR` rejection, and post-`close()` rejection. | [`smoke-verification.json`](../../../research/WP-0019/carbon/evidence/smoke-verification.json) |
| `git diff --name-status fc15d1bd3af1b4c7dfbfbf1eac2680b9ae9ac1af..793fbb7a2a5a3a9354bb753c39b29fcdda959160` and `git diff --name-status 793fbb7a2a5a3a9354bb753c39b29fcdda959160..44ed3d2171ee49562fcd747bbe5c0f22eea1d1dc` | Git in `crop19-carbon` | Confirmed strictly 5 source files in frozen candidate `793fbb7a2a5a3a9354bb753c39b29fcdda959160` and 1 evidence JSON file in `44ed3d2171ee49562fcd747bbe5c0f22eea1d1dc`; zero edits outside owned paths. | Git history on `research/wp-0019-winrt-worker` |

### Checks not run and why

- **Stage 1 exposed H and A full-page / crop execution, AB/BA paired timing runs, and truth scoring**: Explicitly withheld in this session by kickoff instruction (`no H/A until coordinator`, `Only synthetic smoke is authorized in this session, do not conduct H/A timing concurrently`).
- **Stage 2 fresh synthetic families, Sealed Packet B, GPU/Baidu inference, and product code**: Outside authorized WP-0019 / 002 scope.

## Review map

- Python worker & helpers: [`docs/research/WP-0019/carbon/engine.py`](../../../research/WP-0019/carbon/engine.py) (`Worker`, `inspect_bmp_header`, `validate_crop_rect`, `bmp_to_expected_bgra_bytes`, `slice_bgra_rect`)
- Persistent WinRT PowerShell + C# worker: [`docs/research/WP-0019/carbon/worker.ps1`](../../../research/WP-0019/carbon/worker.ps1) (`WinRtWorkerNative`, `Invoke-SharedRecognize`, `ReadSoftwareBitmapBgra8`)
- Synthetic verification suite & post-freeze evidence: [`docs/research/WP-0019/carbon/test_worker.py`](../../../research/WP-0019/carbon/test_worker.py), [`docs/research/WP-0019/carbon/evidence/smoke-verification.json`](../../../research/WP-0019/carbon/evidence/smoke-verification.json)
- Usage & byte-semantics reference: [`docs/research/WP-0019/carbon/README.md`](../../../research/WP-0019/carbon/README.md)

## Risks, disagreements, and unfinished work

- **No technical blockers or disagreements** within `/002` scope.
- **Downstream observation for callers**: On synthetic identifiers rendered in `test_worker.py` (`Docket 88L1L-631` -> `Docket 88LIL-631`, `1L8O1-493` -> `IL801-493`), WinRT `en-US` character confusions occur identically in both in-memory `crop()` and standalone `full(crop_bmp)` when given the same cropped raster; whether fixed cropping recovers historical H/A criticals without regressions is an empirical Stage 1 question for the paired runner and independent reviewer (`eld-rd-reviewer`).
- **H/A execution**: Pending coordinator admission/connection and `eld-rd-astra` / `eld-rd-reviewer` Stage 1 runs.

## Handoff

- **Branch**: `research/wp-0019-winrt-worker`
- **Base SHA**: `fc15d1bd3af1b4c7dfbfbf1eac2680b9ae9ac1af`
- **Frozen deliverable source SHA**: `793fbb7a2a5a3a9354bb753c39b29fcdda959160`
- **Post-freeze evidence SHA**: `44ed3d2171ee49562fcd747bbe5c0f22eea1d1dc`
- **Canonical report path**: `docs/agent-reports/eld-rd-carbon/WP-0019/002_2026-11-20_research_eld-rd-carbon.md` (report publication SHA provided in the handoff message immediately after committing and pushing this report)
- **Scratch readiness manifest**: `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\wp0019-data\carbon\READY.json`
- **Next owners / actions**: `eld-coordinator` and `eld-rd-astra` may connect staged H/A runs against frozen source `793fbb7a2a5a3a9354bb753c39b29fcdda959160`; `eld-rd-reviewer` (`WP-0019 / 003`) performs independent source, pixel-identity, geometry, and timed verification from isolated reviewer scratch.
- **Publication receipt**: Remote `origin/research/wp-0019-winrt-worker` was verified to contain frozen source `793fbb7a2a5a3a9354bb753c39b29fcdda959160` and evidence `44ed3d2171ee49562fcd747bbe5c0f22eea1d1dc` prior to committing this report; remote confirmation of this report commit follows immediately via `git push` and `git ls-remote` in the final handoff step.
