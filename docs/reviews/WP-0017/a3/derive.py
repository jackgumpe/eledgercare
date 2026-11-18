"""Derive the WP-0017 A3 escrow tools from the committed WP-0016 G0 escrow tools (eld-rd-reviewer). Stdlib only.

A3 is the unchanged WP-0016 G0 gate with carbon_surgical in place of carbon_bf16. Rather than re-author the
verifier/scorer, this script materializes the exact WP-0016 tool blobs at the integration base (each SHA-256
verified), applies ONLY the enumerated literal substitutions below (each must match its exact expected count),
and writes the derived files plus a derivation manifest into a NEW directory. The diff from WP-0016 is
therefore mechanical and fully listed. Run it once root binds the A3 plan record; commit the output before
any A3 run exists.

Substitutions:
  * every literal  carbon_bf16  ->  <trial mode>  in verify.py, score_all.py, selftest.py, forecast-free tools
  * common.py PINS["g0-plans.json"] (commit, path, sha256) -> the bound A3 plan record
  * kind strings "WP-0016" -> "WP-0017 A3" in escrow.py/verify.py/score_all.py headers of written records
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import INTEGRATION_BASE, REPO as REPO_ROOT, git, sha, write_new  # noqa: E402

SOURCES = {  # path at the integration base -> SHA-256 of the blob
    "common.py": None, "escrow.py": None, "verify.py": None, "score_all.py": None, "title_adapt.py": None,
    "grammar.py": None, "selftest.py": None,
}
TRIAL_SUBST = ("verify.py", "score_all.py", "selftest.py")
OLD_PLANS = ('"g0-plans.json": (PLANS_COMMIT, "docs/coordination/WP-0016/g0-plans.json",\n'
             '                      "53be595ad05302c43aadf76bc8e04af929532877aed2a9ee08c12f32923854fb"),')


def derive(dest, trial, plans_commit, plans_path, plans_sha256, base=INTEGRATION_BASE):
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=False)
    manifest = dict(base=base, trial_mode=trial, plans=dict(commit=plans_commit, path=plans_path, sha256=plans_sha256),
                    files={})
    for name in SOURCES:
        src = git("cat-file", "blob", f"{base}:docs/reviews/WP-0016/{name}")
        text = src.decode("utf-8")
        subs = []
        if name in TRIAL_SUBST:
            n = text.count("carbon_bf16")
            text = text.replace("carbon_bf16", trial)
            subs.append(dict(old="carbon_bf16", new=trial, count=n))
        if name == "common.py":
            if text.count(OLD_PLANS) != 1:
                raise SystemExit("common.py plans pin not found exactly once")
            new = (f'"g0-plans.json": ("{plans_commit}", "{plans_path}",\n'
                   f'                      "{plans_sha256}"),')
            text = text.replace(OLD_PLANS, new)
            subs.append(dict(old="PINS['g0-plans.json']", new=[plans_commit, plans_path, plans_sha256], count=1))
            depth = len(dest.resolve().relative_to(REPO_ROOT.resolve()).parts)
            old_repo = "REPO = HERE.parents[2]"
            if text.count(old_repo) != 1:
                raise SystemExit("common.py REPO line not found exactly once")
            text = text.replace(old_repo, f"REPO = HERE.parents[{depth - 1}]")
            subs.append(dict(old=old_repo, new=f"REPO = HERE.parents[{depth - 1}]", count=1))
        for k in ("escrow.py", "verify.py", "score_all.py"):
            if name == k:
                n = len(re.findall(r'kind=f?"WP-0016', text))
                text = re.sub(r'kind=(f?)"WP-0016', r'kind=\1"WP-0017 A3 (derived from WP-0016)', text)
                subs.append(dict(old='kind="WP-0016', new='kind="WP-0017 A3 (derived from WP-0016)', count=n))
        out = text.encode("utf-8")
        (dest / name).write_bytes(out)
        manifest["files"][name] = dict(source=f"{base}:docs/reviews/WP-0016/{name}", source_sha256=sha(src),
                                       derived_sha256=sha(out), substitutions=subs)
    write_new(dest / "derivation.json", manifest)
    return manifest


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dest", type=Path, required=True)
    ap.add_argument("--trial", default="carbon_surgical")
    ap.add_argument("--plans-commit", required=True)
    ap.add_argument("--plans-path", required=True)
    ap.add_argument("--plans-sha256", required=True)
    a = ap.parse_args()
    m = derive(a.dest, a.trial, a.plans_commit, a.plans_path, a.plans_sha256)
    print(json.dumps({k: dict(derived=v["derived_sha256"], subs=[(s["old"], s["count"]) for s in v["substitutions"]])
                      for k, v in m["files"].items()}, indent=1))


if __name__ == "__main__":
    main()
