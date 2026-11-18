"""Release only the two admitted regression keys after published pre-key reviewer custody."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from bind_plans import HERE, PACKET, PREVIOUS, REPO, publish, encoded
from inventory import inspect, read, sha


def release(args):
    if not (len(args.freeze) == 40 and len(args.blind_digest) == 64):
        raise ValueError("Full reviewer revision and pre-key artifact digest required")
    subprocess.run(["git","merge-base","--is-ancestor",args.freeze,"origin/review/wp-0016-escrow"],check=True,cwd=REPO)
    blind_path = args.inventory.resolve(strict=True)
    if sha(blind_path) != args.blind_digest:
        raise ValueError("Reviewer inventory differs")
    ref = subprocess.check_output(["git","show",args.freeze + ":" + args.receipt_path],cwd=REPO)
    if args.blind_digest.encode() not in ref:
        raise ValueError("Published receipt does not bind this blind inventory")
    lease = read(args.release)
    lease_out = PACKET / "coordination/leases" / lease["name"]
    outer = read(lease_out / "returned.json")
    if outer["error"] or outer["release_sha256"] != sha(args.release):
        raise ValueError("G0 lease has a guard or source failure")
    for o in lease["orders"]:
        ret = read(lease_out / (o["run"]+"-returned.json"))
        if ret["exit"] or ret["guard"]:
            raise ValueError("G0 crossover incomplete")
    verified = inspect(lease)
    independent = PACKET / "coordination/g0-origins-blind.json"
    publish(independent, encoded(verified))
    frozen_inputs = read(HERE/"g0-plans.json")["inputs"]
    staged, identities = [], {}
    for family in ("A","H"):
        identities[family] = {}
        source = PREVIOUS / ("scoring-" + family)
        dest = PACKET / "review/scoring" / family
        for name in ("truth.json","rasters.json"):
            payload = (source/name).read_bytes()
            actual = hashlib.sha256(payload).hexdigest()
            assert actual == frozen_inputs[family]["files"][name]
            staged.append((dest/name,payload))
            identities[family][name] = actual
        source_pdf = frozen_inputs[family]["files"]["source.pdf"]
        for order in ("ab","ba"):
            if family == "A":
                path = PREVIOUS / "runs/a-recovery-ab/04-a-windows"
            elif order == "ab":
                path = PREVIOUS / "runs/h-r1-ab/04-h-windows"
            else:
                path = PREVIOUS / "runs/h-r2-ba/03-h-windows"
            t = read(path/"timing.json")
            expected = t["prediction_sha256"]
            assert expected == sha(path/"prediction.json") and t["request"]["sha256"] == source_pdf
            name = f"windows-{order}"
            for file in ("prediction.json","timing.json"):
                staged.append((dest/name/file,(path/file).read_bytes()))
            identities[family][name] = {"sha256":expected,"elapsed_s":t["elapsed_s"]}
    for file, payload in staged:
        publish(file, payload)
    receipt = {"reviewer_prekey":args.freeze,"private_inventory_sha256":args.blind_digest,
               "coordinator_prekey_sha256":sha(independent),"gate":"G0","source":lease["review_worktree_head"],
               "keys_and_reference_predictions":identities,"B":"sealed"}
    publish(HERE/"g0-scoring-release.json",encoded(receipt))
    print("Released A and H keys and matching Windows references to reviewer only.")


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("release",type=Path)
    p.add_argument("freeze")
    p.add_argument("receipt_path")
    p.add_argument("inventory",type=Path)
    p.add_argument("blind_digest")
    release(p.parse_args())
