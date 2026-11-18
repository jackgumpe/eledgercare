"""Bind admitted original PDFs and ordered RGB inventories without reading any scoring key."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PACKET = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0016")
PREVIOUS = PACKET.parent / "WP-0015/review"
WARM = REPO / "docs/research/WP-0014/eld-latency-author/A.pdf"
WARM_SHA = "25c14530845cad96329b528f860032c27a1259ed46de3ccb56f0e57730aa0858"
WARM_RGB = "a189916661ad64469762ea65a693b49c0d59ca2508df2742cc5d92b60f7dd18d"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def publish(path, data):
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError(f"Existing pinned file differs: {path.name}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(data)


def encoded(obj):
    return (json.dumps(obj, indent=2) + "\n").encode()


def prepare():
    custody = json.loads((REPO / "docs/evaluation/WP-0015/commitments.json").read_bytes())["packets"]
    assert digest(WARM.read_bytes()) == WARM_SHA
    common = [dict(label=f"warm-{i}", warmup=True, pages=1, pdf=str(WARM), sha256=WARM_SHA,
                   rgb_sha256=[WARM_RGB]) for i in (1, 2, 3)]
    inputs = {}
    for family in ("H", "A"):
        pins = custody[family]
        prior = PREVIOUS / f"input-{family}"
        destination = PACKET / "review/inputs" / family
        src = (prior / "source.pdf").read_bytes()
        raster_bytes = (prior / "rasters.input.json").read_bytes()
        raster = json.loads(raster_bytes)
        sha = digest(src)
        assert sha == pins["files"]["source.pdf"] == raster["pdf_sha256"]
        assert raster["family"] == family and len(raster["pages"]) == pins["pages"]
        assert [row["page_number"] for row in raster["pages"]] == list(range(1, pins["pages"] + 1))
        publish(destination / "source.pdf", src)
        publish(destination / "rasters.input.json", raster_bytes)
        common.append(dict(label=family.lower(), warmup=False, pages=pins["pages"], pdf=str(destination / "source.pdf"),
                           sha256=sha, rgb_sha256=[r["rgb_sha256"] for r in raster["pages"]]))
        inputs[family] = {"files":pins["files"], "pages":pins["pages"], "raster_input_sha256":digest(raster_bytes)}
    binds = {}
    for order, modes in (("ab", ["native", "carbon_bf16"]), ("ba", ["carbon_bf16", "native"])):
        plan = {"requests":[dict(r, mode=m) for m in modes for r in common]}
        path = PACKET / "coordination/plans" / f"g0-{order}.json"
        data = encoded(plan)
        publish(path, data)
        binds[order] = {"path":str(path), "sha256":digest(data), "order":modes, "excluded_warm_windows":6,
                        "inference_windows":50, "scored_source_pages_per_mode":64}
    record = {"gate":"G0", "inputs":inputs, "warm_sha256":WARM_SHA, "warm_rgb_sha256":WARM_RGB, "orders":binds}
    publish(HERE / "g0-plans.json", encoded(record))
    return binds


if __name__ == "__main__":
    print(json.dumps(prepare(),indent=2))
