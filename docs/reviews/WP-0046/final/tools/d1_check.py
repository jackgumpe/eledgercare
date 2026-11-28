"""Archive-byte reproduction of the no-repeat ban sets (D1 / Ban_1) for the five F07.warm1 rows.

Reads pinned bytes with read-only `git show` at e43af2e2. Applies the Edition 02.1 A2 rule:
n = generated-history length before the decision; when n >= 35, for i in max(0, n-1024)..n-35,
if H[i:i+34] == H[n-34:n] then ban H[i+34] (empty whitelist). Prompt IDs excluded.
Usage: python -I d1_check.py REPO_DIR BUNDLE_DIR
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

BASE = "e43af2e263f55478d1d551a5a095536b042589c2"
EV = ["docs/coordination/WP-0005/gpu-reviewer-release/author-run-snapshot/evidence/",
      "docs/reviews/WP-0005/eld-q0-reviewer/runtime-005/run-20261115T210422Z-565e2de9/evidence/",
      "qualification/q0/harness/evidence/004-gpu-trial/9e73ef86/run-20261115T202627Z-eb5bf7da/evidence/"]


def find(node, key):
    if isinstance(node, dict):
        for k, v in node.items():
            if k == key:
                yield v
            yield from find(v, key)
    elif isinstance(node, list):
        for v in node:
            yield from find(v, key)


def main(repo, bundle):
    show = lambda p: subprocess.run(["git", "-C", repo, "show", BASE + ":" + p], capture_output=True).stdout
    toks = [show(d + "F07.warm1.token_ids.json") for d in EV]
    H = json.loads(toks[0])
    obs = json.loads(show(EV[0] + "F07.warm1.observation.json"))
    prompt = sorted({v for v in find(obs, "prompt_len") if isinstance(v, int)})
    rows = json.loads((Path(bundle) / "sources/native43.json").read_text(encoding="utf-8"))["retained_rows"]
    out = {"token_sha256": [hashlib.sha256(t).hexdigest() for t in toks], "token_files_identical": len({hashlib.sha256(t).hexdigest() for t in toks}) == 1,
           "generated_ids": len(H), "prompt_len_values": prompt, "rows": []}
    P = prompt[0] if len(prompt) == 1 else None
    for r in rows:
        n = r["position"] - P
        suffix = H[n - 34:n]
        starts = list(range(max(0, n - 1024), n - 35 + 1))
        bans = sorted({H[i + 34] for i in starts if H[i:i + 34] == suffix})
        longest = 0
        for i in starts:
            m = 0
            while m < 34 and H[i + 33 - m] == H[n - 1 - m]:
                m += 1
            longest = max(longest, m)
        out["rows"].append({"position": r["position"], "n": n, "aligned_emission": H[n] == r["actual_emission"],
                            "starts": len(starts), "ban_1": bans, "longest_suffix_match": longest,
                            "scanned_final_minus_n": r["final_page_guard"]["scanned"] - n})
    out["total_starts"] = sum(x["starts"] for x in out["rows"])
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:3])
