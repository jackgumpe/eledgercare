# WP-0019 · Persistent Local WinRT Full/Crop OCR Worker (`eld-rd-carbon`)

Worktree-relative Python entry point: `docs/research/WP-0019/carbon/engine.py`.

## Usage

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path("docs/research/WP-0019/carbon").resolve()))
from engine import Worker

with Worker() as worker:
    info = worker.info
    full_res = worker.full(bmp_path)
    crop_res = worker.crop([left, top, right, bottom])
```

## Contract & Byte Semantics

- **Single persistent process**: `Worker()` starts one 64-bit `powershell.exe` child running `worker.ps1` with a single `Windows.Media.Ocr.OcrEngine` initialized for `en-US` (`OcrEngine.TryCreateFromLanguage(Language("en-US"))`). `worker.close()` / `__exit__` closes stdin and reaps the child process cleanly.
- **Fresh Windows OCR asset & version discovery**: `worker.info` measures current SHA-256 digests, byte sizes, and PE file/product versions of `%SystemRoot%/System32/Windows.Media.Ocr.dll` and `%SystemRoot%/OCR/en-us/MsOcrRes.orp` dynamically at startup (recording historical WP-0015 comparison metadata without hardcoded refusal on OS updates), alongside OS build/UBR, `max_dimension` (`OcrEngine.MaxImageDimension`), `pid`, and `process_create_filetime`.
- **Native 1x full-page decode and retention (`worker.full(bmp_path)`)**:
  - Validates the uncompressed Windows BMP header (`BM` signature, `bfSize == file_size`, DIB width/height/planes/bpp/compression, stride payload bounds, `1 <= width, height <= max_dimension`). Never resizes or alters pixels.
  - Decodes via `BitmapDecoder.GetSoftwareBitmapAsync(BitmapPixelFormat.Bgra8, BitmapAlphaMode.Ignore)` (matching `docs/research/WP-0015/astra/recognize.ps1`) and retains the resulting `SoftwareBitmap` and its immutable BGRA8 byte buffer in memory until the next `full()` call or `close()`.
  - Clears any previously retained bitmap *before* validating/decoding a new input so a failed `full()` call never leaves stale page state.
- **In-memory half-open crop (`worker.crop([left, top, right, bottom])`)**:
  - Validates exact integer half-open coordinates `0 <= left < right <= full_width`, `0 <= top < bottom <= full_height` (no floats, booleans, empty, or out-of-bounds boxes).
  - Extracts `source_rectangle` directly in memory from the retained full-page BGRA8 buffer (`x in [left, right)`, `y in [top, bottom)`) with zero temporary image files on disk.
  - Populates an in-memory `SoftwareBitmap` with identical `BitmapPixelFormat` (`Bgra8`), `BitmapAlphaMode` (`Straight`, as returned by WinRT `GetSoftwareBitmapAsync(Bgra8, Ignore)`), and `DpiX`/`DpiY`, reads back the live crop `SoftwareBitmap` bytes, and proves `bgra_sha256 == source_rectangle_sha256` *before* calling `OcrEngine.RecognizeAsync`.
- **Shared recognition operation & return fields**:
  - Both `full()` and `crop()` call the same `Invoke-SharedRecognize` routine around `OcrEngine.RecognizeAsync(SoftwareBitmap)`.
  - Both return `mode`, `text`, `lines[{text, words[{text, bbox}]}]`, `angle`, `recognize_ms`, `call_ms`, `width`, `height`, `full_width`, `full_height`, `rect`, `bgra_sha256`, `source_rectangle_sha256`, `full_bgra_sha256`, `byte_equality_verified`, `pixel_format` (`"Bgra8"`), `requested_alpha_mode` (`"Ignore"`), `alpha_mode`, `alpha_summary`, `dpi_x`, `dpi_y`, `pid`, `language`, and `max_dimension`. Word `bbox` values `[x0, y0, x1, y1]` are always in the recognized input's own pixel coordinates (crop-local on `crop()`).
  - **Bound BGRA8 byte semantics**: `bgra_sha256`, `full_bgra_sha256`, and `source_rectangle_sha256` hash top-to-bottom row-major tightly packed `[B, G, R, A]` bytes (`width * height * 4` bytes, `stride = width * 4`). On 24-bit RGB BMPs, WIC populates default opaque `A = 255` (matching canonical RGB-to-opaque-BGRA8 digests); on 32-bit V4/V5 alpha BMPs, exact `[B, G, R, A]` bytes are preserved without premultiplication.

## Synthetic Verification

```powershell
& "C:\Users\jackg\eLedgerCare-Q0\WP-0005\venv\Scripts\python.exe" -I -B docs/research/WP-0019/carbon/test_worker.py --scratch "C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\wp0019-data\carbon\smoke"
```
