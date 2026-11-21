"""Use the already qualified shared board lock, desktop admission and Windows job."""
import argparse
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = spec_from_file_location("bounded_order_guard", HERE.parent / "WP-0025/device_lease.py")
previous = module_from_spec(spec)
spec.loader.exec_module(previous)
guard = previous.guard
guard.PACKET = guard.HOST / "WP-0026"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release", type=Path)
    parser.add_argument("digest")
    args = parser.parse_args()
    guard.run_release(args.release, args.digest)
