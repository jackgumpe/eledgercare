"""Check the genuine direct-creation and protected-original joins in both frozen public returns."""
import hashlib
import json
import subprocess
from collections import Counter

AUTHOR = "2514ca6c7d31f417b0617ec230037c688c610e52:docs/research/WP-0045/"
REVIEW = "5f1ce93dc933a52fe8dd5d6c8668b9aa34a374e6:docs/reviews/WP-0045/blind/"
IMAGE = "4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a"
PAYLOAD = bytes.fromhex("4630370a")


def get(ref):
    return json.loads(subprocess.check_output(["git","show",ref]))


def medium(token):
    return token["integrity_rid"] == 8192 and not token["elevated"] and not token["effective_admin"]


def analyze():
    original = get(AUTHOR + "witnesses.json")
    found = {}
    for i in range(2):
        a = original[str(i)]
        outer = a["outer_to_supervisor"]
        inner = a["supervisor_to_worker"]
        identities = a["self_instance"]
        assert all(medium(t) for t in a["tokens"].values()) and len(a["tokens"]) == 3
        for created in (outer,inner):
            assert created["caller_instance"] == created["caller_after"] and created["caller_thread_stable"]
            assert created["returned_event_process_compared_equal"] and created["event_tid_matches_return"]
            assert created["event_instance"] == created["returned_instance"] and created["exit"] == 0
            assert created["image_file_sha256"] == IMAGE and created["job_member"] and not created["inherit_handles"]
        assert outer["event_instance"] == inner["caller_instance"] == identities["supervisor"] == a["receipt_supervisor"]
        assert inner["event_instance"] == identities["worker"] == a["receipt_worker"]
        assert a["writer"]["inheritable"] is False and a["writer"]["write_count"] == 1 and a["writer"]["bytes_written"] == [4]
        assert set(a["writer"]["read_view_access"]) == {0x80000000}
        object_ids = set(a["member_identities"].values())
        assert len(object_ids) == 1 and a["verified"] and a["receipt_selection"] == i
        assert a["filesystem"] == "NTFS" and bytes.fromhex(a["bytes_hex"]) == PAYLOAD and a["members"][0]["sha256"] == hashlib.sha256(PAYLOAD).hexdigest()
        times = a["times_ns"]
        assert times["worker_open"] <= times["write_flushed"] <= times["writer_closed"] <= times["sealed"] <= times["fresh_scorer_read"]
        r = get(REVIEW+f"native-{i}.json")
        obs, sup, work = [r[k] for k in ("observer","supervisor","worker")]
        assert all(medium(x["token"]) for x in (obs,sup,work))
        creators = [e for e in obs["events"] if e["kind"] == "create"]
        ec = next(e for e in creators if e["instance"] == sup["caller"])
        child = next(e for e in creators if e["instance"] == sup["child"])
        assert all(e["job"] and e["image"]["sha256"] == IMAGE for e in [ec,child])
        assert ec["instance"] == obs["anchor"] and child["instance"] == work["instance"]
        assert sup["tid"] == child["tid"] and sup["caller_thread"] == ec["tid"]
        assert not sup["inherited"] and sup["before"] <= sup["returned"] <= sup["resumed"] <= work["start"]
        assert work["write"] <= work["transfer"] <= work["closed"] <= sup["signed_at"] <= sup["acquired_at"]
        assert sup["authenticated"] and sup["score"] == PAYLOAD.hex() and work["ntfs"] == "NTFS" and work["length"] == 4
        assert work["member"] == sup["object_at_seal"] == sup["scored_object"] == sup["held_after"]
        found[i] = {"author_original_binding": next(iter(object_ids)), "reviewer_original_binding":work["member"],
                    "author_worker_instance": inner["event_instance"], "reviewer_worker_instance":child["instance"]}
    for k in found[0]:
        assert found[0][k] != found[1][k]
    comp = get(AUTHOR+"venv-observed.json")["arms"]
    hist = {k:dict(Counter(row["finding"] for row in arm.values())) for k,arm in comp.items()}
    rev_hist = {str(i):{arm:dict(Counter(row["comparison"] for row in rows.values()))
                        for arm,rows in get(REVIEW+f"prior-{i}.json").items()} for i in range(2)}
    return {"observed_images_sha256": IMAGE, "payload_sha256":hashlib.sha256(PAYLOAD).hexdigest(),
            "per_arm":found, "genuine_distinct_members_each_route":True, "native_role_tokens_checked":12,
            "integrity_rid":8192, "elevated":False, "effective_admin":False,
            "venv_field_coverage_author":hist, "venv_field_coverage_reviewer":rev_hist,
            "scope":"Both independent new topologies on the ordinary current user and trusted cooperative implementation. Historical redirector creator and adversarial same-user writer exclusivity remain unmeasured."}


if __name__ == "__main__":
    print(json.dumps(analyze(),indent=2))
