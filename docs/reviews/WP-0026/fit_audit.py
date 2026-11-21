"""Check frozen fit files, source-bound development labels, budgets and the complete declared calibration grid."""
from itertools import product
import math
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit_common import ROOT,cpu,pinned,read,save,sha
from preflights import PROBE

def inspect(weights,pin,train,cal):
    import torch
    from matrix_audit import materialize
    materialize(PROBE)
    from matrix import Memory
    fit = pinned(weights/"fit.json",pin)
    assert fit["seed"] == 2401 and fit["epochs"] == 6 and set(fit["weights"]) == {"M1","M3"}
    routing = {}
    for split,folder in (("train",train),("cal",cal)):
        manifest = read(folder)
        assert len(manifest["pairs"]) == 10
        routing[split] = {t["binder"] for p in manifest["pairs"] for t in p["twins"]}
        assert len(routing[split]) == 20 and sha(folder.read_bytes()) == fit["input_hashes"][split]
        signed = read(ROOT/"docs/fixtures/WP-0024/v2"/split/"receipt.json")
        assert set(signed["source_pdfs"]) == routing[split] and fit["input_hashes"][split+"_truth"] == signed["truth_sha256"]
    assert not routing["train"] & routing["cal"]
    results = {}
    for name in ("M1","M3"):
        weight = weights/(name+".pt")
        assert sha(weight.read_bytes()) == fit["weights"][name]
        tensors = torch.load(weight,map_location="cpu",weights_only=True)
        model = Memory(name=="M1")
        model.load_state_dict(tensors,strict=True)
        assert sum(p.numel() for p in model.parameters()) == 880258
        torch.manual_seed(fit["seed"])
        initial = Memory(name=="M1").state_dict()
        assert all(torch.isfinite(t).all() for t in tensors.values())
        changed = [k for k in tensors if not torch.equal(tensors[k],initial[k])]
        assert changed
        grid = fit["calibration"][name]
        assert len(grid) == 24 and set((r["tau"],r["margin"]) for r in grid) == set(product((-.25,0.,.15,.3,.5,1.),(0.,.025,.05,.1)))
        order = sorted(grid,key=lambda r:(r["silent"],-r["correct_pairs"],-r["answerable_postings"],-r["tau"],-r["margin"]))
        assert fit["thresholds"][name] == [order[0]["tau"],order[0]["margin"]]
        history = fit["training"][name]
        assert [e["epoch"] for e in history["epochs"]] == [1,2,3,4,5,6]
        assert all(0 < e["binder_steps"] <= 20 and math.isfinite(e["loss_sum"]) for e in history["epochs"])
        assert set(history["nonzero_gradient_by_parameter_tensor"]) == set(k for k,_ in model.named_parameters())
        results[name] = {"weights_sha256":sha(weight.read_bytes()),"epochs":history["epochs"],"train_s":history["training_seconds"],
                         "nonzero_gradient_tensors":sum(history["nonzero_gradient_by_parameter_tensor"].values()),
                         "changed_tensors":changed,"matched_parameters":880258,"calibration_rows":24,"winner":order[0]}
    for field in ("binder_steps","supervised_fields"):
        assert [r[field] for r in results["M1"]["epochs"]] == [r[field] for r in results["M3"]["epochs"]]
    return {"fit_sha256":pin,"probe_revision":PROBE,"input_hashes":fit["input_hashes"],"checks":results,"retraining":False}

if __name__=="__main__":
    cpu()
    save(Path(sys.argv[5]),inspect(Path(sys.argv[1]),sys.argv[2],Path(sys.argv[3]),Path(sys.argv[4])))
