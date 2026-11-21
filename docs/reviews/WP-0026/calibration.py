"""Independently classify actual fitted readouts in every frozen development-calibration grid cell."""
from itertools import product
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit_common import BASE,HOST,blob,cpu,pinned,read,save,sha
from preflights import PROBE,SCORER

def verify(weights,fit_pin,routing):
    import torch
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    from matrix_audit import materialize
    materialize(PROBE)
    from matrix import Memory,NeuralState,advance,result
    from online import load_window
    fit = pinned(weights/"fit.json",fit_pin)
    routes = pinned(routing,fit["input_hashes"]["cal"])
    labels = pinned(HOST.parent/"WP-0024/custody/v2/private/cal/truth.json",fit["input_hashes"]["cal_truth"])
    truth = {t["binder"]:t for t in labels["binders"]}
    assert len(truth) == 20 and len(routes["pairs"]) == 10
    scorer = {}
    code = blob(SCORER,"docs/fixtures/WP-0024/score.py")
    exec(compile(code,SCORER+":score.py","exec"),scorer)
    grids = {}
    with torch.inference_mode():
        for arm in ("M1","M3"):
            model = Memory(flat=arm=="M1").eval()
            file = weights/(arm+".pt")
            assert sha(file.read_bytes()) == fit["weights"][arm]
            model.load_state_dict(torch.load(file,weights_only=True,map_location="cpu"))
            states = {}
            for pair in routes["pairs"]:
                for t in pair["twins"]:
                    state = NeuralState(model.zero())
                    for i,p in enumerate(t["windows"],1):
                        advance(model,state,load_window(Path(p)),i,audit=False)
                    states[t["binder"]] = state
            assert states.keys() == truth.keys()
            actual = []
            selection = None
            for tau,margin in product((-.25,0.,.15,.30,.50,1.),(0.,.025,.05,.1)):
                posted = silent = correct = 0
                all_abstain = True
                for pair in routes["pairs"]:
                    outcomes = []
                    for member in pair["twins"]:
                        b = member["binder"]
                        r = result(states[b],(tau,margin))
                        posting = r["type"] == "Posting"
                        assessed = scorer["assessment"](r,truth[b])
                        outcomes.append(assessed["full"])
                        silent += bool(assessed["silent"])
                        posted += posting and not truth[b]["ambiguous"]
                        all_abstain &= not posting
                    correct += all(outcomes)
                stats = {"tau":tau,"margin":margin,"answerable_postings":posted,"correct_pairs":correct,"silent":silent}
                actual.append(stats)
                if [tau,margin] == fit["thresholds"][arm]:
                    selection = {"all_20_abstained":all_abstain,**stats}
            assert actual == fit["calibration"][arm]
            assert selection is not None
            grids[arm] = {"cells_reproduced":len(actual),"selected":selection,"full_grid":actual}
    return {"fit_sha256":fit_pin,"physical_calibration_binders":20,"physical_calibration_pairs":10,
            "ambiguous_pairs":sum(all(truth[t["binder"]]["ambiguous"] for t in p["twins"]) for p in routes["pairs"]),
            "scorer_source_sha256":sha(code),"actual_frozen_calibration":grids,"additional_fit_or_threshold_change":False}

if __name__ == "__main__":
    cpu()
    save(Path(sys.argv[4]),verify(Path(sys.argv[1]),sys.argv[2],Path(sys.argv[3])))
