"""CPU-only H0 evidence reader. It has no device release operation or subsequent-phase entry point."""
from datetime import datetime, timezone
import hashlib
import json
import msvcrt
import os
from pathlib import Path
import subprocess
import sys
import time


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stamp():
    return datetime.now(timezone.utc).isoformat()


def write(path,value):
    pending=path.with_name(path.name+".pending")
    with pending.open("w",encoding="utf8",newline="\n") as f:
        f.write(json.dumps(value,sort_keys=True,indent=2)+"\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(pending,path)


def read(path):
    return json.loads(path.read_bytes())


def result(folder,phase,**fields):
    write(folder/"status.json",{"phase":phase,"utc":stamp(),"pid":os.getpid(),**fields})


def wait_for_return(binding):
    watch=Path(binding["watch_status"])
    returned=Path(binding["lease_dir"])/"returned.json"
    while True:
        state={}
        if watch.is_file():
            state=read(watch)
            if state.get("binding_sha256")==binding["watch_sha256"] and state["status"]=="watch_error":
                return state
        if returned.is_file():
            assert read(returned)["release_sha256"]==binding["guard_release_sha256"]
            return state|{"physical_guard_return_seen":True}
        time.sleep(45)


def inspect(binding,folder):
    result(folder,"awaiting_return",admission_watch=binding["watch_status"])
    state=wait_for_return(binding)
    lease=Path(binding["lease_dir"])
    runtime=Path(binding["run_dir"])/"sensor"
    receipts={}
    for name in ("acquired.json","h0-r1-issued.json","h0-r1-returned.json","returned.json"):
        path=lease/name
        if path.exists():
            receipts[name]=dict(sha256=digest(path),receipt=read(path))
    proc=runtime.parent/"process.json"
    complete=(state.get("physical_guard_return_seen") is True and receipts.get("h0-r1-returned.json",{}).get("receipt",{}).get("exit")==0
              and receipts.get("returned.json",{}).get("receipt",{}).get("error","missing") is None
              and proc.is_file() and read(proc).get("all_segments_completed") is True and (runtime/"outcome.json").is_file())
    write(folder/"return.json",dict(utc=stamp(),watch=state,guard=receipts,completed=complete,
                                    emitted_sample_directories=sorted(p.parent.name for p in runtime.glob("*/native.json"))))
    if not complete:
        result(folder,"incomplete_guard_or_runtime",return_sha256=digest(folder/"return.json"))
        return
    result(folder,"auditing_returned_h0",return_sha256=digest(folder/"return.json"))
    for name,pin in binding["audit_files"].items():
        if digest(folder/name)!=pin:
            raise ValueError("Source mismatch: "+name)
    summary=folder/"h0-independent-audit.json"
    with summary.open("xb") as out,(folder/"h0-independent-audit.stderr").open("xb") as err:
        entry=binding.get("audit_entrypoint","h0_audit.py")
        assert entry in binding["audit_files"]
        process=subprocess.run([sys.executable,"-I","-B",str(folder/entry)],stdin=subprocess.DEVNULL,
                               stdout=out,stderr=err,cwd=binding["review_worktree"],creationflags=subprocess.CREATE_NO_WINDOW)
    details={"exit":process.returncode,"result_sha256":digest(summary),"return_sha256":digest(folder/"return.json")}
    if process.returncode==0:
        evidence=read(summary)
        if "alignments" in evidence:
            details.update(comparisons=len(evidence["comparisons"]),source_witnesses=len(evidence["alignments"]),
                           unique_literal_and_geometry=evidence["source_witness_uniques"],
                           exact_token_mismatches=evidence["token_unequal_comparisons"],gate=evidence["gate"])
        else:
            details.update(comparisons=len(evidence["comparisons"]),source_witnesses=len(evidence["alignment"]),
                           unique_literal_and_geometry=evidence["uniquely_aligned_count"])
    result(folder,"ready_for_independent_disposition" if process.returncode==0 else "audit_requires_review",**details)


def main():
    path=Path(sys.argv[1])
    assert sys.flags.isolated and sys.dont_write_bytecode and digest(path)==sys.argv[2]
    binding=read(path)
    folder=path.parent.resolve()
    assert folder==Path(binding["audit_folder"]).resolve()
    assert digest(Path(__file__))==binding["reader_sha256"]
    os.environ["CUDA_VISIBLE_DEVICES"]="-1"
    with (folder/"reader.lock").open("a+b") as lock:
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        except OSError:
            return
        try:
            if (folder/"return.json").exists():
                return
            inspect(binding,folder)
        except Exception as exc:
            result(folder,"reader_failed",error=repr(exc))
            raise
        finally:
            lock.seek(0)
            msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)


if __name__=="__main__":
    main()

