"""Independent CPU-only issue checks for the single WP-0017 A1 pair follow-up."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import command
import common
import escrow

HERE = common.HERE
ROOT = command.COORD_ROOT
COORD = command.COORD_DIR
RUNS = common.WP17 / "review/runs"
BASE = "62f4ce4407b3ef6093a412d0504408c500a42c92"
CANDIDATE = "c235bc61820def84142480e6e2a7a2e5485176d6"
RELEASE_COMMIT = "270306c25491892f7b3b4f597da647b7234add5c"
RELEASE = "02eef09347e60af3b99d34fbe9eb7bddaa3151d6abd93a8dd0b01131ed56d8a8"
PLAN = "6c391ef2a0d112c8aaad7a263a2860a5b3b164599a4c556bd661d8ff6d79608b"
DECISION = "b004ef0bda33ef21cbd4e6e337fa469522a4b9326efe4900575713dd9f517cb8"
INVENTORY = "2e3edc902b022b442a5e70dcd050d627f4510332e94f6d6e42b82dc1455809f3"
AUDIT = HERE / "evidence/A1-prefix-audit.json"
AUDIT_SHA = "16eca676114e847059503290b3c4a620eb1625769dd7f3a3e0a39ab252d263b3"
MODES = {"remove_S1b_S1c": "110011", "remove_S1b_S2": "110101", "remove_S1c_S2": "111001"}
IDENTITY = dict(role="eld-rd-reviewer", cli="Codex", model="gpt-6.2-astra", requested_effort="xhigh",
                session="/root/wp17_pair_reviewer", thread_id="01a1f0ec-5fe5-7480-a809-6fda624e72e0",
                assignment="Fresh independent reviewer and operator for the three A1 pair tests authorized by Jack on 2026-11-18 during Opus quota exhaustion.")


def pin(path, ref):
    data = command.git(ROOT, "cat-file", "blob", f"{ref}:{path.relative_to(ROOT).as_posix()}")
    if data != path.read_bytes():
        raise ValueError(f"Git blob differs from {path}")
    return data


def initial(check):
    inv = COORD / "a1-r1-blind-inventory.json"
    stored = COORD / "a1-r1-machine-decision.json"
    norm = COORD / "a1-r1-normalized.json"
    for p in (inv, stored, norm):
        pin(p, "f9190a14e91706147250d77ab6e18b57c710a1a6")
    check(common.sha_file(inv) == INVENTORY and common.sha_file(stored) == DECISION, "initial evidence digests")
    check(common.sha_file(AUDIT) == AUDIT_SHA, "frozen prefix audit digest")
    prior_inv = common.load(inv)
    check(not escrow.verify_unchanged(prior_inv), "entire original four run trees match prior blind digest")
    receipt = common.WP17 / "coordination/carrier/a1-r1/received.json"
    rec = common.load(receipt)
    prior = HERE / "commands/a1-r1.json"
    check(rec["operator_commit"] == BASE and rec["operator_command_sha256"] == common.sha_file(prior)
          and prior.read_bytes() == command.git(ROOT, "cat-file", "blob", BASE + ":docs/reviews/WP-0017/commands/a1-r1.json")
          and common.load(prior)["reviewer_identity"]["model"] == "claude-opus-5-5", "genuine initial operator and command")
    with tempfile.TemporaryDirectory(prefix="eld17-pair-review-") as scratch:
        temp = Path(scratch)
        def run(script, *args):
            subprocess.run([command.Q0, "-I", "-B", script, *args], check=True, stdout=subprocess.DEVNULL)
        run(HERE / "a1_sync.py", "--audit", AUDIT, "--audit-sha256", AUDIT_SHA, "--out", temp/"anchors.json")
        run(HERE / "a1_normalize.py", "--inventory", inv, "--endpoints", RUNS / "a1-r1-endpoints",
            "--switches", RUNS / "a1-r1-switches", "--out", temp/"normalized.json")
        run(HERE / "a1_decide.py", "--audit", AUDIT, "--audit-sha256", AUDIT_SHA, "--inventory", inv,
            "--results", temp/"normalized.json", "--out", temp/"decision.json")
        computed = common.load(temp/"normalized.json")
        previous = common.load(norm)
        del computed["created_utc"], previous["created_utc"]
        check(computed == previous, "initial normalization reproduces exactly, apart from timestamp")
        decision = common.load(temp/"decision.json")
        check(decision["checks_run"] == 800 and decision["failures"] == [] and decision["outcome"] == "PAIR_RUNS_REQUIRED"
              and decision["decision"] == common.load(stored)["decision"], "reproduced all 800 frozen decision checks and full decision")
        pairs = [m.removeprefix("remove_").split("_") for m in MODES]
        check(decision["decision"]["astra_rules_cross_check"]["pairs"] == dict(astra=pairs, reviewer=pairs, agree=True),
              "independent frozen design and reviewer eligibility agree")
        tie_script = COORD / "audit_probe_ties.py"
        pin(tie_script, "458a9c66896dbf9ac26dfbb08f73cb48d7edacce")
        run(tie_script, inv, temp/"ties.json")
        published = pin(COORD / "a1-r1-probe-ties.json", "458a9c66896dbf9ac26dfbb08f73cb48d7edacce")
        ties = common.load(temp/"ties.json")
        check(ties == json.loads(published) and (ties["probe_passes"], ties["tied_passes"], ties["differing_passes"]) == (73,35,14),
              "captured argmax and exact tied-logit defect reproduced from inventory")
    return dict(decision_checks=decision["checks_run"], adapter_checks=computed["checks_run"], inventory_sha256=INVENTORY,
                selected_pairs=pairs, probe_passes=73, tied_top_logits=35, topk_first_differs_from_argmax=14)


def verify_pair(lease, coord_dir, check, notes):
    order, = lease["orders"]
    p = Path(order["plan"])
    plan = common.load(p)
    expected, tag, name, inner, outer = command.a1_expected(p, plan, "pairs", tuple(MODES), 1800, coord_dir)
    expected["bound_files"][str(COORD / "a1-r1-machine-decision.json")] = DECISION
    check(plan == expected and tag == "p1" and lease["review_worktree_head"] == CANDIDATE
          and Path(lease["worktree"]) == ROOT.parent / "eledgercare-worktrees/ablation-replay", "entire independent pair plan")
    check(p == common.WP17/"coordination/plans/p1/a1-p1-pairs.json" and common.sha_file(p) == PLAN
          and pin(COORD/"a1-plans/a1-p1-pairs.json", RELEASE_COMMIT) == p.read_bytes(), "published order bytes")
    check(order == dict(run="a1-p1-pairs-order", plan=str(p), plan_sha256=PLAN, output=str(outer), seconds=1890,
                       argv=[str(command.Q0), "-I", "-B", str(coord_dir/"run_order.py"), str(p), PLAN]),
          "complete signed order envelope")
    check(not inner.exists() and not outer.exists(), "fresh run output paths")
    check(not (common.WP17/"coordination/leases/a1-p1").exists() and not (common.WP17/"coordination/carrier/a1-p1").exists(),
          "no previous lease or carrier activation")
    manifest = common.load(common.A1_MANIFEST[0])
    check([w["first_page"] for w in manifest["windows"]] == [19,37], "exclusive windows 019 and 037")
    import pypdfium2
    for request, idx in zip(plan["requests"], ([18,19,20,36,37,38], [0]), strict=True):
        with pypdfium2.PdfDocument(request["pdf"]) as pdf:
            check(len(pdf) == request["pages"], "PDF page count")
            for i in idx:
                pixels = pdf[i].render(scale=300/72).to_pil().convert("RGB").tobytes()
                check(common.sha(pixels) == request["rgb_sha256"][i], f"page {i+1} actual 300 DPI RGB")
    sys.path.insert(0, str(Path(lease["worktree"]) / command.ENGINE_DIR))
    from switches import resolve_mode
    for raw, bits in MODES.items():
        resolved = resolve_mode(raw)
        check(resolved.family == "pair_remove" and resolved.switch_config.bits == bits and
              resolved.canonical_name == raw and list(resolved.removed_switches) == raw.split("_")[1:],
              f"engine mask and removal: {raw} {bits}")
    check(not command.a1_candidate_ready(CANDIDATE), "existing independently reviewed S3 device-guard binding")
    return dict(modes=MODES, engine_seconds=1800, guard_seconds=1890, excluded_warmups_per_config=3)


def main():
    check = common.Check()
    pin(COORD / "a1-p1-release.json", RELEASE_COMMIT)
    initial_review = initial(check)
    # Reuse all frozen generic digest, guard, closure and candidate checks. This order
    # has one pair-specific plan instead of the first release's two initial plans.
    with patch.object(command, "review_a1", verify_pair):
        r = command.review("a1-p1", RELEASE, "A1", COORD, check)
    if check.failures:
        raise ValueError(check.failures)
    signed = dict(release_name="a1-p1", release_sha256=RELEASE, executor_sha256=r["executor_sha256"],
                  candidate=CANDIDATE, operator="eld-rd-reviewer", action="execute once", stage="A1",
                  issued_utc=common.utc(), carrier=command.CARRIER, orders=r["orders"],
                  reviewer_identity=IDENTITY, reviewer_checks=check.count, reviewer_notes=r["notes"],
                  initial_evidence=initial_review, pair_checks=r["stage_detail"])
    print(common.write_new(HERE/"commands/a1-p1.json", signed))


if __name__ == "__main__":
    main()

