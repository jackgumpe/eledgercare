"""Run one signed WP-0017 lease using the original global GPU lock and Windows process guard."""
import argparse
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / "WP-0016" / "device_lease.py"
spec = importlib.util.spec_from_file_location("wp0016_device_lease", OLD)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
guard.PACKET = guard.HOST / "WP-0017"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release", type=Path)
    parser.add_argument("sha256")
    args = parser.parse_args()
    guard.run_release(args.release, args.sha256)
