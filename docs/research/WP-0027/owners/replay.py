"""WP-0027 part A. Run from run.ps1 with an owned fresh scratch directory."""
import datetime
import os
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from inputs import ROOT, TRUTH, check, prepare, record, sha


def run_replay(work):
    check(sys.flags.isolated and sys.flags.dont_write_bytecode and not sys.flags.optimize, "use -I -B")
    for k,v in {"CUDA_VISIBLE_DEVICES":"-1", "HF_HUB_OFFLINE":"1", "TRANSFORMERS_OFFLINE":"1",
                "HF_DATASETS_OFFLINE":"1", "PIP_NO_INDEX":"1"}.items():
        check(os.environ.get(k) == v, "missing process guard " + k)
    check(work.parent.parent == Path("C:/Users/jackg/eLedgerCare-Speed/WP-0027") and
          work.parent.name in {"owners","review","coordination"}, "unexpected scratch")
    for name in ("TEMP","TMP","TORCH_HOME","HF_HOME","XDG_CACHE_HOME","TORCHINDUCTOR_CACHE_DIR"):
        check(Path(os.environ[name]).parent == work, "unexpected cache path")
    started = time.perf_counter()
    fit, ref, manifest, logical, physical, inputs = prepare(work)
    sys.path.insert(0,str(work / "probe"))
    import torch
    import matrix
    import online
    import run
    from observe import paired_checkpoints, trace, values
    from ranking import inspect_binder, pair_row, posting_cells, summary
    run.setup()
    check(not torch.cuda.is_available() and torch.cuda.device_count() == 0, "CUDA visible")
    routes = run.manifest(manifest)
    truth = run.labels(TRUTH, "cal", routes)
    all_rows, all_progress, times = {}, {}, {}
    with torch.inference_mode():
        for arm in ("M1","M3"):
            start = time.perf_counter()
            model = matrix.Memory(flat=arm == "M1").eval()
            model.load_state_dict(torch.load(work / (arm + ".pt"), map_location="cpu", weights_only=True))
            check(all(p.device.type == "cpu" for p in model.parameters()), "non-CPU parameter")
            cuts,grid = run.calibrate(model,routes,truth)
            reference = ref["actual_frozen_calibration"][arm]
            selected = next(g for g in grid if [g["tau"],g["margin"]] == cuts)
            reproduced = (grid == reference["full_grid"] == fit["calibration"][arm] and
                          len(grid) == 24 and cuts == fit["thresholds"][arm] == [1.,.1] and
                          {"all_20_abstained": True,**selected} == reference["selected"] and
                          (selected["answerable_postings"], selected["correct_pairs"], selected["silent"]) == (0,2,0))
            all_rows[arm] = {"official_grid":grid, "selected":cuts, "original_calibration_reproduced":reproduced}
            if not reproduced:
                times[arm] = time.perf_counter()-start
                continue
            states, rows, pair_rows, progression = {}, {}, {}, {}
            for route in routes:
                members, data, traces, checkpoint_tensors = {}, {}, {}, {}
                for t in route["twins"]:
                    b = t["binder"]
                    tr = truth[b]
                    ws = [online.load_window(p) for p in t["windows"]]
                    original = run.state_for(model,ws)
                    states[b] = original
                    state,contexts,snapshots,numeric = trace(model,ws,original)
                    for g in grid:
                        thresholds = (g["tau"],g["margin"])
                        check(matrix.result(state,thresholds) == matrix.result(original,thresholds), "changed typed result")
                    row = {"binder":b, "pair":tr["pair"], "target":t["target"], "physical_tags":logical[b],
                           "final_registry":values(state.registry.choices()), **inspect_binder(state,contexts,tr,cuts)}
                    members[b] = rows[b] = row
                    data[b] = ws
                    checkpoint_tensors[b] = numeric
                    traces[b] = {"binder":b, "target":t["target"], "recorded_cues":state.trace,
                                 "expected_window1":tr["window1"], "checkpoints":snapshots}
                left,right = sorted(members)
                pair = members[left]["pair"]
                check(members[right]["pair"] == pair and pair not in pair_rows, "pair-truth identity mismatch")
                for b in members:
                    members[b]["twin_binder"] = right if b == left else left
                windows = []
                for i,(a,b) in enumerate(zip(data[left],data[right],strict=True)):
                    tags = {k:logical[k][i] for k in members}
                    pa,pb = (physical[tags[k]] for k in (left,right))
                    windows.append({"ordinal":i+1, "physical_tags":tags,
                                    "same_metadata_bytes": pa["metadata.json"] == pb["metadata.json"],
                                    "same_ordered_rgb":pa["ordered_rgb_sha256"] == pb["ordered_rgb_sha256"],
                                    "same_loaded_spans":a.spans == b.spans,
                                    "same_loaded_feature_bytes":a.features.numpy().tobytes() == b.features.numpy().tobytes()})
                same = all(windows[-1][k] for k in ("same_metadata_bytes","same_ordered_rgb","same_loaded_spans","same_loaded_feature_bytes"))
                pair_rows[pair] = {**pair_row(members,same),"input_comparison":windows}
                progression[pair] = {"by_binder":traces,"paired_checkpoints":paired_checkpoints(checkpoint_tensors)}
            check(len(rows) == 20 and len(pair_rows) == 10, "incomplete replay")
            check(all(r["selected_binder_decision"]["type"] == "ABSTAIN" for r in rows.values()), "expected 20 abstentions")
            all_rows[arm].update({"summary":summary(pair_rows, rows), "by_binder":rows, "by_pair":pair_rows,
                                  "posting_cells":posting_cells(states,truth,grid)})
            all_progress[arm] = progression
            times[arm] = time.perf_counter()-start
    record(work / "owner-rankings.json",{"arms":all_rows,"physical_windows":physical,"input_sha256":inputs})
    record(work / "owner-progression.json",{"arms":all_progress,
           "measurement":"Original cue and scope trace plus read-only checkpoints. Each checkpoint reads the current matrices using this binder's own eventual target query and current depth. Only before-target on an admitted target is an actual scoring read. Directory, cue and window boundaries are retrospective samples. Full and owner-column differences compare every lane. A difference alone does not identify information content."})
    output_hashes = {n:sha((work/n).read_bytes()) for n in ("owner-rankings.json","owner-progression.json")}
    head = subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
    record(work / "runtime.json",{"worktree_head":head,"python":sys.version,"executable":sys.executable,
           "command":sys.orig_argv,"interpreter_sha256":sha(Path(sys.executable).read_bytes()),"torch":str(torch.__version__),
           "cuda_available":torch.cuda.is_available(),"visible_device_count":torch.cuda.device_count(),
           "threads":torch.get_num_threads(),"default_dtype":str(torch.get_default_dtype()),
           "arm_cpu_replay_wall_seconds":times,"process_replay_wall_seconds":time.perf_counter()-started,
           "completed_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"output_sha256":output_hashes,
           "settings":{k:os.environ[k] for k in ("CUDA_VISIBLE_DEVICES","HF_HUB_OFFLINE","TRANSFORMERS_OFFLINE",
                      "HF_DATASETS_OFFLINE","PIP_NO_INDEX","TEMP","TMP","TORCH_HOME","HF_HOME","XDG_CACHE_HOME")}})
    print({"arms":{arm:out.get("summary","calibration mismatch") for arm,out in all_rows.items()},
           "sha256":output_hashes})


if __name__ == "__main__":
    run_replay(Path(sys.argv[1]).resolve())
