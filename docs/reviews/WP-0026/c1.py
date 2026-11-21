"""Audit uncached duplicates, then rerun six decision paths on pinned CPU fit artifacts."""
import argparse
import io
from pathlib import Path
import sys

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_common import HOST, MODEL, cpu, pinned, read, reference, sample, save, sha, stream
from w0_inputs import RECEIPT

def tensor_differences(left,right,name):
    import numpy as np
    dtype = "<u2" if name == "token_hidden.bf16" else "<u4"
    a,b = [np.frombuffer((p/name).read_bytes(),dtype=dtype) for p in (left,right)]
    if a.size != b.size or a.size % 1280:
        return {"same_shape":False,"elements":[int(a.size),int(b.size)]}
    a,b = a.reshape(-1,1280),b.reshape(-1,1280)
    difference = a != b
    where = np.flatnonzero(difference.any(axis=1))
    assert len(where)
    first = int(where[0])
    col = int(np.flatnonzero(difference[first])[0])
    if dtype == "<u2":
        af,bf = [(v.astype("<u4")<<16).view("<f4") for v in (a,b)]
    else:
        af,bf = [v.view("<f4") for v in (a,b)]
    delta = np.abs(af.astype(np.float64)-bf.astype(np.float64))
    limit = float(delta.max()) if np.isfinite(delta).all() else None
    return {"same_shape":True,"rows":len(a),"width":1280,"changed_rows":len(where),
            "changed_scalars":int(difference.sum()),"first_index":[first,col],
            "first_disagreeing_raw_bits":[int(a[first,col]),int(b[first,col])],"max_absolute_delta":limit}

def same_rasters(first,second):
    checks = []
    for left,right in zip(first,second,strict=True):
        png = Path(left["image"]).read_bytes()
        assert png == Path(right["image"]).read_bytes()
        assert sha(png) == left["sha256"] == right["sha256"]
        with Image.open(io.BytesIO(png)) as image:
            rgb = image.convert("RGB")
            assert rgb.size == (2550,3300)
            assert sha(rgb.tobytes()) == left["rgb_sha256"] == right["rgb_sha256"]
        checks.append([left["sha256"],left["rgb_sha256"]])
    assert len(checks) == 3
    return checks

def inspect(plan_file,pin,weights=None,fit_pin=None,probe=None,*,run_root=None):
    import c1_audit
    plan = pinned(plan_file,pin)
    assert plan["packet"] == "WP-0026" and plan["phase"] == "c1" and plan["split"] in ("train","blind")
    assert plan["model_revision"] == MODEL and plan["warmup"]["fixture_sha256"] == RECEIPT
    sensor = Path(plan["output"])/"sensor"
    assert sensor.parent.parent == (HOST/"review/runs" if run_root is None else run_root)
    assert read(sensor/"binding.json")["plan_sha256"] == pin
    assert len(plan["check_groups"]) == 12 and len(plan["calls"]) == 28
    calls = {c["tag"]:c for c in plan["calls"]}
    assert len(calls) == 28 and all(c["hooked"] and c["retain_hidden"] for c in calls.values())
    receipts, groups, failures = {}, [], []
    ref = reference()
    for tag in calls:
        try:
            receipts[tag] = sample(sensor/tag,True,ref)
        except Exception as exc:
            failures.append({"tag":tag,"error":repr(exc)})
    for g in plan["check_groups"]:
        a,b = (calls[g[k]] for k in ("left","right"))
        assert g["mode"] == "duplicate" and a["binder"] != b["binder"] and a["window"] == b["window"]
        left,right = sensor/a["tag"],sensor/b["tag"]
        compared = {}
        for name in ("metadata.json","observed-positions.json","token_hidden.bf16","pooled.f32",
                     "through-eos.u32le","capture.json"):
            try:
                compared[name] = (left/name).read_bytes() == (right/name).read_bytes()
            except OSError as exc:
                compared[name] = repr(exc)
        try:
            na,nb = read(left/"native.json"),read(right/"native.json")
            compared.update({k:na[k] == nb[k] for k in ("prompt","prompt_token_ids","eos_id","terminal_observation",
                                                         "token_ids","text","stop_cause","finish_reason")})
            compared["observed_through_eos"] = stream(left) == stream(right)
            rasters = same_rasters(a["pages"],b["pages"])
        except Exception as exc:
            failures.append({"pair":[a["tag"],b["tag"]],"error":repr(exc)})
            rasters = []
        if not all(v is True for v in compared.values()):
            failures.append({"pair":[a["tag"],b["tag"]],"differences":[k for k,v in compared.items() if v is not True]})
        tensor = {name:tensor_differences(left,right,name) for name in ("token_hidden.bf16","pooled.f32")
                  if compared[name] is False}
        groups.append({"left":a["tag"],"right":b["tag"],"window":a["window"],"encoded_and_rgb":rasters,
                       "equal":compared,"retained_tensor_disagreements":tensor})
    result = {"stage":"uncached","plan_sha256":pin,"candidate":plan["candidate"],"split":plan["split"],
              "warmup_fixture_sha256":RECEIPT,"sensor_tree":plan["sensor_tree"],"model_revision":MODEL,
              "samples":receipts,"duplicates":groups,"failures":failures}
    if failures:
        return result | {"gate":"FAIL"}
    inherited,pairs = c1_audit.inspect(plan_file,pin)
    result["inherited_two_complete_horizons"] = {k:v for k,v in inherited.items() if k != "slots"}
    if weights:
        assert fit_pin and probe and len(probe) == 40
        # The historical reader's only environmental override targets its old scratch.
        # The WP26 CPU policy already selects the isolated packet-local directory.
        c1_audit.isolated_environment = cpu
        result["stage"] = "frozen_fit_decision_equivalence"
        result["fit_sha256"] = fit_pin
        result["probe_revision"] = probe
        result["six_view_equivalence"] = c1_audit.decisions(pairs,weights,fit_pin,probe)
    return result | {"gate":"PASS"}

if __name__ == "__main__":
    cpu()
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("plan",type=Path)
    cli.add_argument("sha")
    cli.add_argument("output",type=Path)
    cli.add_argument("--weights",type=Path)
    cli.add_argument("--fit-pin")
    cli.add_argument("--probe-revision")
    args = cli.parse_args()
    result = inspect(args.plan,args.sha,args.weights,args.fit_pin,args.probe_revision)
    save(args.output,result)
    sys.exit(0 if result["gate"] == "PASS" else 2)
