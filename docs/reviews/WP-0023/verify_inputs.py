"""Independently hash all model files and rerender the six released PDF pages on CPU."""
import argparse
from contextlib import ExitStack, closing
import hashlib
import json
from pathlib import Path

import pypdfium2
from PIL import Image


MODEL = Path("C:/Users/jackg/eLedgerCare-Q0/WP-0005/models/Unlimited_OCR_2_04809669")
MANIFEST = "06abb2ab4cd7bf8d74286741d4ce5da08f6e60fd237050394e2b891ae909058f"


def sha(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path)
    packet = parser.parse_args().packet
    fixtures = packet / "fixtures"
    manifest_file = fixtures / "manifest.json"
    assert sha(manifest_file) == MANIFEST
    manifest = json.loads(manifest_file.read_bytes())
    pdf = fixtures / manifest["source"]
    assert sha(pdf) == manifest["sha256"]
    rows = []
    with pypdfium2.PdfDocument(str(pdf)) as book:
        assert len(book) == manifest["pages"] == 12
        for name, page_range in [("short", range(4, 7)), ("long", range(7, 10))]:
            assert [r["page"] for r in manifest["windows"][name]] == list(page_range)
            for spec in manifest["windows"][name]:
                png = fixtures / spec["image"]
                assert sha(png) == spec["sha256"]
                with ExitStack() as ctx:
                    page = ctx.enter_context(closing(book[spec["page"] - 1]))
                    bmp = ctx.enter_context(closing(page.render(scale=300/72)))
                    rendered = ctx.enter_context(closing(bmp.to_pil().convert("RGB")))
                    saved = ctx.enter_context(Image.open(png))
                    assert saved.mode == "RGB" and rendered.size == saved.size == (spec["width"], spec["height"])
                    rgb = hashlib.sha256(saved.tobytes()).hexdigest()
                    assert rgb == spec["rgb_sha256"] == hashlib.sha256(rendered.tobytes()).hexdigest()
                rows.append(dict(window=name, page=spec["page"], rgb=rgb, png=spec["sha256"]))

    baseline = packet / "model-before.json"
    previous = json.loads(baseline.read_bytes())
    seen = {"files": {}, "directories": []}
    for path in sorted(MODEL.rglob("*")):
        assert not path.is_symlink()
        relpath = path.relative_to(MODEL).as_posix()
        if path.is_dir():
            seen["directories"].append(relpath)
        else:
            stat = path.stat()
            seen["files"][relpath] = dict(bytes=stat.st_size, sha256=sha(path), mtimeNs=stat.st_mtime_ns)
    seen["directories"].sort()
    assert seen == previous
    print(json.dumps(dict(model_files=len(seen["files"]), model_directories=len(seen["directories"]),
                          model_bytes=sum(x["bytes"] for x in seen["files"].values()),
                          model_inventory_sha256=sha(baseline), manifest_sha256=MANIFEST,
                          pdf_sha256=manifest["sha256"], windows=rows), indent=2))


if __name__ == "__main__":
    main()
