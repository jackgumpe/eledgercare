"""Scan preserved raw child stdout/stderr for the pinned model's own diagnostic print lines.

Provenance 'log'. Markers are supplementary: the DASH Triton fallback is silent (returns
None, no print), so ABSENCE of a marker is never evidence of a path (Q0R-04). The raw
logs themselves are preserved byte-for-byte by the supervisor.
"""

from __future__ import annotations

# (marker, meaning, source location in the pinned snapshots)
MARKERS = (
    ("[DASH] Triton block-sparse path active", "DASH Triton kernel returned output", "dash_attention.py L1224"),
    ("[DASH] differentiable DASH attention active", "DASH router constructed", "modeling_deepseekv2.py L86"),
    ("[DASH] Stage-0 summarization", "DASH training-path forward ran (not expected under _INFER)", "dash_attention.py L1293"),
    ("[SparseAttn] triton gather path failed", "base sparse path Triton failure -> block-mask fallback", "_sparse_base_impl.py L1761"),
    ("using fused triton gather kernel", "base sparse path Triton gather used", "_sparse_base_impl.py L1767"),
    ("[CodeStamp]", "_sparse_base_impl import-time code stamp", "_sparse_base_impl.py L73"),
    ("[PageRope][WARN]", "router scoring fell back to 1D RoPE", "modeling_deepseekv2.py L137"),
    ("[debug ForCausalLM]", "one-shot ForCausalLM.forward diagnostic", "modeling_unlimitedocr.py L922"),
    ("Traceback (most recent call last)", "Python traceback text", "-"),
)


def scan(data: bytes) -> dict:
    text = data.decode("utf-8", "replace")
    lines = text.splitlines()
    out = []
    for marker, meaning, where in MARKERS:
        hits = [i for i, l in enumerate(lines) if marker in l]
        out.append({"marker": marker, "meaning": meaning, "source": where, "count": len(hits),
                    "first_line": lines[hits[0]][:400] if hits else None})
    return {"provenance": "log", "bytes": len(data), "lines": len(lines), "markers": out,
            "note": "Absence of a marker is not evidence of a path; DASH fallback is silent."}
