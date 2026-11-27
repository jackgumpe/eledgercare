"""Two ordinary inert Windows arms. Observations remain associated with their handles."""
import _winapi
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import hmac
import json
import msvcrt
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time

from scoring import encode, score, KEYS
import win_observer as win

HERE = Path(__file__).resolve().parent
ROOT = Path.home() / "eLedgerCare-Speed/WP-0044/eld-owner-probe"
VENV = ROOT / "runtime-v1"
LAUNCHER = VENV / "Scripts/python.exe"
WORKER = HERE / "worker.py"
ARGS = [str(LAUNCHER), "-I", "-B", str(WORKER), "emit"]
PAYLOAD = bytes.fromhex("46 30 37 0A")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=True, allow_nan=False)
        stream.write("\n")


def environment():
    if sys.version_info[:3] != (3, 12, 10) or win.ct.sizeof(win.HANDLE) != 8:
        raise RuntimeError("requires x64 CPython 3.12.10")
    return {"SystemRoot": os.environ["SystemRoot"], "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}


def prepare_manifest():
    env = environment()
    env["ELD44_MANIFEST"] = "1"
    snapshot = subprocess.run(ARGS, env=env, cwd=ROOT, stdin=subprocess.DEVNULL,
                              capture_output=True, timeout=20, check=True)
    return {"version": sys.version, "images": {"L.image": sha(LAUNCHER),
            "I.image": sha(Path(sys.executable))}, "fields": json.loads(snapshot.stdout)["fields"],
            "payload_hex": PAYLOAD.hex(), "members": ["result.bin"]}


def stamp(phase, method):
    return {"phase": phase, "source": method, "time_ns": time.monotonic_ns(),
            "clock": "supervisor.monotonic"}


def live_process(directory, sink, launch_guard, challenge):
    import ctypes as ct
    directory.mkdir()
    env = environment()
    env["ELD44_ARM"] = str(directory)
    denied = None
    events = []
    started = time.monotonic()
    with win.owned_job() as (job, limits), ExitStack() as handles:
        # Use a restricted handle list. The launcher and interpreter inherit the
        # same output. Neither the job, private HMAC key nor image guard is inherited.
        null_in = handles.enter_context(open(os.devnull, "rb"))
        null_err = handles.enter_context((directory / "stderr.bin").open("xb"))
        ins, err = [msvcrt.get_osfhandle(f.fileno()) for f in (null_in, null_err)]
        for h in [ins, err, sink]:
            os.set_handle_inheritable(h, True)
        startup = subprocess.STARTUPINFO(dwFlags=subprocess.STARTF_USESTDHANDLES,
                    hStdInput=ins, hStdError=err, hStdOutput=sink,
                    lpAttributeList={"handle_list": [ins, err, sink]})
        try:
            # DEBUG_PROCESS | CREATE_SUSPENDED | CREATE_NO_WINDOW. Observe creation
            # file handles; allow normal execution by acknowledging each event.
            process, thread, pid, tid = _winapi.CreateProcess(
                str(LAUNCHER), subprocess.list2cmdline(ARGS), None, None, True,
                0x08000005, env, str(directory), startup)
        finally:
            for h in [ins, err, sink]:
                os.set_handle_inheritable(h, False)
        handles.callback(win.close, process)
        handles.callback(win.close, thread)
        try:
            win.check(win.assign(job, process))
        except OSError:
            _winapi.TerminateProcess(process, 1)  # only our newly created suspended fixture
            raise
        anchor = win.process_key(process)
        if win.resume(thread) == 0xffffffff:
            raise ct.WinError(ct.get_last_error())
        created, break_seen, exited = {}, set(), {}
        worker = None
        while pid not in exited or len(exited) != len(created):
            if time.monotonic() - started > 27:
                raise TimeoutError("27-second fixture event budget")
            event = win.next_event()
            if event is not None:
                code, who = event.code, event.pid
                disposition = 0x00010002  # DBG_CONTINUE
                try:
                    if code == 3:  # CREATE_PROCESS_DEBUG_EVENT
                        paths = {os.path.normcase(str(p)) for p in (LAUNCHER, Path(sys.executable))}
                        image = win.sample_image(event, job, paths)
                        image["live_anchor"] = win.wait(process, 0) == 258
                        image["time_ns"] = time.monotonic_ns()
                        created[who] = image
                        if len(created) > 4:
                            raise ValueError("owned fixture process ceiling")
                        save(directory / f"creation-{len(created)}.json", {
                             "instance": image["instance"], "image": Path(image["reported_path"]).name,
                             "digest": image.get("sha256"), "job_member": image["job_member"]})
                        if challenge and who == pid:
                            # A read-only OPEN_EXISTING request with incompatible
                            # sharing on our own venv launcher. Never request mutation.
                            try:
                                other = win.open_file(LAUNCHER, win.READ, 0)
                            except OSError as exc:
                                result = exc.winerror
                            else:
                                win.close(other)
                                result = 0
                            denied = {"winerror": result, "guard_id": win.object_id(launch_guard),
                                      "live_image_id": image.get("file_id"), "time_ns": time.monotonic_ns(),
                                      "utc": datetime.now(timezone.utc).isoformat(),
                                      "operation": "CreateFileW(GENERIC_READ, share=0, OPEN_EXISTING)"}
                    elif code == 6 and event.data.words[0]:  # LOAD_DLL_DEBUG_EVENT
                        win.close(event.data.words[0])
                    elif code == 5:  # EXIT_PROCESS_DEBUG_EVENT
                        exited[who] = [event.data.dwords[0], time.monotonic_ns()]
                    elif code == 1:
                        exc = event.data.dwords[0]
                        if exc == 0x80000003 and who not in break_seen:
                            break_seen.add(who)  # loader's initial debugger notification
                        else:
                            disposition = 0x80010001  # DBG_EXCEPTION_NOT_HANDLED
                    events.append([code, who, time.monotonic_ns()])
                finally:
                    win.check(win.ack(who, event.tid, disposition))
            observed = directory / "worker.json"
            if worker is None and observed.is_file():
                worker = json.loads(observed.read_bytes())
                worker_cut = time.monotonic_ns()
                (directory / "release").touch(exist_ok=False)
        if not worker or any(r[0] != 0 for r in exited.values()):
            raise RuntimeError(f"fixture completion: {len(created)} creations; exits {exited}")
        launch, interp = created[pid], created[worker["pid"]]
        for data, expected in [(launch, LAUNCHER), (interp, Path(sys.executable))]:
            data["matches_image_path"] = Path(data.pop("reported_path")).resolve() == expected.resolve()
        observed = {**worker["fields"], "E.launcher": launch["instance"],
                    "E.instance": [launch["instance"], interp["instance"]],
                    "E.order": launch["instance"][1] <= interp["instance"][1] and interp["live_anchor"],
                    "E.job": launch["job_member"] and interp["job_member"] and not limits & 0x1800}
        for key, obj in [("L.image", launch), ("I.image", interp)]:
            if "sha256" in obj:
                observed[key] = obj["sha256"]
        # A later worker snapshot identifies the inherited-parent PID; the Windows
        # creation debug notification does not report which thread made the call.
        return {"observed": observed, "anchor": anchor, "worker": worker,
                "instances": [launch, interp], "exit_codes_and_times": exited,
                "job_flags": limits, "events": events, "denied": denied, "worker_cut": worker_cut,
                "writer_cut": time.monotonic_ns(), "duration_s": time.monotonic() - started}


def members(data):
    return [{"name": "result.bin", "length": len(data), "sha256": hashlib.sha256(data).hexdigest()}]


class Arm:
    def __init__(self, directory, manifest, secret, challenge):
        self.path = directory.parent / (directory.name + "-result.bin")
        self.handle = None
        self.continuous = False
        try:
            self.handle = win.open_file(self.path, win.READ | win.WRITE, win.SHARE_READ, 1)
            self.continuous = True
            self.initial_id = win.object_id(self.handle)
            self.filesystem = win.filesystem(self.handle)
            if self.filesystem != "NTFS":
                raise RuntimeError("NTFS per-member identity required")
            guard = win.open_file(LAUNCHER, win.READ, win.SHARE_READ)
            try:
                self.process = live_process(directory, self.handle, guard, challenge)
            finally:
                win.close(guard)
            identity, data = win.read_member(self.path)
            if (self.initial_id != identity or identity != win.object_id(self.handle)
                    or self.process["worker"]["stdout_id"] != identity):
                raise RuntimeError("original changed across capture")
            self.sealed = {"schema": 1, "run": secrets.token_hex(16),
                           "instance": self.process["instances"][1]["instance"],
                           "object": identity, "members": members(data)}
            self.tag = hmac.digest(secret, encode(self.sealed), "sha256")
            self.seal_time = time.monotonic_ns()
            self.manifest = manifest
            save(directory / "supervision.json", {"process": self.process, "sealed": self.sealed,
                 "tag": self.tag.hex(), "seal_ns": self.seal_time, "filesystem": self.filesystem,
                 "object_at_creation": self.initial_id})
        except BaseException:
            self.close()
            raise

    def close(self):
        if self.handle is not None:
            win.close(self.handle)
            self.handle = None
            self.continuous = False


def submission(selected, pair, path, reference, tag, secret, registry):
    # The process evidence and source receipt are independent of the supplied pathname.
    # For W2 the pair varies; for B2 only the submitted protected object varies.
    src = pair.process
    expected = {**pair.manifest["fields"], **pair.manifest["images"],
                "E.launcher": selected.process["anchor"], "E.parent": pair.process["anchor"],
                "E.instance": [src["anchor"], src["worker"]["self_instance"]], "E.job": True,
                "E.order": True, "B.writer": "exclusive-interpreter", "B.seal": True,
                "B.protection": True, "B.direct": True, "B.origin": selected.sealed["run"],
                "B.members": members(PAYLOAD), "content.bytes": PAYLOAD.hex()}
    obs = dict(src["observed"])
    sources = {}
    for key in KEYS:
        phase = KEYS[key]
        if key in ("L.image", "I.image"):
            sources[key] = stamp("image", "CREATE_PROCESS_DEBUG_EVENT image-file handle SHA-256")
            sources[key]["time_ns"] = src["instances"][key == "I.image"]["time_ns"]
        elif key.startswith("E."):
            sources[key] = stamp("edge", "creation handles, creation FILETIMEs, job query and launcher wait")
            sources[key]["time_ns"] = src["instances"][1]["time_ns"]
        elif key.startswith(("A.", "C.")):
            sources[key] = stamp(phase, "pinned worker module/config cut")
            sources[key]["time_ns"] = src["worker_cut"]
    sources["E.parent"]["source"] = "worker inherited-parent PID and creation event; actual caller unavailable"
    sources["B.writer"] = stamp("writer", "launcher, interpreter and supervisor shared writable endpoint; issuing writer unmeasured")
    sources["B.writer"]["time_ns"] = src["writer_cut"]
    identity, data = win.read_member(path)
    acq = time.monotonic_ns()
    verified = None if secret is None else hmac.compare_digest(tag, hmac.digest(secret, encode(reference), "sha256"))
    if verified is not None:
        obs["B.seal"] = verified
    sources["B.seal"] = stamp("seal", "HMAC-SHA256 verifier on reference receipt")
    identity_sources = []
    for arm in registry:
        if arm.continuous and arm.handle is not None and win.object_id(arm.handle) == arm.initial_id:
            if identity == arm.initial_id:
                identity_sources.append(arm)
    if len(identity_sources) > 1:
        raise RuntimeError("ambiguous live file identity")
    if selected.continuous and selected.handle is not None and win.object_id(selected.handle) == selected.initial_id:
        obs["B.protection"] = True
    if identity_sources:
        arm = identity_sources[0]
        if secret is not None and hmac.compare_digest(arm.tag, hmac.digest(secret, encode(arm.sealed), "sha256")):
            obs["B.origin"] = arm.sealed["run"]
        obs["B.direct"] = True
    # Compare a trusted sealed member commitment wherever one is available, and
    # report the content of the actual read independently of receipt availability.
    if verified is True:
        expected["B.members"] = reference["members"]
    obs["B.members"] = members(data)  # public manifest if no authenticated receipt
    obs["content.bytes"] = data.hex()
    for key, method in {"B.protection": "open guard at creation and scorer acquisition",
            "B.direct": "scorer handle joined to continuously held registered NTFS object",
            "B.origin": "authenticated protected-object registry joined by volume serial and file index",
            "B.members": "scorer read of sorted member name, length, SHA-256",
            "content.bytes": "scorer read of four original input bytes"}.items():
        sources[key] = stamp(KEYS[key], method)
        sources[key]["time_ns"] = acq
    record = {"expected": expected, "observed": obs, "sources": sources}
    return {"verdict": score(record), "evidence": {"submission_id": identity,
            "reference_id": reference["object"], "payload": data.hex(), "verified": verified,
            "protected_registry_match": bool(identity_sources), "direct_read_ns": acq},
            "record": record}


def run_live(directory, manifest, emit, smoke=False):
    secret = secrets.token_bytes(32)
    # Persist only in role-private scratch for receipt verification.
    with (directory / "hmac.key").open("xb") as keyfile:
        keyfile.write(secret)
    with ExitStack() as stack:
        a = Arm(directory / "first", manifest, secret, True)
        stack.callback(a.close)
        if smoke:
            result = submission(a, a, a.path, a.sealed, a.tag, secret, [a])
            emit("development-only", result)
            return
        b = Arm(directory / "second", manifest, secret, False)
        stack.callback(b.close)
        if a.initial_id == b.initial_id:
            raise RuntimeError("two independent files required")
        arms = [a, b]
        def submit(name, selected, pair, path, reference, tag, key):
            emit(name, submission(selected, pair, path, reference, tag, key, arms))
        submit("W1.A", a, a, a.path, a.sealed, a.tag, secret)
        submit("W1.B", b, b, b.path, b.sealed, b.tag, secret)
        submit("W2.other", a, b, a.path, a.sealed, a.tag, secret)
        denied = a.process["denied"]
        if denied and denied["winerror"] == 32 and denied["guard_id"] == denied["live_image_id"]:
            submit("W4.denied", a, a, a.path, a.sealed, a.tag, secret)
        else:
            emit("W4.denied", {"error": "owned image sharing-violation observation unavailable", "denied": denied})
        submit("B1.original", a, a, a.path, a.sealed, a.tag, secret)
        submit("B2.other", a, a, b.path, a.sealed, a.tag, secret)
        copy = directory / "detached.bin"
        with copy.open("xb") as output:
            output.write(win.read_member(a.path)[1])
        submit("B3.copy", a, a, copy, a.sealed, a.tag, secret)
        invalid = bytes([a.tag[0] ^ 1]) + a.tag[1:]
        submit("B4.invalid", a, a, copy, a.sealed, invalid, secret)
        submit("B4.unavailable", a, a, copy, a.sealed, a.tag, None)
        a.close()
        submit("B5.reopen", a, a, a.path, a.sealed, a.tag, secret)
