"""Enforce exclusivity, admission and source pins using the common Windows board/job guard."""
import argparse
import importlib.util
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("wp16_device_guard",HERE.parent/"WP-0016/device_lease.py")
guard=importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
guard.PACKET=guard.HOST/"WP-0024"


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("release",type=Path)
    p.add_argument("digest")
    args=p.parse_args()
    guard.run_release(args.release,args.digest)
