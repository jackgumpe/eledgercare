"""Issue one reviewer GPU command for the coordinator's passive carrier (eld-rd-reviewer). Stdlib only.

Method (root, docs/coordination/WP-0017/review_command.py at d17669e, SHA-256 c5596d0e...): for each release
the coordinator publishes <name>-release.json and its digest. After independent review I commit and push one
JSON command docs/reviews/WP-0017/commands/<name>.json on review/wp-0017-escrow. A passive carrier process
owned by the coordinator ("eld-coordinator Windows process") waits for that exact pushed object, checks that
it equals the signed release and executes only that pinned lease once. No reviewer process needs to break away
from the CLI job, and no reviewer tool call needs to remain open during GPU execution.

`review` performs the independent pre-issue checks and prints them; `issue` repeats them and writes the
command file (exclusive create) only if every check passes. Committing and pushing remain explicit manual
steps by the reviewer. This tool never starts the carrier, the executor or any GPU work.

Revision by the continuation session (common.OPERATOR), before any release existed:
* the operator of record is common.OPERATOR (the prior text named the exhausted Antigravity session);
* executor, carrier, nested WP-0016 guard, winjob, run_order, issue_lease, check_endpoints and prepare_a1 are
  compared with their reviewed Git blobs. An on-disk copy that differs ONLY by CRLF line endings is accepted as
  'eol_variant' and recorded with both digests (the coordinator's working copies end in one CRLF); any other
  difference fails;
* every A1 order plan is independently re-derived from the reviewed prepare_a1.py contract and must equal the
  published plan exactly (argv, configs, budgets, bound files, required outputs, requests, output roots);
  the endpoint order must precede the switch order; both inner and outer output roots must be new;
* the candidate must descend from the inference base, be published on a remote ref, be clean, and every
  tracked engine file (not only *.py) must equal its blob at the candidate;
* A2/A3 fail closed until their plan generators have been reviewed and bound here;
* an A1 command is issued only for a candidate with a reviewed a1_normalize binding whose S3-on probes use the
  configuration's device guards (a1_candidate_ready); eb16708 does not, so its S3-on probes could only fail.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (A1_MANIFEST, COORD_PATHS, HERE, OPERATOR, OPERATOR_TEXT, REPO, WP17, Check, eol_status,  # noqa
                    sha, sha_file, utc, write_new)

COORD_ROOT = Path("C:/Users/jackg/Asp.net Projects/eledgercare")
COORD_DIR = COORD_ROOT / "docs/coordination/WP-0017"
GPU = "GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d"
CEILING = {"A1": 14500, "A2": 14500, "A3": 10000}
CARRIER = "eld-coordinator Windows process (docs/coordination/WP-0017/review_command.py)"
Q0 = Path("C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe")
INFERENCE_BASE = "c7b2ee3663317e42a0e9bdd7ff9e17f16747d2cf"
ENGINE_DIR = "docs/research/WP-0017/engine"
SWITCHES = ("S0", "S1a", "S1b", "S1c", "S2", "S3")
ENDPOINTS = ("native", "all_off", "carbon_bf16", "all_on")          # genuine + switch-harness endpoint controls
ONE_FACTOR = tuple(f"{k}_{s}" for k in ("add", "remove") for s in SWITCHES)
A1_GROUPS = (("endpoints", ENDPOINTS, 2700), ("switches", ONE_FACTOR, 7200))   # reviewed prepare_a1.py 74b24a1f
A1_WARM = dict(pages=1, rel="docs/research/WP-0014/eld-latency-author/A.pdf",
               sha256="25c14530845cad96329b528f860032c27a1259ed46de3ccb56f0e57730aa0858",
               rgb_sha256=["a189916661ad64469762ea65a693b49c0d59ca2508df2742cc5d92b60f7dd18d"])
SEALED = ("truth", "custody", "details.json", "escrow-stage2", "g0-quality-return", "/b/", "\\b\\", "packet-b")


def git(cwd, *args, ok=False):
    r = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True)
    if ok:
        return r.returncode == 0
    r.check_returncode()
    return r.stdout


def pinned_file(path, name, check, notes):
    """Compare a coordinator file on disk with its reviewed blob; record raw digest and EOL status."""
    data = Path(path).read_bytes()
    st = eol_status(data, name)
    check(st in ("identical", "eol_variant"), f"{name} on disk equals its reviewed blob (status {st})")
    if st == "eol_variant":
        notes.append(f"{name}: on-disk copy differs from its blob only by CRLF line endings "
                     f"(disk {sha(data)[:12]}, normalized equal); executed semantics unchanged")
    return dict(path=str(path), sha256=sha(data), status=st)


def a1_expected(cfg_path, cfg, group, configs, seconds, coord_dir, packet=WP17, anchor_pin=A1_MANIFEST):
    """Independent re-derivation of one A1 order plan under the reviewed prepare_a1.py contract."""
    worktree = Path(cfg["worktree"]).resolve()
    head = cfg["source"]
    tag = Path(cfg_path).parent.name
    name = f"a1-{tag}-{group}"
    runs = packet / "review/runs"
    inner, outer = runs / name, runs / (name + "-order")
    anchor, anchor_sha = anchor_pin
    if sha_file(anchor) != anchor_sha:
        raise SystemExit("A1 manifest digest mismatch")
    manifest = json.loads(Path(anchor).read_bytes())
    warm = dict(pages=A1_WARM["pages"], pdf=str(worktree / A1_WARM["rel"]), sha256=A1_WARM["sha256"],
                rgb_sha256=A1_WARM["rgb_sha256"])
    argv = [str(Q0), "-I", "-B", str(worktree / ENGINE_DIR / "launch.py"), "--source", head, "--owner", "review",
            "--run", name, "--lease", "a1-" + tag, "--plan", str(anchor), "--sha256", anchor_sha,
            "--seconds", str(seconds), "--min-vram-mib", "12000", "--warmup-count", "3", "--configs", ",".join(configs)]
    commands = [dict(label=name, argv=argv, required_outputs=[str(inner / "process.json")])]
    files = {str(anchor): anchor_sha}
    if group == "endpoints":
        chk = coord_dir / "check_endpoints.py"
        files[str(chk)] = sha_file(chk)
        commands.append(dict(label="require-eight-endpoint-matches",
                             argv=[str(Q0), "-I", "-B", str(chk), str(inner), str(outer / "endpoint-check.json")]))
    plan = dict(stage="A1", worktree=str(worktree), source=head, output=str(outer),
                requests=[dict(manifest["request"]), warm], bound_files=files, commands=commands)
    return plan, tag, name, inner, outer


def a1_candidate_ready(head):
    """Issuance precondition: the A1 candidate has a reviewed probe/label binding whose S3-on probes use the
    configuration's device guards. Otherwise its S3-on probes could only end BINDING_FAILED (wasted lease)."""
    from a1_normalize import BOUND  # noqa: PLC0415
    problems = []
    if head not in BOUND:
        problems.append(f"candidate {head[:12]} has no reviewed a1_normalize binding (re-bind commit required)")
    elif BOUND[head].get("s3_device_guards") is not True:
        problems.append(f"candidate {head[:12]}: S3-on probes do not use the configuration's device guards "
                        "(joint design read finding 3); release the corrected candidate")
    return problems


def review_a1(lease, coord_dir, check, notes):
    for p in a1_candidate_ready(lease["review_worktree_head"]):
        check(False, p)
    orders = lease["orders"]
    check(len(orders) == len(A1_GROUPS), f"A1 release has {len(A1_GROUPS)} orders (endpoints, then switches)")
    tags, out = set(), []
    for k, (group, configs, seconds) in enumerate(A1_GROUPS):
        if k >= len(orders):
            break
        o = orders[k]
        p = Path(o["plan"])
        cfg = json.loads(p.read_bytes())
        exp, tag, name, inner, outer = a1_expected(p, cfg, group, configs, seconds, coord_dir)
        tags.add(tag)
        check(p.parent.parent == WP17 / "coordination/plans" and p.name == name + ".json",
              f"order {k + 1}: plan path {p} is coordination/plans/<tag>/{name}.json")
        check(cfg == exp, f"order {k + 1} ({group}): plan equals the independent re-derivation "
                          f"(differing keys {sorted(x for x in set(cfg) | set(exp) if cfg.get(x) != exp.get(x))})")
        check(o["run"] == outer.name and Path(o["output"]).resolve() == outer.resolve(),
              f"order {k + 1}: run/output = {outer.name}")
        check(o["argv"] == [str(Q0), "-I", "-B", str(coord_dir / "run_order.py"), str(p), sha_file(p)],
              f"order {k + 1}: executor argv runs the reviewed run_order.py on this exact plan digest")
        check(not inner.exists() and not outer.exists(), f"order {k + 1}: inner and outer output roots are new")
        if o["seconds"] < seconds:
            notes.append(f"order {k + 1}: supervised wall {o['seconds']} s is below the engine budget {seconds} s; "
                         "the board guard may stop it first (a documented partial result)")
        out.append(dict(group=group, configs=list(configs), engine_seconds=seconds, supervised_seconds=o["seconds"],
                        inner=str(inner), outer=str(outer)))
    check(len(tags) == 1, "both A1 orders share one tag")
    return out


def review(name, digest, stage, coord_dir, check):
    notes = []
    rel = coord_dir / f"{name}-release.json"
    data = rel.read_bytes()
    check(sha(data) == digest, "release bytes equal the signed digest")
    lease = json.loads(data)
    check(lease.get("name") == name and lease.get("operator") == "eld-rd-reviewer" and lease.get("gate") == stage,
          "release name/operator/stage")
    check(lease.get("gpu_uuid") == GPU and lease.get("ceiling_mib") == CEILING[stage], "GPU UUID and stage ceiling")
    root = coord_dir.parents[2]
    pins = {k: pinned_file(root / p, k, check, notes) for k, p in COORD_PATHS.items()}
    executor_sha = pins["coord/device_lease.py"]["sha256"]
    guard_files = lease.get("coordination_files", {})
    for f, h in guard_files.items():
        check(sha_file(root / f) == h, f"coordination file {f} matches the release")
        key = next((k for k, p in COORD_PATHS.items() if p == f), None)
        check(key is not None, f"coordination file {f} is one of the reviewed pins")
    wt = Path(lease["worktree"])
    head = lease["review_worktree_head"]
    check(lease.get("inference_base") == INFERENCE_BASE, "inference base c7b2ee3")
    check(git(wt, "rev-parse", "HEAD").decode().strip() == head, "replay worktree HEAD = candidate")
    check(git(wt, "status", "--porcelain", "--untracked-files=all") == b"", "replay worktree clean (incl. untracked)")
    check(git(REPO, "cat-file", "-e", f"{head}^{{commit}}", ok=True), "candidate commit is present in the repository")
    check(git(REPO, "merge-base", "--is-ancestor", INFERENCE_BASE, head, ok=True), "candidate descends from c7b2ee3")
    remotes = git(REPO, "for-each-ref", "--contains", head, "--format=%(refname)", "refs/remotes").decode().split()
    check(bool(remotes), f"candidate is published on a remote ref ({remotes[:3]})")
    tracked = git(REPO, "ls-tree", "-r", "--name-only", head, "--", ENGINE_DIR).decode().split("\n")
    tracked = [t for t in tracked if t]
    check(bool(tracked) and sorted(f for f in tracked if f.endswith(".py")) == sorted(lease.get("source_files", {})),
          "release pins exactly the candidate's tracked engine *.py files")
    for f in tracked:
        b = git(REPO, "cat-file", "blob", f"{head}:{f}")
        d = (wt / f).read_bytes()
        check(d == b, f"engine file {f} on disk equals its blob at the candidate")
        if f in lease.get("source_files", {}):
            check(sha(d) == lease["source_files"][f], f"source file {f} matches the release")
    non_py = [f for f in tracked if not f.endswith(".py")]
    if non_py:
        notes.append(f"executor binds HEAD and *.py digests only; {len(non_py)} non-.py engine file(s) {non_py[:4]} "
                     "are covered by this issue-time clean/blob check, not by device_lease.bind_inputs")
    orders = []
    for o in lease["orders"]:
        plan = Path(o["plan"])
        check(sha_file(plan) == o["plan_sha256"], f"{o['run']}: plan digest")
        cfg = json.loads(plan.read_bytes())
        check(cfg.get("stage") == stage and cfg.get("source") == head, f"{o['run']}: plan stage/source")
        check(Path(cfg.get("worktree", "")).resolve() == wt.resolve(), f"{o['run']}: plan worktree = release worktree")
        out = Path(o["output"]).resolve()
        check(out.is_relative_to((WP17 / "review/runs").resolve()) and not out.exists(), f"{o['run']}: new output root")
        for f, h in cfg.get("bound_files", {}).items():
            check(sha_file(Path(f)) == h, f"{o['run']}: bound file {Path(f).name} digest")
        for item in cfg.get("requests", []):
            check(sha_file(Path(item["pdf"])) == item["sha256"] and len(item["rgb_sha256"]) == item["pages"],
                  f"{o['run']}: request {item.get('label')} input pin")
        text = json.dumps(cfg).lower()
        check(not any(s in text for s in SEALED), f"{o['run']}: no truth/custody/sealed path in the plan")
        orders.append(dict(run=o["run"], plan_sha256=o["plan_sha256"], seconds=o["seconds"], output=str(out)))
    if stage == "A1":
        detail = review_a1(lease, coord_dir, check, notes)
    else:
        detail = None
        check(False, f"{stage}: no reviewed plan generator is bound in command.py yet (fail closed)")
    return dict(release=str(rel), release_sha256=digest, executor_sha256=executor_sha, candidate=head, stage=stage,
                orders=orders, worktree=str(wt), stage_detail=detail, coordinator_pins=pins, notes=notes)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action", choices=["review", "issue"])
    ap.add_argument("--name", required=True)
    ap.add_argument("--sha256", required=True)
    ap.add_argument("--stage", required=True, choices=["A1", "A2", "A3"])
    ap.add_argument("--coord-dir", type=Path, default=COORD_DIR)
    ap.add_argument("--commands-dir", type=Path, default=HERE / "commands")
    a = ap.parse_args()
    check = Check()
    r = review(a.name, a.sha256, a.stage, a.coord_dir, check)
    print(json.dumps(dict(review=r, checks=check.count, failures=check.failures), indent=1))
    if a.action == "issue":
        if check.failures:
            raise SystemExit("not issuing: independent review failed")
        cmd = dict(release_name=a.name, release_sha256=a.sha256, executor_sha256=r["executor_sha256"],
                   candidate=r["candidate"], operator="eld-rd-reviewer", action="execute once", stage=a.stage,
                   issued_utc=utc(), carrier=CARRIER, orders=r["orders"], reviewer_checks=check.count,
                   reviewer_notes=r["notes"], reviewer_session=OPERATOR_TEXT, reviewer_identity=OPERATOR)
        path = a.commands_dir / f"{a.name}.json"
        print(json.dumps(dict(command=str(path), sha256=write_new(path, cmd)), indent=1))
    return 0 if not check.failures else 1


if __name__ == "__main__":
    sys.exit(main())
