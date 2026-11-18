"""Write a fresh truth-free, ordered reviewer plan from public commitments and a released PDF."""
import argparse
import hashlib
import json
from pathlib import Path

from observe_host import PACKET_ROOT

DOCS = Path(__file__).resolve().parents[2]
REVIEW = Path("C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/speed-review")
WARM_PDF = REVIEW / "docs/research/WP-0014/eld-latency-author/A.pdf"
WARM_PDF_ID = "25c14530845cad96329b528f860032c27a1259ed46de3ccb56f0e57730aa0858"
WARM_RGB = "a189916661ad64469762ea65a693b49c0d59ca2508df2742cc5d92b60f7dd18d"


def make(family, order, out):
    commitment = json.loads((DOCS / "evaluation/WP-0015/commitments.json").read_bytes())["packets"][family]
    inp = PACKET_ROOT / "review" / ("input-" + family)
    pdf = inp / "source.pdf"
    raster = json.loads((inp / "rasters.input.json").read_bytes())
    source_hash = hashlib.sha256(pdf.read_bytes()).hexdigest()
    n = commitment["pages"]
    assert source_hash == commitment["files"]["source.pdf"] == raster["pdf_sha256"]
    assert raster["family"] == family and len(raster["pages"]) == n
    assert [r["page_number"] for r in raster["pages"]] == list(range(1,n+1))
    assert hashlib.sha256(WARM_PDF.read_bytes()).hexdigest() == WARM_PDF_ID
    modes = ["native", "windows"] if order == "ab" else ["windows", "native"]
    warm = dict(label="warm", pdf=str(WARM_PDF), pages=1, warmup=True, sha256=WARM_PDF_ID, rgb_sha256=[WARM_RGB])
    doc = dict(label=family.lower(), pdf=str(pdf), pages=n, warmup=False, sha256=source_hash,
               rgb_sha256=[r["rgb_sha256"] for r in raster["pages"]])
    requests = [dict(**req, mode=mode) for req in (warm,doc) for mode in modes]
    data = (json.dumps({"requests": requests}, separators=(",", ":")) + "\n").encode()
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("xb") as handle:
        handle.write(data)
    print(hashlib.sha256(data).hexdigest(), str(out))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("family", choices=["H","A","B"])
    p.add_argument("order", choices=["ab","ba"])
    p.add_argument("out", type=Path)
    a = p.parse_args()
    make(a.family,a.order,a.out)
