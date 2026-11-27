"""Outer recorder and scorer. Original object protection overlaps both process handoffs."""
from contextlib import ExitStack
import hashlib
import hmac
from pathlib import Path

import score
import state as s
import win

def image_record(call):
    img = call["image"]
    return [img.get("sha256"), Path(img["image_path"]) == win.BASE, img.get("object"),
            img["returned_same_object"]]

def call_order(c):
    return (c["call"] <= c["returned"] <= c["assigned"] <= c["resumed"] <= c["image"]["at"]
            <= c["creation_continue"] <= c["exit"][1])

def role_profile(message):
    return {k: message["snapshot"][k] for k in ("command", "runtime")}

def relation(arm, m, request, outer, outer_transfer, initial, guard_id, script_hash, raw_read,
             authentic, inventory, token):
    sp, wk = s.read(arm / "supervisor.json"), s.read(arm / "worker.json")
    call = s.read(arm / "child-call.json")
    mid = s.read(arm / "supervisor-held.json")
    idx = request["selection"]
    selected = outer["returned_instance"]
    reference = sp["receipt"]
    expected_roles = [m["roles"][f"{role}{idx}"] for role in ("supervisor", "worker")]
    profiles = [role_profile(sp), role_profile(wk)]
    ordered = (call_order(outer) and call_order(call)
               and outer["creation_continue"] <= sp["snapshot"]["cut"] <= call["call"]
               and call["creation_continue"] <= wk["snapshot"]["command_start"] <= wk["snapshot"]["cut"])
    ordinary = {"integrity_rid": 8192, "elevated": 0, "effective_admin": False}
    expected = {"L.image": [m["base"], True, initial, True, m["source"]["stage.py"]],
                "I.image": [m["base"], True, initial, True],
                "E.caller": [selected, selected, True, True],
                "E.child": [call["returned_instance"]] * 3 + [True, True],
                "E.order": True, "E.job": [0x2000, 0x2000, True, True],
                "A.command": [[p["command"] for p in expected_roles], True, True, True],
                "C.runtime": [[p["runtime"] for p in expected_roles], [ordinary] * 3],
                "B.writer": [True, True, True, True, True, True, True, [call["returned_instance"]]],
                "B.seal": True, "B.protection": [True, True, True, True],
                "B.direct": [True, "NTFS", True],
                "B.origin": [idx, selected, call["returned_instance"], wk["created_object"]],
                "B.members": [{"name": s.ORIGINAL, "size": 4,
                               "sha256": hashlib.sha256(bytes.fromhex(request["payload_hex"])).hexdigest()}],
                "content.bytes": request["payload_hex"]}
    measured = {"L.image": image_record(outer) + [script_hash], "I.image": image_record(call),
                "E.caller": [call["caller"], sp["instance"], call["caller"] == call["caller_after"],
                             call["caller_tid"] == call["caller_tid_after"]],
                "E.child": [call["image"]["event_instance"], wk["instance"], mid["from_instance"],
                            call["child_tid"] == call["image"]["event_tid"], call["image"]["returned_same_object"]],
                "E.order": ordered,
                "E.job": [outer["policy"], call["policy"], outer["image"]["member"], call["image"]["member"]],
                "A.command": [[p["command"] for p in profiles],
                              outer["argv"] == s.argv("supervisor",idx) and call["argv"] == s.argv("worker",idx),
                              all(Path(p) == arm for p in (outer["cwd"], call["cwd"],
                                  sp["snapshot"]["raw_paths"]["cwd"], wk["snapshot"]["raw_paths"]["cwd"])),
                              call["environment"] == outer["environment"] == s.env()],
                "C.runtime": [[p["runtime"] for p in profiles], [token, sp["token"], wk["token"]]],
                "B.writer": [not call["inherit_handles"] and not outer["inherit_handles"],
                             wk["requested_access"] == win.READ | win.WRITE,
                             wk["share"] == win.SHARE_R and wk["disposition"] == 1,
                             wk["inherit"] is False and wk["duplicated_access"] == mid["desired"] == win.READ,
                             wk["writes"] == [{"object": wk["created_object"], "size": 4,
                                                "bytes": request["payload_hex"]}],
                             wk["closed"] < mid["at"] < sp["signed"],
                             wk["created_object"] == mid["object"] == raw_read["object"],
                             [wk["instance"]]],
                "B.seal": authentic, "B.protection": [
                    wk["duplicated"] < wk["closed"] <= mid["at"] < call["exit"][1],
                    mid["at"] < sp["signed"] <= outer_transfer["at"] < outer["exit"][1],
                    wk["created_object"] == wk["view_object"] == mid["object"] == sp["view_object"] == guard_id,
                    guard_id == outer_transfer["object"] == raw_read["object"]],
                "B.direct": [guard_id == raw_read["object"], raw_read["filesystem"], raw_read["eof"]],
                "B.members": inventory, "content.bytes": raw_read["bytes"]}
    if authentic and reference["object"] == guard_id == raw_read["object"]:
        measured["B.origin"] = [reference[k] for k in ("selection","supervisor","child","object")]
    if not authentic or reference["members"] != inventory:
        measured.pop("B.origin", None)
    for key, c in [("L.image", outer), ("I.image", call)]:
        if not c["image"].get("sha256"):
            measured.pop(key)
    return {"expected": expected, "observed": measured, "evidence": score.ATOMS}

def collect(arm, request, manifest):
    token = win.ordinary()
    idx = request["selection"]
    if type(idx) is not int or idx not in (0, 1) or len(bytes.fromhex(request["payload_hex"])) != 4:
        raise ValueError("invalid bounded fixture")
    arm.mkdir()
    (arm / "members").mkdir()
    s.save(arm / "request.json", request)
    outer, transfer, scorer = {}, {}, {}
    with ExitStack() as held:
        exe = win.file(win.BASE, win.READ, win.SHARE_R)
        held.callback(win.close, exe)
        initial = win.identity(exe)
        guards = {}
        for name, wanted in manifest["source"].items():
            path = s.HERE / name
            h = win.file(path, win.READ, win.SHARE_R)
            held.callback(win.close, h)
            with win.as_stream(win.read_view(win.SELF,h)) as stream:
                guards[name] = hashlib.file_digest(stream, "sha256").hexdigest()
            if guards[name] != wanted:
                raise ValueError(f"source digest differs: {name}")
        def receive(process_handle, events):
            if transfer or not (arm / "supervisor.json").is_file():
                return
            packet = s.read(arm / "supervisor.json")
            if packet["instance"] != win.process(process_handle) or packet["instance"] != events["image"]["event_instance"]:
                raise ValueError("unjoined supervisor read-view transfer")
            view = win.read_view(process_handle, packet["view"])
            held.callback(win.close, view)
            transfer.update(view=view, object=win.identity(view), at=win.clock(), desired=win.READ)
            mac = hmac.digest((arm / "key.bin").read_bytes(), s.encode(packet["receipt"]), "sha256")
            authentic = hmac.compare_digest(mac, bytes.fromhex(packet["mac"]))
            verified = win.clock()
            direct = win.fresh_read(arm / "members" / s.ORIGINAL)
            acquired = bytes.fromhex(direct["bytes"])
            members = [{"name": f.name, "size": len(acquired), "sha256": hashlib.sha256(acquired).hexdigest()}
                       if f.name == s.ORIGINAL else {"name": f.name, "unexpected_entry": True}
                       for f in sorted((arm / "members").iterdir())]
            scorer.update(direct=direct, members=members, authentic=authentic,
                          guard_id=win.identity(view), verified=verified)
            s.publish(arm / "scorer-held.json", transfer)
        try:
            win.launch(s.argv("supervisor", idx), arm, s.env(), receive, outer)
        finally:
            s.save(arm / "supervisor-call.json", outer)
        s.save(arm / "scorer.json", {"initial_image_object":initial, "script_hashes":guards, "outer_token":token, **scorer})
        # Commit the raw observation bundle before the normal predicate reads it.
        s.save(arm / "raw-commitments.json", {f.relative_to(arm).as_posix(): s.sha(f)
               for f in sorted(arm.rglob("*")) if f.is_file()})
        rel = relation(arm, manifest, request, outer, transfer, initial, scorer["guard_id"],
                       guards["stage.py"], scorer["direct"], scorer["authentic"], scorer["members"], token)
        s.save(arm / "relation.json", rel)
        return score.project(rel)
