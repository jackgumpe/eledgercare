"""Persistent single-process WinRT en-US full-page and in-memory crop OCR worker.

Implements the WP-0019 / 002 interface (`docs/research/WP-0019/carbon/engine.py`):
- `with Worker() as worker:` starts one persistent 64-bit WinRT `en-US` process.
- `worker.info` exposes engine/OS build, fresh Windows OCR asset digests and PE versions,
  process identity, language, maximum input dimension, decode mode, and byte semantics.
- `worker.full(bmp_path)` decodes the complete lossless BMP at native 1x via
  `BitmapDecoder.GetSoftwareBitmapAsync(BitmapPixelFormat.Bgra8, BitmapAlphaMode.Ignore)`,
  verifies dimensions/header/alpha/byte identity, recognizes with `OcrEngine.RecognizeAsync`,
  and retains the full-page `SoftwareBitmap` and its exact BGRA8 bytes in worker memory.
- `worker.crop([left, top, right, bottom])` slices the half-open integer rectangle
  `[left, top, right, bottom)` in memory from the retained full-page BGRA8 buffer without
  touching disk, populates an in-memory `SoftwareBitmap` with matching format/alpha/DPI,
  proves byte equality on the live crop `SoftwareBitmap` *before* recognition, and invokes
  the exact same `OcrEngine.RecognizeAsync` operation returning crop-local word boxes.
"""

from __future__ import annotations

from collections.abc import Sequence
import hashlib
import json
import math
import operator
import os
from pathlib import Path
import struct
import subprocess
from time import perf_counter_ns
from typing import Any

HERE = Path(__file__).resolve().parent
WORKER_PS1 = HERE / "worker.ps1"

# Retained solely to record whether a host Windows update changed OCR binaries relative to WP-0015.
# Startup measures fresh current SHA-256 digests and NEVER fails on a legitimate OS update.
HISTORICAL_WP0015_ASSET_SHA256: dict[str, str] = {
    "System32/Windows.Media.Ocr.dll": "0db8e48e4f27055f7b7e45412761839b492f5b120b6245edadae61f3fe357ea1",
    "OCR/en-us/MsOcrRes.orp": "81771d772d77d541e33f3b37e94c81f8a6f87e0b75e933a2389dbcc55715b908",
}

BYTE_SEMANTICS: str = (
    "Top-to-bottom row-major tightly packed 4-byte [B, G, R, A] pixels "
    "(length = width * height * 4, row_stride = width * 4) read directly from the "
    "WinRT SoftwareBitmap buffer passed to Windows.Media.Ocr.OcrEngine.RecognizeAsync. "
    "For 24-bit RGB BMPs, WIC GetSoftwareBitmapAsync(Bgra8, Ignore) populates default "
    "opaque alpha A=255 (matching canonical RGB->opaque BGRA8); for 32-bit V4/V5 alpha "
    "BMPs, exact [B, G, R, A] bytes are preserved without premultiplication."
)


def sha256_hex(data: bytes | bytearray | memoryview) -> str:
    """Return lowercase 64-character hex SHA-256 of raw bytes."""
    return hashlib.sha256(data).hexdigest()


def _is_sha256_hex(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _strict_int(value: Any, name: str) -> int:
    if isinstance(value, bool):
        raise TypeError(f"{name} must be an integer, not bool")
    if isinstance(value, float):
        raise TypeError(f"{name} must be an integer, not float")
    try:
        return operator.index(value)
    except TypeError as exc:
        raise TypeError(f"{name} must be an integer, got {type(value).__name__}") from exc


def rgb_to_opaque_bgra_bytes(rgb_bytes: bytes, width: int, height: int) -> bytes:
    """Convert tightly packed top-to-bottom RGB24 bytes into canonical opaque BGRA8 bytes."""
    w = _strict_int(width, "width")
    h = _strict_int(height, "height")
    if w <= 0 or h <= 0:
        raise ValueError(f"Invalid dimensions {w}x{h}")
    expected = w * h * 3
    if len(rgb_bytes) != expected:
        raise ValueError(f"RGB byte length {len(rgb_bytes)} != {expected}")
    try:
        import numpy as np

        rgb = np.frombuffer(rgb_bytes, dtype=np.uint8).reshape((h, w, 3))
        bgra = np.empty((h, w, 4), dtype=np.uint8)
        bgra[..., 0] = rgb[..., 2]
        bgra[..., 1] = rgb[..., 1]
        bgra[..., 2] = rgb[..., 0]
        bgra[..., 3] = 255
        return bgra.tobytes()
    except ImportError:
        out = bytearray(w * h * 4)
        dst = 0
        for src in range(0, expected, 3):
            out[dst] = rgb_bytes[src + 2]
            out[dst + 1] = rgb_bytes[src + 1]
            out[dst + 2] = rgb_bytes[src]
            out[dst + 3] = 255
            dst += 4
        return bytes(out)


def slice_bgra_rect(
    full_bgra: bytes | bytearray | memoryview,
    full_width: int,
    full_height: int,
    rect: Sequence[int],
) -> bytes:
    """Independently slice half-open `[left, top, right, bottom)` from packed BGRA8 bytes."""
    fw = _strict_int(full_width, "full_width")
    fh = _strict_int(full_height, "full_height")
    left, top, right, bottom = validate_crop_rect(rect, fw, fh)
    expected = fw * fh * 4
    if len(full_bgra) != expected:
        raise ValueError(f"Full BGRA8 byte length {len(full_bgra)} != {expected}")
    cw = right - left
    ch = bottom - top
    row_bytes = cw * 4
    src_stride = fw * 4
    mv = memoryview(full_bgra)
    out = bytearray(row_bytes * ch)
    for r in range(ch):
        s0 = (top + r) * src_stride + left * 4
        d0 = r * row_bytes
        out[d0 : d0 + row_bytes] = mv[s0 : s0 + row_bytes]
    return bytes(out)


def inspect_bmp_header(bmp_path: str | os.PathLike[str], *, max_dimension: int | None = None) -> dict[str, Any]:
    """Validate lossless uncompressed Windows BMP file header and payload bounds."""
    if isinstance(bmp_path, (bool, int, float, bytes)):
        raise TypeError(f"bmp_path must be str or PathLike, got {type(bmp_path).__name__}")
    path = Path(bmp_path)
    if not path.exists():
        raise FileNotFoundError(f"BMP file does not exist: {path}")
    if not path.is_file():
        raise ValueError(f"BMP path is not a regular file: {path}")

    file_size = path.stat().st_size
    if file_size < 54:
        raise ValueError(f"BMP file shorter than 54-byte header ({file_size} bytes): {path}")

    with path.open("rb") as handle:
        hdr = handle.read(min(138, file_size))

    if len(hdr) < 54 or hdr[:2] != b"BM":
        raise ValueError(f"File does not begin with BMP 'BM' signature: {path}")

    bf_size, _r1, _r2, bf_off_bits = struct.unpack_from("<IHHI", hdr, 2)
    dib_size = struct.unpack_from("<I", hdr, 14)[0]
    if dib_size < 40:
        raise ValueError(f"Unsupported BMP DIB header size {dib_size}: {path}")
    if bf_size != file_size:
        raise ValueError(f"BMP header bfSize ({bf_size}) != actual file size ({file_size}): {path}")
    if 14 + dib_size > bf_off_bits or bf_off_bits > file_size:
        raise ValueError(f"BMP pixel offset bfOffBits ({bf_off_bits}) out of range for file size {file_size}")

    bi_width, bi_height, bi_planes, bi_bpp, bi_compression = struct.unpack_from("<iiHHI", hdr, 18)
    if bi_width <= 0 or bi_height == 0 or bi_height == -(1 << 31):
        raise ValueError(f"Invalid BMP dimensions width={bi_width}, height={bi_height}")
    abs_height = abs(bi_height)
    if max_dimension is not None and (bi_width > max_dimension or abs_height > max_dimension):
        raise ValueError(
            f"BMP dimensions {bi_width}x{abs_height} exceed max_dimension {max_dimension}"
        )
    if bi_planes != 1:
        raise ValueError(f"Invalid BMP biPlanes={bi_planes}; expected 1")
    if bi_bpp not in (8, 24, 32):
        raise ValueError(f"Unsupported BMP bits_per_pixel={bi_bpp}; expected 8, 24, or 32")
    if not (bi_compression == 0 or (bi_compression == 3 and bi_bpp == 32 and dib_size >= 56)):
        raise ValueError(f"Unsupported or compressed BMP biCompression={bi_compression}")

    row_stride = ((bi_width * bi_bpp + 31) // 32) * 4
    required_payload = row_stride * abs_height
    if bf_off_bits + required_payload > file_size:
        raise ValueError(
            f"Truncated BMP pixel payload: need {bf_off_bits + required_payload} bytes, got {file_size}"
        )

    alpha_mask = 0
    if bi_bpp == 32 and bi_compression == 3 and len(hdr) >= 70:
        r_mask, g_mask, b_mask, alpha_mask = struct.unpack_from("<IIII", hdr, 54)
        if (r_mask, g_mask, b_mask) != (0x00FF0000, 0x0000FF00, 0x000000FF):
            raise ValueError("Unsupported 32-bit BI_BITFIELDS channel masks; expected standard BGRA8 masks")

    return {
        "path": str(path.resolve()),
        "file_size": file_size,
        "bf_size": bf_size,
        "bf_off_bits": bf_off_bits,
        "dib_size": dib_size,
        "width": bi_width,
        "height": abs_height,
        "top_down": bi_height < 0,
        "bits_per_pixel": bi_bpp,
        "compression": bi_compression,
        "alpha_mask": alpha_mask,
        "row_stride": row_stride,
    }


def bmp_to_expected_bgra_bytes(bmp_path: str | os.PathLike[str]) -> bytes:
    """Independently decode an uncompressed 24-bit or 32-bit BMP into expected WinRT BGRA8 bytes."""
    meta = inspect_bmp_header(bmp_path)
    raw = Path(meta["path"]).read_bytes()
    w = meta["width"]
    h = meta["height"]
    bpp = meta["bits_per_pixel"]
    stride = meta["row_stride"]
    off = meta["bf_off_bits"]
    top_down = meta["top_down"]

    import numpy as np

    payload = np.frombuffer(raw, dtype=np.uint8, offset=off, count=stride * h).reshape((h, stride))
    if not top_down:
        payload = payload[::-1]

    if bpp == 24:
        bgr = payload[:, : w * 3].reshape((h, w, 3))
        out = np.empty((h, w, 4), dtype=np.uint8)
        out[..., :3] = bgr
        out[..., 3] = 255
        return out.tobytes()
    if bpp == 32:
        bgra = payload[:, : w * 4].reshape((h, w, 4)).copy()
        if meta["compression"] == 0 or meta["alpha_mask"] == 0:
            bgra[..., 3] = 255
        return bgra.tobytes()
    raise ValueError(f"bmp_to_expected_bgra_bytes supports 24-bit and 32-bit BMPs, got {bpp}-bit")


def validate_crop_rect(rect: Sequence[int], full_width: int, full_height: int) -> tuple[int, int, int, int]:
    """Validate half-open integer rectangle `[left, top, right, bottom)` against `(full_width, full_height)`."""
    if not isinstance(rect, (list, tuple)):
        raise TypeError(f"crop rect must be a 4-element list or tuple, got {type(rect).__name__}")
    if len(rect) != 4:
        raise ValueError(f"crop rect must have exactly 4 elements [left, top, right, bottom], got {len(rect)}")
    left = _strict_int(rect[0], "left")
    top = _strict_int(rect[1], "top")
    right = _strict_int(rect[2], "right")
    bottom = _strict_int(rect[3], "bottom")
    if left < 0 or top < 0 or right <= left or bottom <= top or right > full_width or bottom > full_height:
        raise ValueError(
            f"Invalid half-open crop rect [{left}, {top}, {right}, {bottom}] "
            f"for retained bitmap {full_width}x{full_height}"
        )
    return left, top, right, bottom


def _discover_windows_ocr_assets(win_root: Path) -> tuple[dict[str, str], dict[str, dict[str, Any]]]:
    required_rels = ["System32/Windows.Media.Ocr.dll", "OCR/en-us/MsOcrRes.orp"]
    extra_dir = win_root / "OCR/en-us"
    rels: list[str] = list(required_rels)
    if extra_dir.exists():
        for item in sorted(extra_dir.rglob("*")):
            if item.is_file():
                rel = str(item.relative_to(win_root)).replace("\\", "/")
                if rel not in rels:
                    rels.append(rel)

    asset_sha256: dict[str, str] = {}
    asset_details: dict[str, dict[str, Any]] = {}
    for rel in rels:
        p = win_root / rel
        if not p.is_file():
            raise FileNotFoundError(f"Required Windows OCR asset not found: {p}")
        data = p.read_bytes()
        digest = sha256_hex(data)
        asset_sha256[rel] = digest
        asset_details[rel] = {
            "path": str(p),
            "size_bytes": len(data),
            "sha256": digest,
        }
    return asset_sha256, asset_details


def _validate_ocr_lines(lines: Any) -> None:
    if not isinstance(lines, list):
        raise RuntimeError(f"OCR response 'lines' must be a list, got {type(lines).__name__}")
    for line in lines:
        if not isinstance(line, dict) or set(line.keys()) != {"text", "words"}:
            raise RuntimeError("Invalid OCR line structure")
        if not isinstance(line["text"], str) or not isinstance(line["words"], list):
            raise RuntimeError("Invalid OCR line text/words types")
        for word in line["words"]:
            if not isinstance(word, dict) or set(word.keys()) != {"text", "bbox"}:
                raise RuntimeError("Invalid OCR word structure")
            bbox = word["bbox"]
            if not isinstance(word["text"], str) or not isinstance(bbox, list) or len(bbox) != 4:
                raise RuntimeError("Invalid OCR word text/bbox types")
            coords: list[float] = []
            for v in bbox:
                if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(float(v)):
                    raise RuntimeError(f"Non-finite OCR word bbox coordinate: {v!r}")
                coords.append(float(v))
            if coords[2] < coords[0] or coords[3] < coords[1]:
                raise RuntimeError(f"Inverted OCR word bbox: {bbox!r}")


class Worker:
    """Single persistent en-US WinRT OCR worker supporting `full(bmp_path)` and in-memory `crop(rect)`."""

    def __init__(
        self,
        *,
        language: str = "en-US",
        cwd: str | os.PathLike[str] | None = None,
        timeout_s: float = 60.0,
    ) -> None:
        if language != "en-US":
            raise ValueError(f"Only 'en-US' is authorized for WP-0019, got {language!r}")
        if timeout_s <= 0:
            raise ValueError("timeout_s must be positive")
        if not WORKER_PS1.is_file():
            raise FileNotFoundError(f"Missing WinRT worker script: {WORKER_PS1}")

        self._closed = False
        self._retained: dict[str, Any] | None = None
        self._timeout_s = float(timeout_s)

        start_ns = perf_counter_ns()
        sys_root_env = os.environ.get("SystemRoot")
        if not sys_root_env:
            raise RuntimeError("SystemRoot environment variable is not set")
        win_root = Path(sys_root_env)
        powershell_exe = win_root / "System32/WindowsPowerShell/v1.0/powershell.exe"
        if not powershell_exe.is_file():
            raise FileNotFoundError(f"64-bit Windows PowerShell not found: {powershell_exe}")

        asset_sha256, asset_details = _discover_windows_ocr_assets(win_root)
        engine_py_sha256 = sha256_hex(Path(__file__).read_bytes())
        worker_ps1_sha256 = sha256_hex(WORKER_PS1.read_bytes())

        cmd = [
            str(powershell_exe),
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(WORKER_PS1),
        ]
        self._child = subprocess.Popen(
            cmd,
            cwd=str(Path(cwd).resolve()) if cwd is not None else None,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="strict",
            bufsize=1,
        )
        try:
            assert self._child.stdout is not None
            hello_line = self._child.stdout.readline()
            if not hello_line:
                err_out = ""
                if self._child.stderr is not None:
                    err_out = self._child.stderr.read()
                raise RuntimeError(f"WinRT worker exited during startup: {err_out.strip()}")
            hello = json.loads(hello_line)
            if hello.get("error"):
                raise RuntimeError(f"WinRT worker startup error: {hello['error']}")
            if hello.get("language") != "en-US":
                raise RuntimeError(f"WinRT worker language mismatch: {hello.get('language')!r}")
            if hello.get("pid") != self._child.pid:
                raise RuntimeError(
                    f"WinRT worker PID mismatch: handshake={hello.get('pid')} vs popen={self._child.pid}"
                )
            if hello.get("is_64bit_process") is not True:
                raise RuntimeError("WinRT worker is not running as a 64-bit process")
            max_dim = hello.get("max_dimension")
            if isinstance(max_dim, bool) or not isinstance(max_dim, int) or max_dim <= 0:
                raise RuntimeError(f"Invalid WinRT MaxImageDimension: {max_dim!r}")

            ps_versions = hello.get("asset_versions") or {}
            for rel, meta in asset_details.items():
                ver = ps_versions.get(rel) or {}
                meta["file_version"] = ver.get("file_version")
                meta["product_version"] = ver.get("product_version")
                meta["file_description"] = ver.get("file_description")

            changed_historical = sorted(
                rel
                for rel, hist_sha in HISTORICAL_WP0015_ASSET_SHA256.items()
                if asset_sha256.get(rel) != hist_sha
            )
            dll_ver = asset_details["System32/Windows.Media.Ocr.dll"].get("product_version")
            startup_ms = (perf_counter_ns() - start_ns) / 1e6

            self.info: dict[str, Any] = {
                "engine": "Windows.Media.Ocr.OcrEngine",
                "engine_version": dll_ver,
                "language": hello["language"],
                "language_display_name": hello.get("language_display_name"),
                "max_dimension": max_dim,
                "pid": int(hello["pid"]),
                "process_create_filetime": int(hello["process_create_filetime"]),
                "python_pid": os.getpid(),
                "is_64bit_process": True,
                "powershell_executable": str(powershell_exe),
                "powershell_version": hello.get("powershell_version"),
                "clr_version": hello.get("clr_version"),
                "os_build": hello.get("os"),
                "asset_sha256": asset_sha256,
                "assets": asset_details,
                "historical_wp0015_asset_sha256": dict(HISTORICAL_WP0015_ASSET_SHA256),
                "historical_wp0015_assets_unchanged": len(changed_historical) == 0,
                "historical_wp0015_changed_assets": changed_historical,
                "loaded_ocr_module": hello.get("loaded_ocr_module"),
                "worker_script": str(WORKER_PS1),
                "worker_script_sha256": worker_ps1_sha256,
                "engine_py_sha256": engine_py_sha256,
                "decode_mode": {
                    "scale": "1x",
                    "requested_pixel_format": "Bgra8",
                    "requested_alpha_mode": "Ignore",
                    "crop_storage": "in_memory_software_bitmap",
                    "shared_recognition_operation": "Windows.Media.Ocr.OcrEngine.RecognizeAsync(SoftwareBitmap)",
                },
                "byte_semantics": BYTE_SEMANTICS,
                "startup_ms": startup_ms,
            }
        except BaseException:
            self.close()
            raise

    def __enter__(self) -> Worker:
        if self._closed:
            raise RuntimeError("Cannot enter a closed Worker")
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()

    def _ensure_alive(self) -> None:
        if self._closed:
            raise RuntimeError("Worker is closed")
        rc = self._child.poll()
        if rc is not None:
            raise RuntimeError(f"Persistent WinRT worker process (pid={self.info['pid']}) exited with code {rc}")

    def _rpc(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._ensure_alive()
        assert self._child.stdin is not None and self._child.stdout is not None
        wire = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), allow_nan=False) + "\n"
        self._child.stdin.write(wire)
        self._child.stdin.flush()
        line = self._child.stdout.readline()
        if not line:
            err_tail = ""
            if self._child.stderr is not None:
                try:
                    err_tail = self._child.stderr.read().strip()
                except Exception:
                    err_tail = ""
            raise RuntimeError(f"WinRT worker EOF during {payload.get('op')!r}: {err_tail}")
        resp = json.loads(line)
        if not isinstance(resp, dict):
            raise RuntimeError("WinRT worker returned non-object JSON payload")
        if resp.get("error"):
            raise RuntimeError(f"WinRT worker {payload.get('op')} failure: {resp['error']}")
        if resp.get("pid") != self.info["pid"]:
            raise RuntimeError(
                f"Worker PID changed unexpectedly: expected {self.info['pid']}, got {resp.get('pid')}"
            )
        if resp.get("language") != "en-US":
            raise RuntimeError(f"Worker language mismatch: {resp.get('language')!r}")
        return resp

    def full(self, bmp_path: str | os.PathLike[str]) -> dict[str, Any]:
        """Recognize complete lossless BMP at 1x and retain its `SoftwareBitmap` for subsequent `crop()` calls."""
        self._ensure_alive()
        # Clear retained state up-front so a failed full() never leaves a previous page's bitmap active.
        self._retained = None

        call_begin_ns = perf_counter_ns()
        hdr = inspect_bmp_header(bmp_path, max_dimension=self.info["max_dimension"])
        resp = self._rpc({"op": "full", "path": hdr["path"]})
        call_ms = (perf_counter_ns() - call_begin_ns) / 1e6

        if resp.get("mode") != "full":
            raise RuntimeError(f"Expected mode='full', got {resp.get('mode')!r}")
        if resp.get("pixel_format") != "Bgra8":
            raise RuntimeError(f"Expected pixel_format='Bgra8', got {resp.get('pixel_format')!r}")
        if resp.get("width") != hdr["width"] or resp.get("height") != hdr["height"]:
            raise RuntimeError(
                f"Worker full() dimensions {resp.get('width')}x{resp.get('height')} "
                f"disagree with BMP header {hdr['width']}x{hdr['height']}"
            )
        if resp.get("full_width") != hdr["width"] or resp.get("full_height") != hdr["height"]:
            raise RuntimeError("Worker full_width/full_height mismatch")
        if resp.get("rect") != [0, 0, hdr["width"], hdr["height"]]:
            raise RuntimeError(f"Unexpected full rect: {resp.get('rect')!r}")

        bgra_sha = resp.get("bgra_sha256")
        full_sha = resp.get("full_bgra_sha256")
        src_sha = resp.get("source_rectangle_sha256")
        if not (_is_sha256_hex(bgra_sha) and bgra_sha == full_sha == src_sha):
            raise RuntimeError("Invalid or mismatched BGRA8 SHA-256 digests on full()")
        if resp.get("byte_equality_verified") is not True:
            raise RuntimeError("Worker did not confirm byte_equality_verified on full()")
        alpha_summary = resp.get("alpha_summary") or {}
        if hdr["bits_per_pixel"] in (8, 24) and alpha_summary.get("all_opaque_255") is not True:
            raise RuntimeError(f"Expected opaque 255 alpha for {hdr['bits_per_pixel']}-bit BMP")
        if not isinstance(resp.get("text"), str):
            raise RuntimeError("Missing string 'text' in OCR response")
        angle = resp.get("angle")
        if angle is not None and (isinstance(angle, bool) or not isinstance(angle, (int, float)) or not math.isfinite(float(angle))):
            raise RuntimeError(f"Invalid OCR angle: {angle!r}")
        _validate_ocr_lines(resp.get("lines"))

        resp["call_ms"] = call_ms
        self._retained = {
            "bmp_path": hdr["path"],
            "width": hdr["width"],
            "height": hdr["height"],
            "bgra_sha256": bgra_sha,
            "pixel_format": resp["pixel_format"],
            "alpha_mode": resp["alpha_mode"],
            "dpi_x": resp["dpi_x"],
            "dpi_y": resp["dpi_y"],
        }
        return resp

    def crop(self, rect: Sequence[int]) -> dict[str, Any]:
        """Recognize half-open `[left, top, right, bottom)` in memory on the retained full-page bitmap."""
        self._ensure_alive()
        if self._retained is None:
            raise RuntimeError("No full-page bitmap is currently retained; call worker.full(bmp_path) first")

        call_begin_ns = perf_counter_ns()
        full_w = self._retained["width"]
        full_h = self._retained["height"]
        left, top, right, bottom = validate_crop_rect(rect, full_w, full_h)
        cw = right - left
        ch = bottom - top

        resp = self._rpc({
            "op": "crop",
            "left": left,
            "top": top,
            "right": right,
            "bottom": bottom,
        })
        call_ms = (perf_counter_ns() - call_begin_ns) / 1e6

        if resp.get("mode") != "crop":
            raise RuntimeError(f"Expected mode='crop', got {resp.get('mode')!r}")
        if resp.get("pixel_format") != "Bgra8":
            raise RuntimeError(f"Expected pixel_format='Bgra8', got {resp.get('pixel_format')!r}")
        if resp.get("alpha_mode") != self._retained["alpha_mode"]:
            raise RuntimeError(
                f"Crop alpha_mode {resp.get('alpha_mode')!r} != retained {self._retained['alpha_mode']!r}"
            )
        if resp.get("width") != cw or resp.get("height") != ch:
            raise RuntimeError(
                f"Crop dimensions {resp.get('width')}x{resp.get('height')} != expected {cw}x{ch}"
            )
        if resp.get("full_width") != full_w or resp.get("full_height") != full_h:
            raise RuntimeError("Crop full_width/full_height mismatch against retained bitmap")
        if resp.get("rect") != [left, top, right, bottom]:
            raise RuntimeError(f"Crop rect mismatch: {resp.get('rect')!r}")

        bgra_sha = resp.get("bgra_sha256")
        src_sha = resp.get("source_rectangle_sha256")
        full_sha = resp.get("full_bgra_sha256")
        if not (_is_sha256_hex(bgra_sha) and _is_sha256_hex(src_sha) and _is_sha256_hex(full_sha)):
            raise RuntimeError("Invalid SHA-256 format in crop() response")
        if bgra_sha != src_sha:
            raise RuntimeError(
                f"Crop SoftwareBitmap bgra_sha256 ({bgra_sha}) != source_rectangle_sha256 ({src_sha})"
            )
        if full_sha != self._retained["bgra_sha256"]:
            raise RuntimeError(
                f"Crop full_bgra_sha256 ({full_sha}) != retained full page ({self._retained['bgra_sha256']})"
            )
        if resp.get("byte_equality_verified") is not True:
            raise RuntimeError("Worker did not confirm pre-recognition byte_equality_verified on crop()")
        if not isinstance(resp.get("text"), str):
            raise RuntimeError("Missing string 'text' in crop OCR response")
        angle = resp.get("angle")
        if angle is not None and (isinstance(angle, bool) or not isinstance(angle, (int, float)) or not math.isfinite(float(angle))):
            raise RuntimeError(f"Invalid crop OCR angle: {angle!r}")
        _validate_ocr_lines(resp.get("lines"))

        resp["call_ms"] = call_ms
        return resp

    def close(self) -> None:
        """Idempotently close stdin and terminate the persistent WinRT child process."""
        if self._closed:
            return
        self._closed = True
        self._retained = None
        child = getattr(self, "_child", None)
        if child is None:
            return
        try:
            if child.stdin is not None and not child.stdin.closed:
                child.stdin.close()
        except Exception:
            pass
        try:
            child.wait(timeout=4.0)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()
        finally:
            for pipe in (child.stdout, child.stderr):
                if pipe is not None and not pipe.closed:
                    try:
                        pipe.close()
                    except Exception:
                        pass
