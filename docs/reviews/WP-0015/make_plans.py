"""eld-rd-reviewer plan generator for the frozen common launcher (docs/research/WP-0015/astra/launch.py).

Standard library only. Writes one immutable plan per new process, alternating engine order
(ab = native first, ba = windows first; two pairs follow ab, ba, ba, ab). Every request carries the
source PDF SHA-256 and every 300-DPI RGB pin. The excluded warm-up is public WP-0014 A.pdf, run on
both engines before the measured document. Plans reference only the released input PDF; they never
name truth, scoring keys or custody paths. Prints the exact PowerShell launch commands.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EVAL = ROOT / "docs/evaluation/WP-0015"
LAUNCH = ROOT / "docs/research/WP-0015/astra/launch.py"
PY = "C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe"
PACKET = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0015")
WARM = dict(label="warm", pdf=str(ROOT / "docs/research/WP-0014/eld-latency-author/A.pdf"), pages=1, warmup=True,
            sha256="25c14530845cad96329b528f860032c27a1259ed46de3ccb56f0e57730aa0858",
            rgb_sha256=["a189916661ad64469762ea65a693b49c0d59ca2508df2742cc5d92b60f7dd18d"])
ORDERS = {"ab": ("native", "windows"), "ba": ("windows", "native")}
SEQUENCE = ("ab", "ba", "ba", "ab")
HEX = re.compile("[0-9a-f]{64}")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_pins(path, pages):
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if isinstance(data, dict) and "pages" in data:          # rasters.json layout
        pins = [p["rgb_sha256"] for p in sorted(data["pages"], key=lambda p: p["page_number"])]
    elif isinstance(data, dict):
        pins = data["rgb_sha256"]
    else:
        pins = data
    if len(pins) != pages or not all(isinstance(p, str) and HEX.fullmatch(p) for p in pins):
        raise SystemExit(f"need exactly {pages} lowercase SHA-256 RGB pins")
    return pins


def launcher_accepts(r):
    """Mirror of launch.py request validation (frozen 82206bc) plus reviewer-side requirements."""
    return (re.fullmatch("[a-z0-9-]{1,28}", r["label"]) and r["mode"] in ("native", "windows")
            and isinstance(r["warmup"], bool) and 1 <= r["pages"] <= 60 and HEX.fullmatch(r["sha256"])
            and Path(r["pdf"]).is_absolute() and len(r["rgb_sha256"]) == r["pages"])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--family", required=True, help="H, A or B (sealed) or a public dev family")
    ap.add_argument("--pdf", type=Path, required=True, help="released input source.pdf (absolute)")
    ap.add_argument("--rgb-pins", type=Path, required=True, help="custodian/coordinator RGB digests")
    ap.add_argument("--out", type=Path, required=True, help="new directory for plans")
    ap.add_argument("--pairs", type=int, choices=(1, 2), default=1, help="1 -> ab,ba; 2 -> ab,ba,ba,ab")
    ap.add_argument("--source", default="82206bc4b77654010ac02364adaaf589d1f36780")
    ap.add_argument("--seconds", default="<RELEASED_SECONDS>")
    ap.add_argument("--lease", default="<RELEASED_LEASE>")
    ap.add_argument("--prefix", default=None, help="run-name prefix; default family-lowercase")
    a = ap.parse_args()

    commitments = json.loads((EVAL / "commitments.json").read_text(encoding="utf-8"))["packets"]
    pdf = a.pdf.resolve()
    body = pdf.read_bytes()
    digest = sha(body)
    if a.family in commitments:
        want = commitments[a.family]
        if digest != want["files"]["source.pdf"]:
            raise SystemExit("released PDF does not match the custodian commitment")
        pages = want["pages"]
    else:
        manifest = json.loads((EVAL / "dev" / a.family / "rasters.json").read_text(encoding="utf-8"))
        if digest != manifest["pdf_sha256"]:
            raise SystemExit("dev PDF does not match its manifest")
        pages = len(manifest["pages"])
    if pdf.name != "source.pdf" or any(part.lower() in ("scoring", "custody") for part in pdf.parts):
        raise SystemExit("plan input must be a released source.pdf outside scoring/custody paths")
    page_objects = len(re.findall(rb"/Type\s*/Page(?![s\w])", body))
    pins = read_pins(a.rgb_pins, pages)
    if sha(Path(WARM["pdf"]).read_bytes()) != WARM["sha256"]:
        raise SystemExit("warm-up PDF changed")

    label = a.family.lower()
    prefix = a.prefix or label
    doc = dict(label=label, pdf=str(pdf), pages=pages, warmup=False, sha256=digest, rgb_sha256=pins)
    a.out.mkdir(parents=True, exist_ok=False)
    records = []
    for n, order in enumerate(SEQUENCE[:2 * a.pairs], 1):
        modes = ORDERS[order]
        requests = [dict(WARM, mode=m) for m in modes] + [dict(doc, mode=m) for m in modes]
        if not all(launcher_accepts(r) for r in requests):
            raise SystemExit("frozen launcher would refuse a request")
        data = (json.dumps(dict(requests=requests), indent=1) + "\n").encode()
        assert b"truth" not in data and b"scoring" not in data.lower()
        path = a.out / f"plan-{n}-{order}.json"
        with path.open("xb") as fh:
            fh.write(data)
        run = f"{prefix}-r{n}-{order}"
        if not re.fullmatch(r"[\w-]{1,64}", run) or (PACKET / "review/runs" / run).exists():
            raise SystemExit("run name invalid or already used: " + run)
        cmd = (f"& '{PY}' -I -B '{LAUNCH.as_posix()}' --source {a.source} --plan '{path.resolve().as_posix()}' "
               f"--sha256 {sha(data)} --owner review --run {run} --seconds {a.seconds} --lease {a.lease} "
               f"--min-vram-mib 12000")
        records.append(dict(process=n, order=order, plan=str(path.resolve()), plan_sha256=sha(data), run=run,
                            run_dir=str(PACKET / "review/runs" / run), command=cmd))
    manifest = dict(family=a.family, source=a.source, pdf=str(pdf), pdf_sha256=digest, pages=pages,
                    pdf_page_objects_seen=page_objects, rgb_sha256=pins, rgb_pins_file=str(a.rgb_pins.resolve()),
                    rgb_pins_file_sha256=sha(a.rgb_pins.read_bytes()), warmup=WARM, processes=records)
    with (a.out / "plans.json").open("x", encoding="utf-8") as fh:
        fh.write(json.dumps(manifest, indent=2) + "\n")
    for r in records:
        print(r["command"])
    if page_objects != pages:
        print(f"WARNING: {page_objects} page objects seen vs {pages} committed pages", file=sys.stderr)


if __name__ == "__main__":
    main()
