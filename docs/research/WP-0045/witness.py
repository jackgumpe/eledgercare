"""Public, reproducible projection of the private native-handle ledger."""
import hashlib
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import state as s

def witness(arm):
    outer, child, sp, wk, mid, scorer, final, hashes = [s.read(arm / f) for f in
        ("supervisor-call.json","child-call.json","supervisor.json","worker.json","supervisor-held.json",
         "scorer.json","scorer-held.json","raw-commitments.json")]
    for name, sha in hashes.items():
        if s.sha(arm / name) != sha:
            raise ValueError("raw file altered")
    t0 = outer["call"]
    def digest(x):
        return hashlib.sha256(s.encode(x)).hexdigest()
    def call(c):
        im = c["image"]
        return {"caller_instance":digest(c["caller"]), "caller_after":digest(c["caller_after"]),
                "caller_thread_stable": c["caller_tid"] == c["caller_tid_after"],
                "returned_instance":digest(c["returned_instance"]), "event_instance":digest(im["event_instance"]),
                "event_tid_matches_return":im["event_tid"]==c["child_tid"],
                "returned_event_process_compared_equal":im["returned_same_object"],
                "image_file_identity":digest(im["object"]), "image_file_sha256":im["sha256"],
                "image_path_matches_absolute_application": Path(im["image_path"]) == Path(c["application"]),
                "job_policy":c["policy"], "job_member":im["member"],"inherit_handles":c["inherit_handles"],
                "job_total_processes":c["job_total_processes"], "creation_flags":c["flags"], "event_count":len(c["events"]), "exit":c["exit"][0],
                "qpc_delta_ns":{k:c[k]-t0 for k in ("call","returned","assigned","resumed","creation_continue")}
                               | {"create_event":im["at"]-t0,"exit":c["exit"][1]-t0}}
    return {"source_index_sha256":s.sha(arm / "raw-commitments.json"),
            "direct_request":s.read(arm / "request.json"),
            "clock":"perf_counter_ns, common Windows QPC; origin outer call",
            "outer_to_supervisor":call(outer),"supervisor_to_worker":call(child),
            "self_instance":{"supervisor":digest(sp["instance"]), "worker":digest(wk["instance"])},
            "tokens":{"recorder":scorer["outer_token"],"supervisor":sp["token"],"worker":wk["token"]},
            "image_guard_object":digest(scorer["initial_image_object"]),
            "guarded_sources":scorer["script_hashes"],
            "snapshots":{role:{key:digest(msg["snapshot"][key]) for key in ("command","runtime")}
                         for role,msg in [("supervisor",sp),("worker",wk)]},
            "writer":{"access":wk["requested_access"],"share":wk["share"],"disposition":wk["disposition"],
                      "read_view_access":[wk["duplicated_access"],mid["desired"],final["desired"]],
                      "inheritable":wk["inherit"],"write_count":len(wk["writes"]),
                      "bytes_written":[w["size"] for w in wk["writes"]]},
            "member_identities":{k:digest(v) for k,v in {"writer":wk["created_object"],
                "worker_read_view":wk["view_object"],"supervisor_duplicated_view":mid["object"],
                "supervisor_at_signing":sp["view_object"], "receipt":sp["receipt"]["object"],
                "scorer_duplicate":final["object"],"scorer_end_guard":scorer["guard_id"],
                "scorer_fresh_open":scorer["direct"]["object"]}.items()},
            "times_ns":{k:v-t0 for k,v in {"supervisor_command_start":sp["snapshot"]["command_start"],
                "supervisor_runtime_cut":sp["snapshot"]["cut"], "worker_command_start":wk["snapshot"]["command_start"],
                "worker_runtime_cut":wk["snapshot"]["cut"],"worker_open":wk["created"],
                "write_flushed":wk["written"],"worker_read_view":wk["duplicated"],"writer_closed":wk["closed"],
                "supervisor_read_view":mid["at"],"sealed":sp["signed"],"scorer_read_view":final["at"],
                "verified":scorer["verified"],"fresh_scorer_read":scorer["direct"]["at"]}.items()},
            "seal_algorithm":"HMAC-SHA256", "verified":scorer["authentic"],"receipt_sha256":digest(sp["receipt"]),
            "receipt_selection":sp["receipt"]["selection"],"receipt_supervisor":digest(sp["receipt"]["supervisor"]),
            "receipt_worker":digest(sp["receipt"]["child"]), "members":scorer["members"],
            "filesystem":scorer["direct"]["filesystem"],"eof":scorer["direct"]["eof"],
            "bytes_hex":scorer["direct"]["bytes"]}

if __name__ == "__main__":
    dest, output = map(Path,sys.argv[1:])
    s.save(output,{str(i):witness(dest / f"arm-{i}") for i in (0,1)})
