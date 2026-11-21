"""Exercise the duplicate and decision readers on a manufactured routing of retained development bytes."""
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from zipfile import ZipFile

sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit_common import BASE, HOST, MODEL, ROOT, SCRATCH, blob, cpu, read, save, sha, stream
from h0 import originals
from w0_inputs import RECEIPT
from preflights import PROBE

def exercise(tmp):
    import c1
    archive = ROOT/"docs/reviews/WP-0024/h0-r1.zip"
    assert sha(archive.read_bytes()) == "37670af4116f543e2d0104b5d3599d88f2e2d06fc092418ee1cf839769430fc6"
    original, _ = originals()
    old = {c["tag"]:c for c in original["calls"]}
    run, sensor = tmp/"tape",tmp/"tape/sensor"
    sensor.mkdir(parents=True)
    check, calls, pairs = [],[],[]
    with ZipFile(archive) as z:
        for horizon in (4,10):
            twins = []
            for side in (1,2):
                binder = f"artificial-{horizon}-{side}"
                windows = []
                for i in range(horizon):
                    n = 1 if i==0 else 2+(i-1)%3
                    old_tag = f"b{(side if i==0 else 1):02d}w{n:02d}H"
                    tag = f"k{len(calls)+1:04d}"
                    d = sensor/tag
                    d.mkdir()
                    prefix = f"run/sensor/{old_tag}/"
                    for path in z.namelist():
                        if path.startswith(prefix):
                            (d/path.removeprefix(prefix)).write_bytes(z.read(path))
                    (d/"through-eos.u32le").write_bytes(stream(d,False))
                    calls.append({"tag":tag,"binder":binder,"window":i+1,"pages":old[old_tag]["pages"],
                                  "hooked":True,"retain_hidden":True})
                    windows.append(tag)
                twins.append({"binder":binder,"windows":windows})
            for a,b in zip(twins[0]["windows"][1:],twins[1]["windows"][1:],strict=True):
                check.append({"mode":"duplicate","left":a,"right":b})
            pairs.append({"twins":twins})
    plan = {"packet":"WP-0026","phase":"c1","split":"train","model_revision":MODEL,"warmup":{"fixture_sha256":RECEIPT},
            "output":str(run),"candidate":BASE,"sensor_tree":"archival-test-only","calls":calls,"check_groups":check,
            "delivery":{"pairs":pairs}}
    path = tmp/"cpu-plan.json"
    save(path,plan)
    pin = sha(path.read_bytes())
    save(sensor/"binding.json",{"plan_sha256":pin})
    # These untrained deterministic weights exercise only the decision comparison, never train or select an arm.
    weights = tmp/"toy"
    weights.mkdir()
    import torch
    from matrix_audit import materialize
    materialize(PROBE)
    from matrix import Memory
    torch.manual_seed(101)
    digests = {}
    for name in ("M1","M3"):
        file = weights/(name+".pt")
        torch.save(Memory(name=="M1").state_dict(),file)
        digests[name] = sha(file.read_bytes())
    fit = weights/"fit.json"
    save(fit,{"weights":digests,"thresholds":{"M1":[0.0,0.0],"M3":[0.0,0.0]}})
    positive = c1.inspect(path,pin,weights,sha(fit.read_bytes()),PROBE,run_root=tmp)
    assert positive["gate"] == "PASS" and len(positive["six_view_equivalence"]) == 2
    changed = sensor/check[-1]["right"]/"pooled.f32"
    with changed.open("r+b") as f:
        v = f.read(1)
        f.seek(0)
        f.write(bytes([v[0]^1]))
    negative = c1.inspect(path,pin,run_root=tmp)
    assert negative["gate"] == "FAIL"
    assert negative["failures"][-1]["differences"] == ["pooled.f32"]
    return {"purpose":"Manufactured duplicate routing over WP24 archive, CPU only, untrained toy models",
            "positive":{k:positive[k] for k in ("gate","inherited_two_complete_horizons","six_view_equivalence")},
            "one_bit_pool_corruption":{"gate":negative["gate"],"failures":negative["failures"]},
            "real_wp26_device_rows":0,"fit_or_calibration":False}

if __name__ == "__main__":
    cpu()
    with TemporaryDirectory(dir=SCRATCH) as d:
        save(Path(sys.argv[1]),exercise(Path(d)))
