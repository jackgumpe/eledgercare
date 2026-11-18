"""Freeze the reviewer's A1 anchors and cross-bind the coordinator manifest (eld-rd-reviewer). CPU only, no truth.

Before any A1 output exists: binds the coordinator A1 manifest (a1-inputs.json, e7f47d14...) to the frozen
prefix audit (16eca676...), i.e. every token array and every AB/BA window-file digest, then freezes the
structural field locators, branch spans, native prefixes and boundary byte lengths that a1_decide.py uses,
plus the pinned design/rules.py and PROTOCOL.md digests it synchronizes with.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import a1_decide as A1  # noqa: E402
from common import A1_MANIFEST, BLOBS, Check, Vocab, blob, disk, ids_sha, load, sha, sha_file, utc, write_new  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--audit", type=Path, required=True)
    ap.add_argument("--audit-sha256", required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    check = Check()
    check(sha_file(a.audit) == a.audit_sha256, "audit digest")
    audit = load(a.audit)
    man = load(A1_MANIFEST[0])
    check(sha_file(A1_MANIFEST[0]) == A1_MANIFEST[1], "A1 manifest digest e7f47d14...")
    check(man["inventory_sha256"] == BLOBS["G0-blind-inventory.json"][2], "manifest cites the committed blind inventory")
    rgb = json.loads(disk("A/rasters.input.json"))
    check(man["request"]["sha256"] == rgb["pdf_sha256"] and
          man["request"]["rgb_sha256"] == [p["rgb_sha256"] for p in sorted(rgb["pages"], key=lambda p: p["page_number"])],
          "manifest A source and ordered RGB = pinned raster inventory")
    for w in man["windows"]:
        key = f"window-{w['first_page']:03d}"
        aw = audit["windows"][key]
        for mode, v in w["by_mode"].items():
            check(ids_sha(v["token_ids"]) == aw["a1_prefixes"]["full_window"][mode]["sha256"], f"{key}/{mode}: token array")
            check(v["window_ab_sha256"] == aw["arms"][f"{mode}:ab"]["file_sha256"]
                  and v["window_ba_sha256"] == aw["arms"][f"{mode}:ba"]["file_sha256"], f"{key}/{mode}: AB/BA file digests")
    vocab = Vocab(disk("tokenizer.json"))
    manifest = A1.load_manifest()
    locs, spans, pref, bb = A1.anchors(audit, manifest, vocab)
    for w in A1.WINDOWS:
        check(locs[w]["frozen_value"] == A1.NATIVE_IDS[w], f"{w}: native locator reads the native ID")
        st, val, _ = A1.field(vocab, manifest[w]["carbon_bf16"], locs[w])
        check((st, val) == ("ok", A1.CARBON_IDS[w]), f"{w}: same locator reads the Carbon ID on the Carbon history")
        for m in ("native", "carbon_bf16"):
            b = A1.free_boundary(vocab, manifest[w][m], locs[w], bb[w])
            check(b == pref[w]["tokens"], f"{w}/{m}: structural boundary = audited boundary {pref[w]['tokens']}")
    out = dict(kind="WP-0017 A1 reviewer anchors (pre-output, synchronized with design 1fad21c)", reviewer="eld-rd-reviewer",
               created_utc=utc(), audit_sha256=a.audit_sha256, manifest_sha256=A1_MANIFEST[1],
               design=dict(rules=dict(commit=BLOBS["design/rules.py"][0], sha256=sha(blob("design/rules.py"))),
                           protocol=dict(commit=BLOBS["design/PROTOCOL.md"][0], sha256=sha(blob("design/PROTOCOL.md")))),
               locators=locs, branch_spans=spans, native_prefixes=pref, boundary_bytes=bb,
               native_ids=A1.NATIVE_IDS, carbon_ids=A1.CARBON_IDS,
               rules=dict(D="ell(native ID) - ell(Carbon ID), FP32 log-softmax over the full vocabulary, summed in nats",
                          restore="both anchored free fields status ok and equal to the native IDs",
                          flip="addition's anchored free field ok and a different complete identifier",
                          noise_floor="E_w = max(1e-5 nats, |D_native1 - D_native2|, |D_full1 - D_full2|)",
                          selection="min removed, then sum of ordinary 019+037 seconds, then switch order"),
               checks_run=check.count, failures=check.failures)
    digest = write_new(a.out, out)
    print(json.dumps(dict(out=str(a.out), sha256=digest, checks=check.count, failures=check.failures), indent=1))
    return 0 if not check.failures else 1


if __name__ == "__main__":
    sys.exit(main())
