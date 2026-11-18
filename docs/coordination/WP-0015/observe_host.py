"""Capture local capacity and process ownership before issuing or returning a WP-0015 lease."""
import csv
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

GPU = "GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d"
PACKET_ROOT = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0015")
BRIEFS = {
    "Baidu OCR Optimization.pdf": "6c7f5199fb971eff0953f24c6a00b1af8f7c44c407df9c08c4363938c2d6567b",
    "eLedgerCare-OCR-Architecture-Review.md": "a6442154f4c65fa0994b7d9b9229cc4d5e1169336dff39f5e17da44f18533099",
    "eLedgerCare-Next-Lane-OCR-Speed-Trial.md": "5b46d5317c0e8579ea5015d357a38ea4f73cae622f235a92dd3173a4e27c83eb",
}


def output(*args):
    return subprocess.check_output(args, text=True, timeout=15).strip()


def snapshot():
    device = next(csv.reader([output("nvidia-smi", "--id=" + GPU,
        "--query-gpu=uuid,driver_version,memory.total,memory.used,memory.free,utilization.gpu",
        "--format=csv,noheader,nounits")], skipinitialspace=True))
    app_rows = csv.reader(output("nvidia-smi", "--id=" + GPU, "--query-compute-apps=pid,process_name",
                                 "--format=csv,noheader,nounits").splitlines(), skipinitialspace=True)
    apps = [{"pid": int(pid), "image": Path(image).name} for pid, image in app_rows if pid.isdigit()]
    installed = {name: hashlib.sha256((PACKET_ROOT / "briefs" / name).read_bytes()).hexdigest()
                 for name in BRIEFS}
    if installed != BRIEFS or device[0] != GPU:
        raise ValueError("Input or GPU identity mismatch")
    ollama = output("ollama", "ps").splitlines()
    return {
        "observed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "gpu_uuid": device[0], "driver": device[1], "total_mib": int(device[2]),
        "used_mib": int(device[3]), "free_mib": int(device[4]), "utilization_percent": int(device[5]),
        "wddm_processes": apps, "ollama_loaded_model_count": max(0, len(ollama) - 1),
        "volume_free_bytes": shutil.disk_usage(PACKET_ROOT).free,
        "originals_sha256": installed,
        "limits": "A point sample. The coordinator inspects ownership, other active leases and the candidate separately.",
    }


if __name__ == "__main__":
    print(json.dumps(snapshot(), indent=2))
