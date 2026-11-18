"""Bind the pair follow-up to the unchanged review program's published A1 result."""
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare_a1 import HERE, PACKET, Q0, SWITCHES, sha

BASE = "c235bc61820def84142480e6e2a7a2e5485176d6"
REPO = HERE.parents[2]
DECISION = HERE / "a1-r1-machine-decision.json"
SELECTION = "b004ef0bda33ef21cbd4e6e337fa469522a4b9326efe4900575713dd9f517cb8"
ANCHOR = PACKET / "coordination/a1-inputs.json"
ANCHOR_SHA = "e7f47d141972d0e32c53d16e090fcddc237c453ecfc2eaf5d494c6d3426bc8ef"
LEASE_ID = "a1-p1"
RUN = "a1-p1-pairs"
SECONDS = 1800


def main(worktree):
    worktree = worktree.resolve(strict=True)
    head = subprocess.check_output(["git", "-C", worktree, "rev-parse", "HEAD"], text=True).strip()
    if head != BASE or subprocess.check_output(["git", "-C", worktree, "status", "--porcelain"]):
        raise ValueError("pair follow-up requires the same clean GPU candidate")
    rel = DECISION.relative_to(REPO).as_posix()
    published = subprocess.check_output(["git", "-C", REPO, "show", "origin/coordination/bootstrap:" + rel])
    if published != DECISION.read_bytes() or sha(DECISION) != SELECTION or sha(ANCHOR) != ANCHOR_SHA:
        raise ValueError("published decision or frozen inputs differ")
    record = json.loads(published)
    decision = record["decision"]
    pairs = decision["eligible_pairs"]
    cross_check = decision["astra_rules_cross_check"]["pairs"]
    if (record["outcome"] != "PAIR_RUNS_REQUIRED" or record["failures"] or not pairs
            or cross_check != {"astra": pairs, "reviewer": pairs, "agree": True}):
        raise ValueError("no verified pair release")
    if len(pairs) != len({tuple(pair) for pair in pairs}) or any(
        len(pair) != 2 or SWITCHES.index(pair[0]) >= SWITCHES.index(pair[1]) for pair in pairs
    ):
        raise ValueError("unexpected pair ordering")
    modes = ["remove_" + "_".join(pair) for pair in pairs]
    if decision["pair_runs"] != ["remove_" + "+".join(pair) for pair in pairs]:
        raise ValueError("reviewer follow-up names differ")
    anchor = json.loads(ANCHOR.read_bytes())
    warm = dict(pages=1, pdf=str(worktree / "docs/research/WP-0014/eld-latency-author/A.pdf"),
                sha256="25c14530845cad96329b528f860032c27a1259ed46de3ccb56f0e57730aa0858",
                rgb_sha256=["a189916661ad64469762ea65a693b49c0d59ca2508df2742cc5d92b60f7dd18d"])
    inner = PACKET / "review/runs" / RUN
    outer = inner.with_name(RUN + "-order")
    argv = [str(Q0), "-I", "-B", str(worktree / "docs/research/WP-0017/engine/launch.py"),
            "--source", head, "--owner", "review", "--run", RUN, "--lease", LEASE_ID,
            "--plan", str(ANCHOR), "--sha256", ANCHOR_SHA, "--seconds", str(SECONDS), "--min-vram-mib", "12000",
            "--warmup-count", "3", "--configs", ",".join(modes)]
    if inner.exists() or outer.exists():
        raise FileExistsError("pair follow-up already has run data")
    plan = dict(stage="A1", worktree=str(worktree), source=head, output=str(outer),
                requests=[dict(anchor["request"]), warm], bound_files={str(ANCHOR): ANCHOR_SHA, str(DECISION): SELECTION},
                commands=[dict(label=RUN, argv=argv, required_outputs=[str(inner / "process.json")])])
    dest = PACKET / "coordination/plans/p1" / (RUN + ".json")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("x", encoding="utf8", newline="\n") as stream:
        json.dump(plan, stream, indent=2)
        stream.write("\n")
    print(dest, sha(dest), modes)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
