"""Synthetic smoke, pixel-identity, alpha-preservation, warm-persistence, and fail-closed tests.

Authorized scope: synthetic constructed bitmaps in owned scratch only.
Does NOT read or execute H/A fixtures, answer keys, GPU, Baidu, or sealed packets.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))

from engine import (  # noqa: E402
    HISTORICAL_WP0015_ASSET_SHA256,
    Worker,
    bmp_to_expected_bgra_bytes,
    inspect_bmp_header,
    rgb_to_opaque_bgra_bytes,
    sha256_hex,
    slice_bgra_rect,
)


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    win = Path(os.environ["SystemRoot"]) / "Fonts"
    for name in ("consola.ttf", "arial.ttf", "segoeui.ttf", "cour.ttf"):
        candidate = win / name
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def _write_raw_bmp24_with_sentinel_padding(
    path: Path,
    rgb: np.ndarray,
    *,
    sentinel_byte: int = 0xA5,
    top_down: bool = False,
) -> None:
    """Write an uncompressed 24-bit BMP with explicit non-zero bytes in per-row stride padding."""
    h, w, c = rgb.shape
    assert c == 3
    row_bytes = w * 3
    stride = ((w * 24 + 31) // 32) * 4
    pad_len = stride - row_bytes
    ordered = rgb if top_down else rgb[::-1]
    bgr = ordered[..., ::-1]

    rows = bytearray()
    pad = bytes([sentinel_byte] * pad_len)
    for r in range(h):
        rows.extend(bgr[r].tobytes())
        if pad_len:
            rows.extend(pad)

    bf_size = 54 + len(rows)
    bi_height = -h if top_down else h
    bfh = struct.pack("<2sIHHI", b"BM", bf_size, 0, 0, 54)
    dib = struct.pack(
        "<IiiHHIIiiII", 40, w, bi_height, 1, 24, 0, len(rows), 11811, 11811, 0, 0
    )
    path.write_bytes(bfh + dib + bytes(rows))


def _write_raw_bmp32_bi_rgb(path: Path, bgra: np.ndarray) -> None:
    """Write a 40-byte BITMAPINFOHEADER 32bpp BI_RGB (BGRX) BMP."""
    h, w, c = bgra.shape
    assert c == 4
    payload = bgra[::-1].tobytes()
    bfh = struct.pack("<2sIHHI", b"BM", 54 + len(payload), 0, 0, 54)
    dib = struct.pack("<IiiHHIIiiII", 40, w, h, 1, 32, 0, len(payload), 11811, 11811, 0, 0)
    path.write_bytes(bfh + dib + payload)


def _write_raw_bmp32_v4_alpha(path: Path, bgra: np.ndarray) -> None:
    """Write a 108-byte BITMAPV4HEADER 32bpp BI_BITFIELDS BMP with explicit alpha channel mask."""
    h, w, c = bgra.shape
    assert c == 4
    payload = bgra[::-1].tobytes()
    bfh = struct.pack("<2sIHHI", b"BM", 14 + 108 + len(payload), 0, 0, 14 + 108)
    b4h = struct.pack(
        "<IiiHHIIiiIIIIIII36sIII",
        108,
        w,
        h,
        1,
        32,
        3,
        len(payload),
        11811,
        11811,
        0,
        0,
        0x00FF0000,
        0x0000FF00,
        0x000000FF,
        0xFF000000,
        0x73524742,
        b"\x00" * 36,
        0,
        0,
        0,
    )
    path.write_bytes(bfh + b4h + payload)


def _build_synthetic_maintenance_bmp(path: Path) -> tuple[np.ndarray, dict[str, list[int]]]:
    """Construct a synthetic 300-DPI maintenance form with prose, bullet, and ruled grid."""
    w, h = 1600, 1200
    img = Image.new("RGB", (w, h), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    font_hdr = _load_font(34)
    font_body = _load_font(28)

    draw.text((90, 70), "MAINTENANCE WORK RECORD", fill=(0, 0, 0), font=font_hdr)
    draw.text((90, 130), "Docket 88L1L-631", fill=(0, 0, 0), font=font_body)
    draw.text((90, 180), "Unit • PUMP-409 • Status READY", fill=(0, 0, 0), font=font_body)

    # Ruled 3-row x 3-col table at x=[90, 520, 1020, 1480], y=[280, 360, 440, 520, 600]
    xs = [90, 520, 1020, 1480]
    ys = [280, 360, 440, 520, 600]
    for x in xs:
        draw.line([(x, ys[0]), (x, ys[-1])], fill=(0, 0, 0), width=3)
    for y in ys:
        draw.line([(xs[0], y), (xs[-1], y)], fill=(0, 0, 0), width=3)

    rows = [
        ("Inspection ID", "Component", "Reading"),
        ("1L8O1-493", "VALVE-A1", "142.75"),
        ("0I8O1-139", "SEAL-B2", "0.085"),
        ("99204-771", "FILTER-C9", "PASS"),
    ]
    for r_idx, row_vals in enumerate(rows):
        y_top = ys[r_idx] + 22
        for c_idx, val in enumerate(row_vals):
            x_left = xs[c_idx] + 20
            draw.text((x_left, y_top), val, fill=(0, 0, 0), font=font_body)

    draw.text((90, 690), "Technician Signoff: J. CARTER   Date: 2026-11-20", fill=(0, 0, 0), font=font_body)
    img.save(path, format="BMP", dpi=(300, 300))

    regions = {
        "docket_prose_padded": [74, 118, 560, 172],
        "unicode_bullet_line": [74, 168, 860, 224],
        "cell_r1_c0_inset": [xs[0] + 6, ys[1] + 6, xs[1] - 6, ys[2] - 6],
        "cell_r2_c0_inset": [xs[0] + 6, ys[2] + 6, xs[1] - 6, ys[3] - 6],
        "cell_r1_c2_inset": [xs[2] + 6, ys[1] + 6, xs[3] - 6, ys[2] - 6],
        "footer_prose": [74, 676, 1150, 742],
    }
    return np.asarray(img), regions


def _run_original_wp0015_recognize_ps1(bmp_path: Path) -> dict[str, Any]:
    orig_ps1 = REPO_ROOT / "docs/research/WP-0015/astra/recognize.ps1"
    ps_exe = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    proc = subprocess.Popen(
        [str(ps_exe), "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(orig_ps1)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="strict",
    )
    try:
        assert proc.stdin is not None and proc.stdout is not None
        _hdr = json.loads(proc.stdout.readline())
        proc.stdin.write(json.dumps({"path": str(bmp_path)}) + "\n")
        proc.stdin.flush()
        res = json.loads(proc.stdout.readline())
        if res.get("error"):
            raise RuntimeError(res["error"])
        return res
    finally:
        if proc.stdin is not None and not proc.stdin.closed:
            proc.stdin.close()
        proc.wait(timeout=4)
        for pipe in (proc.stdout, proc.stderr):
            if pipe is not None and not pipe.closed:
                pipe.close()


def run_all_tests(scratch_dir: Path) -> dict[str, Any]:
    scratch_dir = scratch_dir.resolve()
    scratch_dir.mkdir(parents=True, exist_ok=True)
    summary: dict[str, Any] = {
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "git_head": subprocess.check_output(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"], text=True
        ).strip(),
        "python_executable": sys.executable,
        "python_version": sys.version,
        "tests": {},
    }

    # --- T1 & T2 & T3 & T4 & T5 & T6 inside monitored persistent worker ---
    monitored_cwd = scratch_dir / "worker_empty_cwd"
    monitored_cwd.mkdir(parents=True, exist_ok=True)
    isolated_temp = scratch_dir / "worker_isolated_temp"
    isolated_temp.mkdir(parents=True, exist_ok=True)

    # Verify spec_from_file_location loading (needed when callers load across 'WP-0019' hyphenated path).
    spec = importlib.util.spec_from_file_location("wp0019_carbon_engine", HERE / "engine.py")
    assert spec is not None and spec.loader is not None
    spec_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(spec_mod)
    assert hasattr(spec_mod, "Worker")

    # Non-en-US language must fail closed before spawning a worker.
    bad_lang_rejected = False
    try:
        Worker(language="fr-FR")
    except ValueError:
        bad_lang_rejected = True
    assert bad_lang_rejected

    orig_temp = os.environ.get("TEMP")
    orig_tmp = os.environ.get("TMP")
    os.environ["TEMP"] = str(isolated_temp)
    os.environ["TMP"] = str(isolated_temp)
    try:
        return _run_worker_suite(scratch_dir, monitored_cwd, isolated_temp, summary)
    finally:
        if orig_temp is None:
            os.environ.pop("TEMP", None)
        else:
            os.environ["TEMP"] = orig_temp
        if orig_tmp is None:
            os.environ.pop("TMP", None)
        else:
            os.environ["TMP"] = orig_tmp


def _snapshot_dir(folder: Path) -> list[tuple[str, int, int]]:
    out: list[tuple[str, int, int]] = []
    for p in sorted(folder.rglob("*")):
        st = p.stat()
        out.append((str(p.relative_to(folder)).replace("\\", "/"), st.st_size, st.st_mtime_ns))
    return out


def _run_worker_suite(
    scratch_dir: Path,
    monitored_cwd: Path,
    isolated_temp: Path,
    summary: dict[str, Any],
) -> dict[str, Any]:
    with Worker(cwd=monitored_cwd) as worker:
        info = worker.info
        assert info["engine"] == "Windows.Media.Ocr.OcrEngine"
        assert info["language"] == "en-US"
        assert info["is_64bit_process"] is True
        assert isinstance(info["max_dimension"], int) and info["max_dimension"] >= 4096
        assert isinstance(info["pid"], int) and info["pid"] > 0
        assert isinstance(info["process_create_filetime"], int) and info["process_create_filetime"] > 0

        # Verify fresh asset hashes match independent disk reads (never relying on hardcoded constants).
        win_root = Path(os.environ["SystemRoot"])
        for rel, got_sha in info["asset_sha256"].items():
            expected_sha = sha256_hex((win_root / rel).read_bytes())
            assert got_sha == expected_sha, f"Fresh asset digest mismatch for {rel}"
        assert set(HISTORICAL_WP0015_ASSET_SHA256.keys()).issubset(info["asset_sha256"].keys())

        summary["worker_info"] = info
        summary["tests"]["T1_startup_and_fresh_assets"] = {
            "passed": True,
            "pid": info["pid"],
            "max_dimension": info["max_dimension"],
            "engine_version": info["engine_version"],
            "historical_wp0015_assets_unchanged": info["historical_wp0015_assets_unchanged"],
            "startup_ms": round(info["startup_ms"], 3),
        }

        # --- T6a: crop() before any full() fails closed ---
        failed_pre_full = False
        try:
            worker.crop([0, 0, 10, 10])
        except RuntimeError:
            failed_pre_full = True
        assert failed_pre_full, "crop() before full() must fail closed"

        # --- T2: 2D prime-dimension coordinate/channel ramp & non-origin crops ---
        rw, rh = 317, 211
        ys_grid, xs_grid = np.mgrid[0:rh, 0:rw]
        ramp_rgb = np.stack(
            [
                ((xs_grid * 37 + ys_grid * 13 + 7) % 256).astype(np.uint8),
                ((xs_grid * 73 + ys_grid * 29 + 53) % 256).astype(np.uint8),
                ((xs_grid * 19 + ys_grid * 97 + 149) % 256).astype(np.uint8),
            ],
            axis=-1,
        )
        ramp_bmp = scratch_dir / "ramp_317x211.bmp"
        Image.fromarray(ramp_rgb, mode="RGB").save(ramp_bmp, format="BMP")

        expected_ramp_bgra = rgb_to_opaque_bgra_bytes(ramp_rgb.tobytes(), rw, rh)
        expected_ramp_sha = sha256_hex(expected_ramp_bgra)
        assert sha256_hex(bmp_to_expected_bgra_bytes(ramp_bmp)) == expected_ramp_sha

        full_ramp = worker.full(ramp_bmp)
        assert full_ramp["bgra_sha256"] == expected_ramp_sha
        assert full_ramp["full_bgra_sha256"] == expected_ramp_sha
        assert full_ramp["source_rectangle_sha256"] == expected_ramp_sha
        assert full_ramp["width"] == rw and full_ramp["height"] == rh
        assert full_ramp["pixel_format"] == "Bgra8"
        assert full_ramp["requested_alpha_mode"] == "Ignore"
        assert full_ramp["alpha_mode"] == "Straight"
        assert full_ramp["alpha_summary"] == {"min": 255, "max": 255, "all_opaque_255": True}
        assert full_ramp["pid"] == info["pid"]

        ramp_rects: list[Sequence[int]] = [
            [0, 0, rw, rh],
            [0, 0, 1, 1],
            [rw - 1, 0, rw, 1],
            [0, rh - 1, 1, rh],
            [rw - 1, rh - 1, rw, rh],
            [37, 19, 284, 173],
            [101, 53, 102, 199],
            [14, 88, 305, 89],
            [200, 50, rw, 150],
            [50, 150, 250, rh],
            [np.int64(11), np.int64(23), np.int64(97), np.int64(89)],
        ]
        for rect in ramp_rects:
            c_res = worker.crop(rect)
            indep_slice = slice_bgra_rect(expected_ramp_bgra, rw, rh, rect)
            indep_sha = sha256_hex(indep_slice)
            assert c_res["bgra_sha256"] == indep_sha
            assert c_res["source_rectangle_sha256"] == indep_sha
            assert c_res["full_bgra_sha256"] == expected_ramp_sha
            assert c_res["byte_equality_verified"] is True
            assert c_res["width"] == int(rect[2]) - int(rect[0])
            assert c_res["height"] == int(rect[3]) - int(rect[1])
            assert c_res["alpha_summary"] == {"min": 255, "max": 255, "all_opaque_255": True}
            assert c_res["pid"] == info["pid"]

        # Half-open boundary sensitivity: shifting any edge by 1 pixel changes the SHA-256.
        base_rect = [37, 19, 284, 173]
        base_sha = sha256_hex(slice_bgra_rect(expected_ramp_bgra, rw, rh, base_rect))
        shifted_rects = [
            [38, 19, 284, 173],
            [37, 20, 284, 173],
            [37, 19, 283, 173],
            [37, 19, 284, 172],
        ]
        for s_rect in shifted_rects:
            assert worker.crop(s_rect)["bgra_sha256"] != base_sha

        summary["tests"]["T2_ramp_and_half_open_geometry"] = {
            "passed": True,
            "full_dimensions": [rw, rh],
            "full_bgra_sha256": expected_ramp_sha,
            "verified_crop_count": len(ramp_rects) + len(shifted_rects),
        }

        # --- T3: BMP row-stride padding (w % 4 in 0..3 with sentinel pad bytes), top-down, and 32-bit alpha ---
        stride_cases = []
        for w_mod in (64, 65, 66, 67):
            h_mod = 29
            yy, xx = np.mgrid[0:h_mod, 0:w_mod]
            rgb_mod = np.stack(
                [
                    ((xx * 41 + yy * 7) % 256).astype(np.uint8),
                    ((xx * 17 + yy * 59) % 256).astype(np.uint8),
                    ((xx * 83 + yy * 23) % 256).astype(np.uint8),
                ],
                axis=-1,
            )
            bmp_pad = scratch_dir / f"padded_w{w_mod}_sentinel.bmp"
            _write_raw_bmp24_with_sentinel_padding(bmp_pad, rgb_mod, sentinel_byte=0xA5, top_down=False)
            exp_bgra = rgb_to_opaque_bgra_bytes(rgb_mod.tobytes(), w_mod, h_mod)
            exp_sha = sha256_hex(exp_bgra)

            f_mod = worker.full(bmp_pad)
            assert f_mod["bgra_sha256"] == exp_sha
            assert f_mod["alpha_summary"] == {"min": 255, "max": 255, "all_opaque_255": True}
            c_mod = worker.crop([3, 5, w_mod - 1, h_mod - 2])
            assert c_mod["bgra_sha256"] == sha256_hex(
                slice_bgra_rect(exp_bgra, w_mod, h_mod, [3, 5, w_mod - 1, h_mod - 2])
            )
            stride_cases.append({"width": w_mod, "row_stride": inspect_bmp_header(bmp_pad)["row_stride"], "bgra_sha256": exp_sha})

        # Top-down 24-bit BMP must match bottom-up 24-bit BMP byte-for-byte in SoftwareBitmap.
        bmp_topdown = scratch_dir / "padded_w67_topdown.bmp"
        _write_raw_bmp24_with_sentinel_padding(bmp_topdown, rgb_mod, sentinel_byte=0x5A, top_down=True)
        f_td = worker.full(bmp_topdown)
        assert f_td["bgra_sha256"] == stride_cases[-1]["bgra_sha256"]

        # 32-bit BITMAPINFOHEADER BI_RGB (BGRX) preserves BGR and normalizes X->255.
        bgra_bgrx = np.zeros((40, 80, 4), dtype=np.uint8)
        bgra_bgrx[..., 0] = 240
        bgra_bgrx[..., 1] = 120
        bgra_bgrx[..., 2] = 60
        bgra_bgrx[..., 3] = 17  # Reserved X byte in 40-byte BI_RGB header
        bmp_bgrx = scratch_dir / "test_32bpp_bgrx.bmp"
        _write_raw_bmp32_bi_rgb(bmp_bgrx, bgra_bgrx)
        f_bgrx = worker.full(bmp_bgrx)
        assert f_bgrx["bgra_sha256"] == sha256_hex(bmp_to_expected_bgra_bytes(bmp_bgrx))
        assert f_bgrx["alpha_summary"] == {"min": 255, "max": 255, "all_opaque_255": True}

        # 32-bit BITMAPV4HEADER with explicit alpha (0, 64, 128, 255) and synthetic text glyphs:
        # proves exact [B, G, R, A] preservation without premultiplication!
        v4_img = Image.new("RGB", (520, 160), (255, 255, 255))
        v4_draw = ImageDraw.Draw(v4_img)
        v4_draw.text((36, 48), "ALPHA 77410-K", fill=(12, 24, 36), font=_load_font(32))
        v4_rgb = np.asarray(v4_img)
        v4_bgra = np.empty((160, 520, 4), dtype=np.uint8)
        v4_bgra[..., 0] = v4_rgb[..., 2]
        v4_bgra[..., 1] = v4_rgb[..., 1]
        v4_bgra[..., 2] = v4_rgb[..., 0]
        v4_bgra[..., 3] = 128
        v4_bgra[0, 0, 3] = 0
        v4_bgra[0, 1, 3] = 64
        v4_bgra[0, 2, 3] = 255
        bmp_v4 = scratch_dir / "test_32bpp_v4_alpha.bmp"
        _write_raw_bmp32_v4_alpha(bmp_v4, v4_bgra)

        expected_v4_bytes = v4_bgra.tobytes()
        expected_v4_sha = sha256_hex(expected_v4_bytes)
        assert sha256_hex(bmp_to_expected_bgra_bytes(bmp_v4)) == expected_v4_sha

        f_v4 = worker.full(bmp_v4)
        assert f_v4["bgra_sha256"] == expected_v4_sha
        assert f_v4["alpha_summary"] == {"min": 0, "max": 255, "all_opaque_255": False}
        c_v4 = worker.crop([20, 30, 420, 120])
        assert c_v4["bgra_sha256"] == sha256_hex(slice_bgra_rect(expected_v4_bytes, 520, 160, [20, 30, 420, 120]))
        assert "77410" in c_v4["text"]

        summary["tests"]["T3_padded_stride_and_alpha_preservation"] = {
            "passed": True,
            "stride_widths_tested": [c["width"] for c in stride_cases],
            "top_down_matches_bottom_up": True,
            "bmp24_default_alpha": 255,
            "bmp32_v4_preserves_exact_bgra_and_alpha": True,
            "bmp32_v4_crop_text": c_v4["text"],
        }

        # --- T4: Constructed synthetic page, original recognize.ps1 parity, visual.layout compatibility,
        #         crop-local word boxes, and standalone-BMP vs in-memory-crop exact OCR equivalence ---
        synth_bmp = scratch_dir / "synthetic_maintenance_300dpi.bmp"
        synth_rgb, synth_regions = _build_synthetic_maintenance_bmp(synth_bmp)
        expected_synth_bgra = rgb_to_opaque_bgra_bytes(synth_rgb.tobytes(), 1600, 1200)
        expected_synth_sha = sha256_hex(expected_synth_bgra)

        full_synth = worker.full(synth_bmp)
        assert full_synth["bgra_sha256"] == expected_synth_sha

        orig_ps1_res = _run_original_wp0015_recognize_ps1(synth_bmp)
        assert full_synth["text"] == orig_ps1_res["text"]
        assert full_synth["lines"] == orig_ps1_res["lines"]
        assert full_synth["angle"] == orig_ps1_res["angle"]
        assert full_synth["width"] == orig_ps1_res["width"]
        assert full_synth["height"] == orig_ps1_res["height"]

        # Verify drop-in compatibility with WP-0015 visual.rule_tables and visual.layout.
        wp15_dir = REPO_ROOT / "docs/research/WP-0015/astra"
        sys.path.insert(0, str(wp15_dir))
        import visual as wp15_visual  # noqa: E402

        with Image.open(synth_bmp) as pil_synth:
            grids = wp15_visual.rule_tables(pil_synth, (384.0, 288.0))
        projected = wp15_visual.layout(full_synth, grids, (384.0, 288.0))
        assert len(projected["tables"]) == 1 and len(projected["tables"][0]["rows"]) == 4

        # Snapshot monitored worker cwd AND isolated TEMP/TMP BEFORE in-memory crops to prove zero disk scratch writes.
        before_cwd = _snapshot_dir(monitored_cwd)
        before_temp = _snapshot_dir(isolated_temp)
        crop_records: dict[str, Any] = {}
        standalone_bmps: dict[str, Path] = {}
        for label, rect in synth_regions.items():
            c_out = worker.crop(rect)
            exp_slice = slice_bgra_rect(expected_synth_bgra, 1600, 1200, rect)
            assert c_out["bgra_sha256"] == sha256_hex(exp_slice)
            assert c_out["source_rectangle_sha256"] == c_out["bgra_sha256"]
            assert c_out["full_bgra_sha256"] == expected_synth_sha
            cw, ch = rect[2] - rect[0], rect[3] - rect[1]
            assert c_out["width"] == cw and c_out["height"] == ch
            for ln in c_out["lines"]:
                for wd in ln["words"]:
                    x0, y0, x1, y1 = wd["bbox"]
                    assert -2.0 <= x0 <= x1 <= cw + 2.0
                    assert -2.0 <= y0 <= y1 <= ch + 2.0
            crop_records[label] = c_out

        after_cwd = _snapshot_dir(monitored_cwd)
        after_temp = _snapshot_dir(isolated_temp)
        assert before_cwd == after_cwd == [], "In-memory crop() wrote unexpected files to worker cwd"
        assert before_temp == after_temp, "In-memory crop() wrote or modified files in TEMP/TMP"

        # Compare each in-memory crop against standalone full(cropped_bmp) for 100% recognition parity.
        for label, rect in synth_regions.items():
            sub_rgb = synth_rgb[rect[1] : rect[3], rect[0] : rect[2]]
            sub_bmp = scratch_dir / f"standalone_{label}.bmp"
            Image.fromarray(sub_rgb, mode="RGB").save(sub_bmp, format="BMP", dpi=(300, 300))
            standalone_bmps[label] = sub_bmp

        for label, sub_bmp in standalone_bmps.items():
            f_sub = worker.full(sub_bmp)
            c_mem = crop_records[label]
            assert f_sub["bgra_sha256"] == c_mem["bgra_sha256"], f"BGRA digest mismatch on {label}"
            assert f_sub["text"] == c_mem["text"], f"OCR text mismatch on {label}"
            assert f_sub["lines"] == c_mem["lines"], f"OCR lines/boxes mismatch on {label}"
            assert f_sub["angle"] == c_mem["angle"], f"OCR angle mismatch on {label}"

        summary["tests"]["T4_synthetic_parity_and_crop_equivalence"] = {
            "passed": True,
            "matches_original_wp0015_recognize_ps1": True,
            "wp0015_visual_layout_tables_detected": len(projected["tables"]),
            "regions_verified_identical_to_standalone_full": list(synth_regions.keys()),
            "sample_crop_texts": {k: v["text"] for k, v in crop_records.items()},
        }

        # --- T5: Warm persistence across page switches ---
        f_again = worker.full(synth_bmp)
        assert f_again["pid"] == info["pid"]
        assert f_again["bgra_sha256"] == expected_synth_sha
        for rect in synth_regions.values():
            c_warm = worker.crop(rect)
            assert c_warm["pid"] == info["pid"]

        # Verify process creation FILETIME is unchanged in live OS process table.
        ps_exe = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
        live_ft_str = subprocess.check_output(
            [
                str(ps_exe),
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                f"(Get-Process -Id {info['pid']}).StartTime.ToFileTimeUtc()",
            ],
            text=True,
        ).strip()
        assert int(live_ft_str) == info["process_create_filetime"]

        summary["tests"]["T5_warm_worker_persistence_and_zero_disk_scratch"] = {
            "passed": True,
            "persistent_pid": info["pid"],
            "process_create_filetime": info["process_create_filetime"],
            "monitored_cwd_files_created": 0,
            "isolated_temp_unchanged_across_crops": True,
        }

        # --- T6b: Bounds & payload fail-closed negative controls ---
        bad_rects: list[Any] = [
            None,
            [0, 0, 10],
            [0, 0, 10, 10, 1],
            [0.0, 0, 10, 10],
            [True, 0, 10, 10],
            ["0", "0", "10", "10"],
            [-1, 0, 10, 10],
            [0, -1, 10, 10],
            [0, 0, 1601, 1200],
            [0, 0, 1600, 1201],
            [10, 10, 10, 20],
            [10, 10, 20, 10],
            [20, 10, 10, 20],
            [10, 20, 20, 10],
        ]
        rejected_rects = 0
        for bad in bad_rects:
            try:
                worker.crop(bad)
                raise AssertionError(f"Accepted invalid crop rect: {bad!r}")
            except (TypeError, ValueError):
                rejected_rects += 1
        assert rejected_rects == len(bad_rects)

        # Retained full bitmap remains intact after rejected crop arguments.
        assert worker.crop([0, 0, 64, 64])["full_bgra_sha256"] == expected_synth_sha

        # Corrupt / non-BMP / oversized / truncated full() inputs fail closed AND clear retained bitmap.
        png_disguised = scratch_dir / "disguised_png.bmp"
        Image.new("RGB", (32, 32), (255, 255, 255)).save(png_disguised, format="PNG")

        truncated_bmp = scratch_dir / "truncated.bmp"
        raw_valid = ramp_bmp.read_bytes()
        truncated_bmp.write_bytes(raw_valid[:-16])

        bad_bfsize_bmp = scratch_dir / "bad_bfsize.bmp"
        mut_bfsize = bytearray(raw_valid)
        struct.pack_into("<I", mut_bfsize, 2, len(raw_valid) + 64)
        bad_bfsize_bmp.write_bytes(bytes(mut_bfsize))

        oversize_hdr_bmp = scratch_dir / "oversize_header.bmp"
        over_w = info["max_dimension"] + 1
        bfh_over = struct.pack("<2sIHHI", b"BM", 54 + ((over_w * 24 + 31) // 32) * 4, 0, 0, 54)
        dib_over = struct.pack("<IiiHHIIiiII", 40, over_w, 1, 1, 24, 0, ((over_w * 24 + 31) // 32) * 4, 11811, 11811, 0, 0)
        oversize_hdr_bmp.write_bytes(bfh_over + dib_over + b"\xff" * (((over_w * 24 + 31) // 32) * 4))

        bad_full_inputs: list[tuple[Path, type[BaseException]]] = [
            (scratch_dir / "missing_does_not_exist.bmp", FileNotFoundError),
            (scratch_dir, ValueError),
            (png_disguised, ValueError),
            (truncated_bmp, ValueError),
            (bad_bfsize_bmp, ValueError),
            (oversize_hdr_bmp, ValueError),
        ]
        for bad_path, exc_cls in bad_full_inputs:
            # Ensure a valid bitmap is retained right before testing that failed full() clears it.
            worker.full(ramp_bmp)
            caught = False
            try:
                worker.full(bad_path)
            except exc_cls:
                caught = True
            assert caught, f"Expected {exc_cls.__name__} for {bad_path}"

            stale_crop_blocked = False
            try:
                worker.crop([0, 0, 4, 4])
            except RuntimeError:
                stale_crop_blocked = True
            assert stale_crop_blocked, f"Stale retained bitmap was not cleared after failed full({bad_path})"

        # Worker still recovers cleanly in the same persistent process.
        rec_after = worker.full(ramp_bmp)
        assert rec_after["pid"] == info["pid"] and rec_after["bgra_sha256"] == expected_ramp_sha

    # Post-close fail-closed checks.
    assert worker._child.poll() is not None, "Child PowerShell process did not exit on context manager exit"
    worker.close()  # Idempotent second close
    post_close_blocked = False
    try:
        worker.full(ramp_bmp)
    except RuntimeError:
        post_close_blocked = True
    assert post_close_blocked

    summary["tests"]["T6_bounds_and_fail_closed_controls"] = {
        "passed": True,
        "invalid_crop_rects_rejected": rejected_rects,
        "invalid_full_inputs_rejected_and_cleared_retained": len(bad_full_inputs),
        "post_close_calls_rejected": True,
    }
    summary["all_passed"] = True
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scratch",
        type=Path,
        default=Path(r"C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\wp0019-data\carbon\smoke"),
        help="Scratch directory for synthetic test BMPs",
    )
    parser.add_argument(
        "--evidence-out",
        type=Path,
        default=None,
        help="Optional path to write JSON verification summary",
    )
    args = parser.parse_args()
    result = run_all_tests(args.scratch)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.evidence_out is not None:
        args.evidence_out.parent.mkdir(parents=True, exist_ok=True)
        args.evidence_out.write_bytes(text.encode("utf-8"))
    print(text, end="")


if __name__ == "__main__":
    main()
