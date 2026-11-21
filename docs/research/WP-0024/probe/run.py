"""CPU-only fit or inference from exclusively named manifests; see PROTOCOL.md."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

if os.environ.get("CUDA_VISIBLE_DEVICES") not in ("", "-1"):
    raise RuntimeError("hide CUDA devices before launching this CPU probe")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import torch
from torch.nn import functional as F
from matrix import Memory, NeuralState, advance, result
from online import key, load_window
from views import predict_pair

SEED = 2401
EPOCHS = 6
SIMILARITIES = (-0.25, 0., .15, .30, .50, 1.)
MARGINS = (0., .025, .05, .10)
FIELDS = ("owner", "unit", "column", "subtotal_status")


def setup():
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.manual_seed(SEED)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save_json(path, obj):
    with path.open("x", encoding="utf-8", newline="\n") as out:
        json.dump(obj, out, indent=2, sort_keys=True, allow_nan=False)
        out.write("\n")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def manifest(path):
    path = Path(path)
    pairs = read_json(path)["pairs"]
    ids = set()
    for pair in pairs:
        twins = pair["twins"]
        if len(twins) != 2 or len(twins[0]["windows"]) != len(twins[1]["windows"]):
            raise ValueError("expected two horizon-matched twins")
        for t in twins:
            if t["binder"] in ids or len(t["windows"]) not in (4, 10):
                raise ValueError("duplicate binder or invalid horizon")
            ids.add(t["binder"])
            t["windows"] = [path.parent / w for w in t["windows"]]
    return pairs


def labels(path, split, pairs):
    # Development sidecars have separate custody paths. The inference command
    # has no truth argument and cannot import the custodian's scoring module.
    path = Path(path)
    if path.name != "truth.json" or path.parent.name != split:
        raise ValueError("incorrect development label sidecar")
    rows = read_json(path)["binders"]
    table = {r["binder"]: r for r in rows}
    expected = {(t["binder"], t["target"]) for p in pairs for t in p["twins"]}
    if len(rows) != len(table) or len(pairs) != 10 or len(expected) != 20:
        raise ValueError("development split size mismatch")
    if {(k, v["target"]) for k, v in table.items()} != expected:
        raise ValueError("development manifest and truth disagree")
    return table


def state_for(model, windows):
    state = NeuralState(model.zero())
    for i, window in enumerate(windows, 1):
        advance(model, state, window, i, audit=False)
    return state


def train_one(model, train_pairs, table):
    opt = torch.optim.AdamW(model.parameters(), lr=.0005, weight_decay=.01)
    history = []
    ever_grad = {name: False for name, _ in model.named_parameters()}
    train_inputs = {t["binder"]: [load_window(w) for w in t["windows"]]
                    for p in train_pairs for t in p["twins"]}
    start = time.perf_counter_ns()
    for epoch in range(EPOCHS):
        count, steps, skipped, total = 0, 0, {}, 0.
        for pair in train_pairs:
            for t in pair["twins"]:
                def skip(why):
                    skipped[why] = skipped.get(why, 0) + 1

                truth = table[t["binder"]]
                if truth["ambiguous"]:
                    skip("full_history_ambiguous")
                    continue
                state = state_for(model, train_inputs[t["binder"]])
                if len(state.attempts) != 1:
                    skip("target_count")
                    continue
                item = state.attempts[0]
                if item.reason:
                    skip(item.reason)
                    continue
                losses = []
                for f in FIELDS:
                    if truth[f] is None:
                        continue
                    values = [key(v) for v in item.choices.get(f, ())]
                    target = key(truth[f])
                    if f not in item.scores or values.count(target) != 1:
                        skip("unavailable_" + f)
                        continue
                    y = torch.tensor([values.index(target)])
                    losses.append(F.cross_entropy(8 * item.scores[f][None], y))
                if not losses:
                    continue
                loss = torch.stack(losses).mean()
                opt.zero_grad(set_to_none=True)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1., error_if_nonfinite=True)
                for name, p in model.named_parameters():
                    if p.grad is not None and not ever_grad[name]:
                        ever_grad[name] = bool(p.grad.abs().max().item() > 0)
                opt.step()
                count += len(losses)
                steps += 1
                total += loss.item()
        history.append({"epoch": epoch + 1, "binder_steps": steps, "supervised_fields": count,
                        "loss_sum": total, "skips": skipped})
        if not steps:
            raise ValueError(f"no usable development supervision in epoch {epoch + 1}: {skipped}")
    return {"training_seconds": (time.perf_counter_ns() - start) / 1e9, "epochs": history,
            "nonzero_gradient_by_parameter_tensor": ever_grad}


def classification(decision, truth):
    if decision["type"] not in ("Posting", "ABSTAIN"):
        raise ValueError("unknown calibration decision type")
    posting = decision["type"] == "Posting"
    if truth["ambiguous"]:
        return not posting, posting, posting
    def same(field):
        value, expected = decision.get(field), truth[field]
        if value is None or expected is None:
            return value is expected
        # casefold, decoded HTML entities and folded whitespace; literal
        # markup is content. Keep the original spelling in the typed record.
        return key(value) == key(expected)

    ok = posting and all(same(f) for f in FIELDS)
    return ok, posting and not ok, posting


@torch.inference_mode()
def calibrate(model, pairs, table):
    attempts = []
    for p in pairs:
        twins = []
        for t in p["twins"]:
            state = state_for(model, [load_window(w) for w in t["windows"]])
            twins.append((state, table[t["binder"]]))
        attempts.append(twins)
    grid = []
    for tau in SIMILARITIES:
        for margin in MARGINS:
            correct_pairs = silent = coverage = 0
            for twins in attempts:
                ok_pair = True
                for state, truth in twins:
                    ok, wrong, posted = classification(result(state, (tau, margin)), truth)
                    ok_pair &= ok
                    silent += int(wrong)
                    coverage += int(posted and not truth["ambiguous"])
                correct_pairs += int(ok_pair)
            grid.append({"tau": tau, "margin": margin, "silent": silent,
                         "correct_pairs": correct_pairs, "answerable_postings": coverage})
    best = max(grid, key=lambda g: (-g["silent"], g["correct_pairs"], g["answerable_postings"],
                                    g["tau"], g["margin"]))
    return [best["tau"], best["margin"]], grid


def fit(args, output):
    train, cal = manifest(args.train), manifest(args.cal)
    train_truth, cal_truth = labels(args.train_truth, "train", train), labels(args.cal_truth, "cal", cal)
    if train_truth.keys() & cal_truth.keys():
        raise ValueError("development split overlap")
    receipt = {"format": 1, "seed": SEED, "epochs": EPOCHS, "torch": str(torch.__version__),
               "input_hashes": {name: digest(getattr(args, name))
                                for name in ("train", "cal", "train_truth", "cal_truth")},
               "thresholds": {}, "weights": {}, "training": {}, "calibration": {}}
    for name in ("M1", "M3"):
        torch.manual_seed(SEED)
        model = Memory(flat=name == "M1").train()
        if sum(p.numel() for p in model.parameters()) != 880258:
            raise ValueError("parameter budget mismatch")
        receipt["training"][name] = train_one(model, train, train_truth)
        model.eval()
        receipt["thresholds"][name], receipt["calibration"][name] = calibrate(model, cal, cal_truth)
        save_json(output / (name + "-development.json"),
                  {"training": receipt["training"][name], "calibration": receipt["calibration"][name],
                   "thresholds": receipt["thresholds"][name]})
        path = output / (name + ".pt")
        torch.save(model.state_dict(), path)
        receipt["weights"][name] = digest(path)
    if [e["binder_steps"] for e in receipt["training"]["M1"]["epochs"]] != [
            e["binder_steps"] for e in receipt["training"]["M3"]["epochs"]]:
        raise ValueError("unequal optimization budgets")
    save_json(output / "fit.json", receipt)


def infer(args, output):
    weights = Path(args.weights)
    if digest(weights / "fit.json") != args.fit_sha256:
        raise ValueError("unfrozen fit receipt")
    fit_record = read_json(weights / "fit.json")
    models = []
    for name in ("M1", "M3"):
        path = weights / (name + ".pt")
        if digest(path) != fit_record["weights"][name]:
            raise ValueError("unfrozen weights")
        model = Memory(flat=name == "M1").eval()
        model.load_state_dict(torch.load(path, weights_only=True, map_location="cpu"))
        models.append(model)
    predictions, telemetry = [], []
    for p in manifest(args.manifest):
        twins = p["twins"]
        signals = [[load_window(w) for w in t["windows"]] for t in twins]
        out = predict_pair(*models, fit_record["thresholds"], *signals)
        for twin, records in zip(twins, out):
            for arm, record in records.items():
                ids = {"binder": twin["binder"], "target": twin["target"], "arm": arm}
                semantic = {k: record[k] for k in ("trace", "target_scores", "final_entry", "subtotal_diagnostic", "binding_diagnostic", "window1_audit", "candidate_receipt") if k in record}
                predictions.append({**ids, **record["decision"], **semantic})
                other = {k: v for k, v in record.items() if k != "decision" and k not in semantic}
                telemetry.append({**ids, **other})
    save_json(output / "predictions.json", {"predictions": predictions})
    save_json(output / "telemetry.json", {"cached_cpu": telemetry, "probe_cuda_allocated_bytes": 0})
    save_json(output / "freeze.json", {"predictions_sha256": digest(output / "predictions.json"),
                                       "telemetry_sha256": digest(output / "telemetry.json"),
                                       "manifest_sha256": digest(args.manifest),
                                       "fit_sha256": args.fit_sha256})


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="mode", required=True)
    train = sub.add_parser("fit")
    for opt in ("train", "train-truth", "cal", "cal-truth"):
        train.add_argument("--" + opt, required=True)
    predict = sub.add_parser("infer")
    for opt in ("manifest", "weights", "fit-sha256"):
        predict.add_argument("--" + opt, required=True)
    for s in (train, predict):
        s.add_argument("--output", required=True)
    args = p.parse_args()
    setup()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    start = time.perf_counter_ns()
    try:
        if args.mode == "fit":
            fit(args, output)
        else:
            infer(args, output)
    except Exception as exc:
        save_json(output / "failure.json", {"mode": args.mode, "exception_type": type(exc).__name__,
                                            "message": str(exc),
                                            "elapsed_seconds": (time.perf_counter_ns() - start) / 1e9})
        raise


if __name__ == "__main__":
    main()
