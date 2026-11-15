#!/usr/bin/env python3
"""Compare isolated regeneration outputs with the exported candidate (reviewer-authored).

Usage: python rd005_regen_compare.py <candidate_root> <regen_eval_root_1> [<regen_eval_root_2> ...]
Each regen root is the --output-eval-root given to the author generator (contains synthetic/ and manifests/).
"""
import hashlib, json, pathlib, sys

cand = pathlib.Path(sys.argv[1]) / "evaluation"
roots = [pathlib.Path(p) for p in sys.argv[2:]]


def listing(root: pathlib.Path) -> dict:
    out = {}
    for sub in ("synthetic/pdfs", "synthetic/expected"):
        for p in sorted((root / sub).rglob("*")):
            if p.is_file():
                out[p.relative_to(root).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    m = root / "manifests/corpus-manifest.json"
    out["manifests/corpus-manifest.json"] = hashlib.sha256(m.read_bytes()).hexdigest()
    return out


base = listing(cand)
res = {"candidate_artifacts": len(base), "runs": []}
for r in roots:
    got = listing(r)
    extra = sorted(set(got) - set(base))
    missing = sorted(set(base) - set(got))
    diff = sorted(k for k in set(base) & set(got) if base[k] != got[k])
    res["runs"].append({"root": r.as_posix(), "artifacts": len(got), "identical": len(set(base) & set(got)) - len(diff),
                        "different": diff, "extra": extra, "missing": missing})
ok = all(not x["different"] and not x["extra"] and not x["missing"] for x in res["runs"])
res["all_byte_identical"] = ok
print(json.dumps(res, indent=1))
sys.exit(0 if ok else 1)
