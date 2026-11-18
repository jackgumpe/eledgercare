"""Copy selected synthetic results, logs and timers; exclude model caches and materialized inputs."""
import argparse
import hashlib
import json
from pathlib import Path

parser = argparse.ArgumentParser(__doc__)
parser.add_argument("runs", type=Path)
parser.add_argument("cpu", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
inventory = {}


def retain(source, rel):
    data = source.read_bytes()
    target = args.output / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    inventory[rel] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


for name in ("cpu.json", "process.json"):
    retain(args.cpu / name, "cpu/" + name)
for stage in ("fresh-A", "fresh-B", "fresh-S", "resident"):
    source = args.runs / stage
    for name in ("process.json", "stdout.txt", "stderr.txt"):
        retain(source / name, stage + "/" + name)
    if stage.startswith("fresh-"):
        for name in ("request.json", "score.json", "output/envelope.json", "output/raw_output.utf8.bin"):
            retain(source / name, stage + "/" + name)
    else:
        for ix, case in enumerate("ABABAS", 1):
            for name in ("score.json", "native.json", "events.json", "envelope.json", "raw_output.utf8.bin"):
                rel = f"{ix}-{case}/{name}"
                retain(source / rel, stage + "/" + rel)
(args.output / "inventory.json").write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
