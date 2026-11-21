"""Check recorded Windows PIDs after the guard exits and re-inventory Q0 bytes and namespace."""
from datetime import datetime, timezone
from pathlib import Path
import sys

import psutil

sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit_common import HOST, ROOT, cpu, pinned, read, save

def check(path,pin):
    from q0_receipt import inspect
    rel = pinned(path,pin)
    lease = HOST/"coordination/leases"/rel["name"]
    operator = HOST/"review/operator"/rel["name"]
    observed = read(operator/"return.json")
    pids = {read(lease/"acquired.json")["pid"],read(lease/"returned.json")["retiring_pid"],
            read(operator/"issued.json")["pid"], read(operator/"started.json")["pid"],observed["pid"]}
    for o in rel["orders"]:
        d = Path(o["output"])
        for file,keys in ((lease/(o["run"]+"-issued.json"),["pid"]),
                          (d/"worker-issued.json",["launcher_pid","supervisor_pid","supervisor_parent_pid"]),
                          (d/"sensor/binding.json",["pid","parent_pid"])):
            if file.exists():
                raw = read(file)
                pids.update(raw[k] for k in keys)
    status = {}
    for pid in sorted(pids):
        try:
            p = psutil.Process(pid)
            creation = datetime.fromtimestamp(p.create_time(),tz=timezone.utc)
            status[pid] = {"created":creation.isoformat(),"name":p.name(),
                           "reused_after_return":creation > datetime.fromisoformat(observed["utc"])}
            assert status[pid]["reused_after_return"], (pid,status[pid])
        except psutil.NoSuchProcess:
            status[pid] = "absent"
    record = inspect(Path("C:/Users/jackg/eLedgerCare-Q0/WP-0005"))
    assert record == read(path.parent/"q0-before.json")
    return {"release_sha256":pin,"observed_utc":datetime.now(timezone.utc).isoformat(),"referenced_pids":status,
            "q0_after":record,"q0_matches_before":True}

if __name__ == "__main__":
    cpu()
    sys.path.insert(0,str(ROOT/"docs/coordination/WP-0024"))
    save(Path(sys.argv[3]),check(Path(sys.argv[1]),sys.argv[2]))
