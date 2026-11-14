#!/usr/bin/env python3
"""E2 angle-sign consistency diagnostic (reviewer-authored, CPU-only, no OCR, dev fixtures only).

Implements the E2 card text in research/carbon/reconciliation/02-ranked-experiment-backlog.md literally:
grayscale -> Otsu foreground mask M (diagnostic only); theta in [-5.0, +5.0] step 0.1 (101 candidates);
V(theta) = Var_y(sum_x M_theta(y, x)); argmax with smallest |theta| then positive tie-break; gate
|theta_hat| >= 1.0 and V(theta_hat) >= 1.10 V(0); correction = rotate original RGB once by -theta_hat
(PIL BILINEAR, expand=True, white fill). The card never defines M_theta, so both readings are run:
  A: M_theta = rotate(M, +theta)  (PIL CCW-positive; the same operator/convention used by the correction
     step and by the corpus generator's signed_angle_degrees_ccw)
  B: M_theta = rotate(M, -theta)  (theta read as the hypothesised CCW page skew)
Residual skew after correction (CCW degrees) = true_skew + (-theta_hat) because PIL rotations about the
centre compose additively; it is also re-measured empirically on the corrected page.
"""
from __future__ import annotations

import json
import pathlib
import sys
import zlib

from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from rd005_verify import MiniPdf  # reviewer-owned parser  # noqa: E402

ANGLES = [(k - 50) / 10 for k in range(101)]


def page_rgb(pdf: pathlib.Path) -> Image.Image:
    pg = MiniPdf(pdf.read_bytes()).pages()[0]
    im = next(iter(pg["images"].values()))
    return Image.frombytes("RGB", (im["w"], im["h"]), zlib.decompress(im["raw"]))


def otsu_mask(rgb: Image.Image) -> Image.Image:
    g = rgb.convert("L")
    hist = g.histogram()
    total = sum(hist)
    sum_all = sum(i * h for i, h in enumerate(hist))
    w_b = sum_b = 0
    best, thr = -1.0, 0
    for t in range(256):
        w_b += hist[t]
        if w_b == 0:
            continue
        w_f = total - w_b
        if w_f == 0:
            break
        sum_b += t * hist[t]
        m_b, m_f = sum_b / w_b, (sum_all - sum_b) / w_f
        between = w_b * w_f * (m_b - m_f) ** 2
        if between > best:
            best, thr = between, t
    mask = g.point(lambda v: 255 if v <= thr else 0).convert("F").point(lambda v: v / 255.0)
    return mask, thr


def variance(mask: Image.Image, theta: float) -> float:
    r = mask.rotate(theta, resample=Image.Resampling.NEAREST, expand=True, fillcolor=0.0)
    w, h = r.size
    col = r.resize((1, h), Image.Resampling.BOX)
    sums = [col.getpixel((0, y)) * w for y in range(h)]
    mu = sum(sums) / h
    return sum((s - mu) ** 2 for s in sums) / h


def estimate(mask: Image.Image, reading: str) -> dict:
    sign = 1.0 if reading == "A" else -1.0
    scores = {t: variance(mask, sign * t) for t in ANGLES}
    best = max(scores.values())
    cands = [t for t, v in scores.items() if v == best]
    th = sorted(cands, key=lambda t: (abs(t), -t))[0]
    gain = scores[th] / scores[0.0]
    trig = abs(th) >= 1.0 and scores[th] >= 1.10 * scores[0.0]
    return {"theta_hat": th, "V_ratio_vs_0": round(gain, 4), "triggered": trig}


def residual_empirical(rgb: Image.Image) -> float:
    """Re-measure remaining CCW skew: find leveling rotation phi in [-10, 10] (reading A) -> skew = -phi."""
    m, _ = otsu_mask(rgb)
    m = m.resize((m.width // 2, m.height // 2), Image.Resampling.BOX)
    grid = [(k - 100) / 10 for k in range(201)]
    sc = {p: variance(m, p) for p in grid}
    phi = max(sc, key=lambda p: (sc[p], -abs(p)))
    return -phi


def main() -> int:
    repo = pathlib.Path(sys.argv[1])
    out = pathlib.Path(sys.argv[2])
    cases = [("F01", "SYN-WO-01", 4.0), ("F02", "SYN-WO-02", -3.0), ("F04", "SYN-INV-01", -3.0), ("F07", "SYN-MP-01", 4.0)]
    res = []
    for fam, pre, true_skew in cases:
        tag = ("pos" if true_skew > 0 else "neg") + f"{int(abs(true_skew))}deg"
        for kind, path, skew in (("v1_raster300", f"{pre}-v1-raster300.pdf", 0.0), ("v2_skew", f"{pre}-v2-skew-{tag}.pdf", true_skew)):
            rgb = page_rgb(repo / "evaluation/synthetic/pdfs" / fam / path)
            mask, thr = otsu_mask(rgb)
            row = {"family": fam, "fixture_page": f"{path}#p1", "variant": kind, "true_ccw_skew_deg": skew, "otsu_threshold": thr}
            for reading in ("A", "B"):
                e = estimate(mask, reading)
                applied = -e["theta_hat"] if e["triggered"] else 0.0
                e["applied_pil_rotate_deg"] = applied
                e["analytic_residual_ccw_deg"] = round(skew + applied, 2)
                if e["triggered"]:
                    corrected = rgb.rotate(applied, resample=Image.Resampling.BILINEAR, expand=True, fillcolor=(255, 255, 255))
                    e["empirical_residual_ccw_deg"] = residual_empirical(corrected)
                e["outcome"] = ("pass-through" if not e["triggered"] else
                                "corrected" if abs(skew + applied) < 0.5 else
                                "amplified" if abs(skew + applied) > abs(skew) else "partially corrected")
                row["reading_" + reading] = e
            res.append(row)
            print(json.dumps(row))
    out.write_text(json.dumps({"tool": "docs/reviews/WP-0004/eld-rd-reviewer/helpers/e2_sign_diagnostic.py",
                               "scope": "dev families F01,F02,F04,F07 page 1 only; v1 (unrotated) and v2 (signed skew); no OCR, no holdout",
                               "pillow": Image.__version__, "angles": "101 candidates -5.0..+5.0 step 0.1", "mask_rotation_resample": "NEAREST (unspecified by card)",
                               "results": res}, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
