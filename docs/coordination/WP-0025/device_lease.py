"""Use the existing exclusive Windows job guard for the two WP-0025 orders."""
import argparse
import importlib.util
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("shared_gpu_guard", HERE.parent / "WP-0016/device_lease.py")
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
guard.PACKET = guard.HOST / "WP-0025"
original_bind = guard.bind_inputs
desktop_binding = HERE.parents[1] / "reviews/WP-0024/admission-watch-binding.json"


def bind_and_observe(lease, order):
    """Check actual GPU clients under the shared lock before each supervised order."""
    original_bind(lease, order)
    if guard.sha(desktop_binding) != "ad311561b81f7d3f86938861726385fa5f7ddd0ffff826d6a205552697b7ab6d":
        raise ValueError("Historical desktop application binding changed")
    known = set(json.loads(desktop_binding.read_bytes())["observed_desktop_images"])
    state = guard.ownership()
    other = [p for p in state["processes"] if p["image"].casefold() not in known]
    folder = guard.PACKET / "coordination/leases" / lease["name"]
    guard.dump(folder / (order["run"] + "-desktop-admission.json"),
               {"observed": state, "unrecognized_gpu_clients": other, "utc": guard.utc()})
    if other:
        raise RuntimeError(f"Unreconciled GPU ownership before {order['run']}: {other}")


guard.bind_inputs = bind_and_observe


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release", type=Path)
    parser.add_argument("sha256")
    args = parser.parse_args()
    guard.run_release(args.release, args.sha256)
