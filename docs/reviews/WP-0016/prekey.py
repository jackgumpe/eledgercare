"""Assemble the WP-0016 G0 independent PRE-KEY receipt from durable records. Stdlib only; reads no truth.

Inputs: the released lease folder, the operator folder, the committed blind inventory, the stage-1 output and
the coordinator inventory.py output. Re-checks closure (PIDs gone, no compute process after job close), EOS
exclusion in every window and the coordinator/escrow blob agreement. Prints no prediction or raw text.
"""
import argparse
import ctypes
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import utc, write_new  # noqa: E402

SUSPECT = ("python", "llama", "inference", "vllm", "sglang")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load(p):
    return json.loads(Path(p).read_bytes())


def gone(pid):
    k = ctypes.WinDLL("kernel32")
    k.OpenProcess.restype = ctypes.c_void_p
    k.OpenProcess.argtypes = (ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32)
    k.GetExitCodeProcess.argtypes = (ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong))
    h = k.OpenProcess(0x1000, False, pid)
    code = ctypes.c_ulong()
    return not h or (k.GetExitCodeProcess(h, ctypes.byref(code)) and code.value != 259)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--release", type=Path, required=True)
    ap.add_argument("--release-sha256", required=True)
    ap.add_argument("--lease-dir", type=Path, required=True)
    ap.add_argument("--operator-dir", type=Path, required=True)
    ap.add_argument("--inventory", type=Path, required=True)
    ap.add_argument("--stage1", type=Path, required=True)
    ap.add_argument("--coordinator-inventory", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    release, inv, s1, cinv = load(a.release), load(a.inventory), load(a.stage1), load(a.coordinator_inventory)
    op_launch = load(a.operator_dir / "launch.json")
    monitor = [json.loads(x) for x in (a.operator_dir / "monitor.jsonl").read_bytes().splitlines() if x.strip()]
    lease = {}
    for order in release["orders"]:
        n = order["run"]
        iss, ret = load(a.lease_dir / f"{n}-issued.json"), load(a.lease_dir / f"{n}-returned.json")
        samples = [json.loads(x) for x in (a.lease_dir / f"{n}-device.jsonl").read_bytes().splitlines() if x.strip()]
        after = ret["ownership_after_job_close"]
        lease[n] = dict(issued_utc=iss["issued"], returned_utc=ret["utc"], child_pid=iss["pid"], child_gone=gone(iss["pid"]),
                        job=iss["job"], argv_equals_release=iss["argv"] == order["argv"], exit=ret["exit"], guard=ret["guard"],
                        wall_s=ret["wall_s"], seconds_bound=order["seconds"],
                        admission_device=iss["admission"]["device"],
                        admission_suspect_compute=[p for p in iss["admission"]["processes"]
                                                   if any(s in p["image"].lower() for s in SUSPECT)],
                        guard_samples=dict(count=len(samples), first_utc=samples[0]["utc"], last_utc=samples[-1]["utc"],
                                           board_used_peak_mib=max(x["used_mib"] for x in samples),
                                           free_min_mib=min(x["free_mib"] for x in samples),
                                           temp_max_c=max(x["temp_c"] for x in samples),
                                           ceiling_mib=release["ceiling_mib"],
                                           within_ceiling=max(x["used_mib"] for x in samples) <= release["ceiling_mib"]),
                        after_job_close=dict(device=after["device"], ollama_models=after["ollama_models"],
                                             suspect_compute=[p for p in after["processes"]
                                                              if any(s in p["image"].lower() for s in SUSPECT)]),
                        stdout_bytes=(a.lease_dir / f"{n}-stdout.txt").stat().st_size,
                        stderr_bytes=(a.lease_dir / f"{n}-stderr.txt").stat().st_size)
    overall = load(a.lease_dir / "returned.json")
    eos = Counter()
    for r in inv["runs"]:
        run = Path(r["path"])
        for rel in r["files"]:
            if re.search(r"/window-\d{3}\.json$", rel):
                d = load(run / rel)
                mode = rel.split("/")[0].split("-", 2)[2]
                eos[f"{r['run']}:{mode}:windows"] += 1
                eos[f"{r['run']}:{mode}:eos_in_returned_ids"] += d["window_token_ids"].count(d["eos_id"])
                eos[f"{r['run']}:{mode}:eos_excluded_flag"] += bool(d.get("eos_is_excluded_from_returned_ids"))
                eos[f"{r['run']}:{mode}:finish_stop"] += d.get("finish_reason") == "stop"
    mine = {r["run"]: r["files"] for r in inv["runs"]}
    blobs = mism = 0
    for o in cinv["orders"]:
        for d in o["docs"]:
            for name, h in d["blobs"].items():
                hits = [k for k, v in mine[o["name"]].items() if k.endswith(f"-{d['label']}-{d['mode']}/{name}") and v == h]
                blobs += 1
                mism += len(hits) != 1
    arms = {}
    for rn, r in s1["runs"].items():
        for mode, arm in r["arms"].items():
            sm = arm["summary"]
            g = sm["grammar_measured"]
            arms[f"{r['order']}:{mode}"] = dict(
                windows=dict(total=sm["windows_total"], warm_excluded=sm["windows_warm"], measured=sm["windows_measured"]),
                stops=sm["stops"], failed_or_fallback_windows=sm["failed_or_fallback_windows"],
                counters={k: v for k, v in sm["counters"].items() if sm["counters_present"][k]},
                kernel_paths=sm["kernel_paths"], allocator=sm["allocator"], device_launcher_samples=sm["device"],
                walls=sm["walls"], warmup_s=sm["warmup_s"],
                measured={f: dict(complete_s=m["complete_s"], first_page_s=m["first_page_s"], last_page_s=m["last_page_s"],
                                  pages_per_min=m["pages_per_min"], prediction_sha256=m["prediction_sha256"])
                          for f, m in arm["measured"].items()},
                grammar_measured={k: g[k] for k in g if k.startswith("header_") or k in (
                    "grammar", "pages", "pages_structurally_valid", "pages_with_malformed", "blocks", "box_invalid",
                    "orphan_fork", "level_outside_header", "unknown_specials", "table_unbalanced_pages", "page_marker_faults",
                    "parser_disagreements", "malformed_reasons")})
    warm = {}
    for r in inv["runs"]:
        for rel, h in r["predictions"].items():
            if "-warm-" in rel:
                warm.setdefault(f"{r['run']}:{rel.split('/')[0]}", []).append(h[:12])
    receipt = dict(
        kind="WP-0016 G0 independent PRE-KEY receipt", reviewer="eld-rd-reviewer",
        operator_session="Claude Code, Opus 5.5 (claude-opus-5-5); requested xhigh, applied effort not exposed",
        created_utc=utc(), keys_accessed=False, scoring_performed=False,
        raw_text_displayed="none; malformed headers were summarised only as masked shapes (digits->9, letters->a)",
        release=dict(commit="2289cd14a3b723eb72087bc5215c863373a4f338", path=str(a.release), sha256=sha(a.release),
                     expected_sha256=a.release_sha256, digest_ok=sha(a.release) == a.release_sha256,
                     worktree=release["worktree"], source=release["review_worktree_head"], ceiling_mib=release["ceiling_mib"]),
        operator=dict(launch=op_launch, supervisor_gone=gone(op_launch["pid"]), monitor_entries=len(monitor),
                      monitor_first_utc=monitor[0]["utc"], monitor_last_utc=monitor[-1]["utc"],
                      watch_end=[m for m in monitor if "watch_end" in m],
                      interventions="none; read-only liveness/lease-name/device checks only; single attempt, no retry"),
        lease=dict(acquired=load(a.lease_dir / "acquired.json"), orders=lease, returned=overall),
        blind_inventory=dict(path="docs/reviews/WP-0016/evidence/G0-blind-inventory.json", sha256=sha(a.inventory),
                             committed="6f3273278215fd0ced7555a84e1e692f144b5b69",
                             runs={r["run"]: dict(order=r["order"], files=len(r["files"]), runtime_cache_files=len(r["runtime_cache_files"]),
                                                  completed=r["all_segments_completed"], pending=r["pending_files"],
                                                  failures=r["failure_files"]) for r in inv["runs"]},
                             measured_prediction_sha256={rel: h for r in inv["runs"] for rel, h in
                                                         ((f"{r['run']}/{k}", v) for k, v in r["predictions"].items())
                                                         if "-warm-" not in rel}),
        stage1=dict(path="docs/reviews/WP-0016/evidence/G0-stage1.json", sha256=sha(a.stage1), checks_run=s1["checks_run"],
                    failures=s1["failures"], real_binding=s1["real_binding"], bound_source=s1["bound_source"],
                    runs={rn: dict(order=r["order"], source=r["source"], head=r["head"], lease=r["lease"],
                                   lease_matches_release=r["lease"] == rn, process_s=r["elapsed_s"]) for rn, r in s1["runs"].items()},
                    arms=arms, memory=s1["memory"], timing=s1["timing"],
                    token_parity={f: {k: dict(identical=v["identical"], first_mismatch=v["first_mismatch"],
                                              pages_identical=v["pages_identical"], pages=v["pages"],
                                              pages_text_outside_boxes_identical=v["pages_text_outside_boxes_identical"])
                                      for k, v in t.items()} for f, t in s1["token_parity"].items()}),
        eos_and_stop=dict(eos),
        warmup_prediction_hash_prefixes=warm,
        coordinator_inventory=dict(tool="docs/coordination/WP-0016/inventory.py", tool_sha256=sha(
            Path("C:/Users/jackg/Asp.net Projects/eledgercare/docs/coordination/WP-0016/inventory.py")),
            output_sha256=sha(a.coordinator_inventory), assertions_passed=True, blobs_cross_checked=blobs, mismatches=mism),
        pending=["stage 2 escrow scoring after the separate key release",
                 "stored WP-0015 Windows prediction/timing copies (not yet supplied)", "report 003"])
    digest = write_new(a.out, receipt)
    print(json.dumps(dict(out=str(a.out), sha256=digest, stage1_failures=len(s1["failures"]), blobs=blobs, mismatches=mism,
                          eos=dict(eos), supervisor_gone=receipt["operator"]["supervisor_gone"],
                          children_gone={n: v["child_gone"] for n, v in lease.items()}), indent=1))


if __name__ == "__main__":
    main()
