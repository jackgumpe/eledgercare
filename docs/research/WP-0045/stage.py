"""Cooperative inert worker and selected direct supervisor, separate ordinary processes."""
from contextlib import ExitStack
import hashlib
import hmac
import os
from pathlib import Path
import secrets
import sys
import traceback

sys.path.insert(0, str(Path(__file__).resolve().parent))
import state as s
import win

def worker(arm, observation, token):
    start = win.clock()
    writer = win.file(arm / "members" / s.ORIGINAL, win.READ | win.WRITE, win.SHARE_R, 1)
    created = win.clock()
    try:
        identity = win.identity(writer)
        length = win.D()
        bytes_out = bytes.fromhex(s.read(arm / "request.json")["payload_hex"])
        if len(bytes_out) != 4:
            raise ValueError("worker four-byte bound")
        win.checked(win.write(writer, bytes_out, 4, win.ct.byref(length), None))
        win.checked(win.flush(writer))
        written = win.clock()
        if length.value != 4:
            raise IOError("short original write")
        view = win.read_view(win.SELF, writer)
        duplicated = win.clock()
    finally:
        win.checked(win.close(writer))
    closed = win.clock()
    try:
        s.publish(arm / "worker.json", {
            "instance": win.current(), "token": token, "snapshot": observation,
            "writer": writer, "view": view, "created_object": identity, "view_object": win.identity(view),
            "start": start, "created": created, "written": written, "duplicated": duplicated,
            "closed": closed, "requested_access": win.READ | win.WRITE, "share": win.SHARE_R,
            "disposition": 1, "duplicated_access": win.READ, "inherit": False,
            "writes": [{"object": identity, "size": length.value, "bytes": bytes_out.hex()}]})
        s.wait_for(arm / "supervisor-held.json")
    finally:
        win.checked(win.close(view))

def supervise(arm, selection, snapshot, token):
    trace, transfer = {}, {}
    with ExitStack() as guard:
        def on_event(process_handle, events):
            if transfer or not (arm / "worker.json").is_file():
                return
            child = s.read(arm / "worker.json")
            if (child["instance"] != win.process(process_handle) or
                    child["instance"] != events["image"]["event_instance"]):
                raise ValueError("worker read-view transfer lacks instance join")
            # Pull only FILE_GENERIC_READ from the handle offered by this child.
            view = win.read_view(process_handle, child["view"])
            guard.callback(win.close, view)
            transfer.update(view=view, object=win.identity(view), at=win.clock(),
                            from_instance=win.process(process_handle), desired=win.READ)
            s.publish(arm / "supervisor-held.json", transfer)
        try:
            win.launch(s.argv("worker", selection), arm, s.env(), on_event, trace)
        finally:
            s.save(arm / "child-call.json", trace)
        if not transfer:
            raise RuntimeError("missing child handoff")
        acquired = win.fresh_read(arm / "members" / s.ORIGINAL)
        receipt = {"schema": 1, "selection": selection, "nonce": secrets.token_hex(16),
                   "supervisor": win.current(), "child": trace["returned_instance"],
                   "object": acquired["object"], "members": [{
                       "name": s.ORIGINAL, "size": len(bytes.fromhex(acquired["bytes"])),
                       "sha256": hashlib.sha256(bytes.fromhex(acquired["bytes"])).hexdigest()}]}
        secret = secrets.token_bytes(32)
        with (arm / "key.bin").open("xb") as out:
            out.write(secret)
        mac = hmac.digest(secret, s.encode(receipt), "sha256").hex()
        handoff = {"view": transfer["view"], "view_object": win.identity(transfer["view"]),
                   "instance": win.current(), "token": token, "snapshot": snapshot,
                   "acquired": acquired, "receipt": receipt, "mac": mac, "signed": win.clock()}
        s.publish(arm / "supervisor.json", handoff)
        s.wait_for(arm / "scorer-held.json")

def main():
    token = win.ordinary()
    role, selection = sys.argv[1:]
    arm = Path.cwd()
    snapshot = s.snapshot(arm)
    if role not in ("supervisor", "worker") or selection not in ("0", "1"):
        raise ValueError("invalid role or slot")
    # The separately owned calibration directory contains this file. The
    # decisive wrapper uses new arm directories and asserts the exact inventory.
    if (arm / "calibration.only").is_file():
        s.save(arm / f"{role}-{selection}.json", snapshot)
        return
    if role == "worker":
        worker(arm, snapshot, token)
    else:
        supervise(arm, int(selection), snapshot, token)

if __name__ == "__main__":
    try:
        main()
    except BaseException:
        s.save(Path.cwd() / ("error-" + sys.argv[1] + ".json"), {"error": traceback.format_exc()})
        raise
