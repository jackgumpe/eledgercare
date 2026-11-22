"""Replay only original M1/M3. Compare candidates by normalized spelling and signed truth margins."""
import collections
import itertools
import json
from pathlib import Path
import sys
import time
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import BASE, ROOT, SCRATCH, SPEED, blob, loaded, save, sha

PROBE = "7db67283a4ffd3e7a20bb8d80499572cc7118c71"
FIT = "6d79c24364ba10a1d9bfa4c72c837e2f216cf4bc"
GRID = "b0d2dc9efee1ef27cf47e2929c05e8fbfde2fde0"
TROOT = SPEED / "WP-0026/author/fit-r1/result"
ORIG = "docs/research/WP-0024/probe/"
FITPATH = "docs/research/WP-0026/fit/"
ARCHIVE = "docs/reviews/WP-0026/cal-features-primary/primary-001.zip"
FIELDS = ("owner","unit","column","subtotal_status")

def prepare():
    source = SCRATCH / "probe"
    source.mkdir(exist_ok=True)
    for module in ("matrix.py","online.py","run.py","views.py"):
        (source/module).write_bytes(blob(PROBE,ORIG+module))
    sys.path.insert(0,str(source))

def replay():
    start = time.perf_counter()
    prepare()
    import torch
    from matrix import Memory, NeuralState, advance, result
    from online import key, load_window
    from run import setup
    setup()
    assert not torch.cuda.is_available()
    truth_raw = (SPEED/"WP-0024/custody/v2/private/cal/truth.json").read_bytes()
    assert sha(truth_raw) == "a227da1293bcd6f8b0f636ce3349abd12d02a52361a46b47dbf34969cc773ff1"
    truth = {(t["binder"],t["target"]):t for t in json.loads(truth_raw)["binders"]}
    fit = loaded(FIT,FITPATH+"fit.json")
    route_bytes = blob(FIT,FITPATH+"cal-transport.json")
    assert sha(route_bytes) == fit["input_hashes"]["cal"]
    routes = json.loads(route_bytes)["pairs"]
    reference = loaded(GRID,"docs/reviews/WP-0026/calibration-independent.json")["actual_frozen_calibration"]
    archive_path = ROOT/ARCHIVE
    assert blob(BASE,ARCHIVE) == archive_path.read_bytes()
    windows, inputs = {}, {}
    physical = SPEED/"WP-0026/review/runs/cal-features-r1/sensor"
    with ZipFile(archive_path) as archive:
        for route in routes:
            for twin in route["twins"]:
                for name in twin["windows"]:
                    path = Path(name)
                    if name in windows:
                        continue
                    assert path.parent == physical
                    prefix = "runs/cal-features-r1/sensor/"+path.name+"/"
                    receipt = json.loads(archive.read(prefix+"receipt.json"))
                    inputs[name] = {}
                    for filename in ("metadata.json", "pooled.f32", "through-eos.u32le"):
                        signed = archive.read(prefix+filename)
                        assert (path/filename).read_bytes() == signed
                        digest = sha(signed)
                        assert receipt["artifacts"][filename] == digest
                        inputs[name][filename] = digest
                    inputs[name]["ordered_source_pages"] = [p["sha256"] for p in receipt["pages"]]
                    windows[name] = load_window(path)
    assert len(windows) == 29
    arms = {}
    for arm in ("M1","M3"):
        model = Memory(flat=arm=="M1").eval()
        weights = TROOT/(arm+".pt")
        assert sha(weights.read_bytes()) == fit["weights"][arm]
        model.load_state_dict(torch.load(weights,weights_only=True,map_location="cpu"))
        tensor_digest = lambda ts: sha(b"".join(t.detach().cpu().contiguous().numpy().tobytes() for t in ts))
        reads = []
        unchanged_read = model.read
        def observe(matrices,depth,query,field):
            response = unchanged_read(matrices,depth,query,field)
            reads.append({"field":field,"depth":depth,"query_sha":tensor_digest([query]),
                          "matrices_sha":tensor_digest(matrices),"response_sha":tensor_digest([response]),
                          "norm":response.norm().item()})
            return response
        model.read = observe
        rows, states = {}, {}
        pairs = collections.defaultdict(list)
        with torch.inference_mode():
            for route in routes:
                pair_ids = set()
                for twin in route["twins"]:
                    k = (twin["binder"],twin["target"])
                    assert k not in states
                    t = truth[k]
                    pairs[t["pair"]].append(k)
                    pair_ids.add(t["pair"])
                    state = NeuralState(model.zero())
                    reads = []
                    checkpoints = []
                    for i,name in enumerate(twin["windows"],1):
                        checkpoints.append(tensor_digest(state.matrices))
                        advance(model,state,windows[name],i)
                    states[k] = state
                    attempts = []
                    for item in state.attempts:
                        fields = {}
                        for field in FIELDS:
                            choices = item.choices.get(field,())
                            scores = {key(v):float(s) for v,s in zip(choices,item.scores[field],strict=True)} if field in item.scores else {}
                            assert len(scores) in (0,len(choices))
                            expected = t[field]
                            delta = None
                            if expected is not None and key(expected) in scores and len(scores) > 1:
                                delta = scores[key(expected)]-max(s for name,s in scores.items() if name!=key(expected))
                            fields[field] = {"expected":expected,"scores":scores,"delta":delta}
                        attempts.append({"fields":fields,"reason":item.reason,"zero":item.zero,"summary":item.summary_target,
                                         "decision":item.typed((1.,.1)),"open_grid":item.typed((-.25,0.))})
                    rows[k] = {"binder":k[0],"target":k[1],"pair":t["pair"],"ambiguous":t["ambiguous"],
                               "stratum":t["stratum"],"attempts":attempts,"reads":reads,"events":state.trace,
                               "registry":state.registry.choices(),"window_entry_matrix":checkpoints,
                               "final_inputs":inputs[twin["windows"][-1]],"decision":result(state,(1.,.1))}
                assert len(pair_ids)==1
        assert set(states)==set(truth) and len(states)==20 and len(pairs)==10
        grid = []
        for tau, gap in itertools.product((-.25,0.,.15,.3,.5,1.),(0.,.025,.05,.1)):
            c = dict(tau=tau,margin=gap,answerable_postings=0,correct_pairs=0,silent=0)
            for members in pairs.values():
                good = []
                for k in members:
                    decision = result(states[k], (tau,gap))
                    posted = decision["type"]=="Posting"
                    t = truth[k]
                    c["answerable_postings"] += int(posted and not t["ambiguous"])
                    correct = not posted if t["ambiguous"] else posted and all(
                        (None if decision[f] is None else key(decision[f])) ==
                        (None if t[f] is None else key(t[f])) for f in FIELDS)
                    good.append(correct)
                    c["silent"] += int(posted and not correct)
                c["correct_pairs"] += int(all(good))
            grid.append(c)
        assert grid == reference[arm]["full_grid"] == fit["calibration"][arm]
        summaries = {}
        for p,members in pairs.items():
            first,second = [rows[k] for k in sorted(members)]
            assert first["final_inputs"] == second["final_inputs"]
            assert first["registry"]==second["registry"]
            assert first["ambiguous"]==second["ambiguous"]
            deltas = {}
            for r in (first,second):
                items=r["attempts"]
                deltas[r["binder"]]=items[0]["fields"]["owner"]["delta"] if len(items)==1 else None
            ds = list(deltas.values())
            category = "ambiguous"
            if not first["ambiguous"]:
                assert truth[members[0]]["owner"] != truth[members[1]]["owner"]
                category = ("unscorable" if None in ds else "tie" if 0 in ds else
                            ("neither","one","both")[sum(d>0 for d in ds)])
            summaries[p]={"deltas":deltas,"category":category}
        arms[arm] = {"grid":grid,"pairs":summaries,"rows":list(rows.values()),
                     "counts":dict(collections.Counter(p["category"] for p in summaries.values())),
                     "weight_sha256":fit["weights"][arm],
                     "selected_decisions":dict(collections.Counter(r["decision"]["reason"] for r in rows.values()))}
    return {"arms":arms,"runtime_seconds":time.perf_counter()-start,"torch":str(torch.__version__),
            "archive_sha256":sha(archive_path.read_bytes()),"truth_sha256":sha(truth_raw),
            "transport_sha256":sha(route_bytes),"physical_inputs":inputs}

if __name__ == "__main__":
    save(SCRATCH/sys.argv[1],replay())

