"""Export reconciled measurements as browsable tables without rounding binary64 fields."""
import argparse
import csv
import json
from pathlib import Path


def write(path, rows):
    with path.open("x", encoding="utf8", newline="") as out:
        table = csv.DictWriter(out, fieldnames=list(rows[0]), lineterminator="\n")
        table.writeheader()
        table.writerows(rows)


def export(data, custody, directory):
    checkpoints = []
    for record in data["checkpoints"]:
        row = {k:v for k,v in record.items() if k not in ("members","labels")}
        row["checkpoint"] = "/".join(record["labels"])
        for binder, measurement in record["members"].items():
            owner = custody["A"][row["pair"]]["members"][binder]["expected"]["owner"]
            for field in ("top","gap","score_pass","gap_pass","score_hex"):
                row[owner+"_"+field] = measurement[field]
        checkpoints.append(row)
    metrics=[]
    for source in data["metrics"]:
        row=dict(source)
        row["typed_reasons"]=json.dumps(row["typed_reasons"],sort_keys=True,separators=(",",":"))
        row["simultaneous_rate"]=row["simultaneous_wins"]/row["answerable_pairs"] if row["simultaneous_wins"] is not None else None
        metrics.append(row)
    write(directory/"checkpoints.csv", checkpoints)
    write(directory/"terminal-metrics.csv", metrics)
    write(directory/"terminal-pairs.csv", data["terminal_pair_contrasts"])
    write(directory/"calibration-pairs.csv", [
        {"pair":pair, "horizon":info["horizon"], "tier":info["tier"],"answerable":info["answerable"],
         "binder":binder, "target":member["target"], "stratum":member["stratum"],"observed_targets":member["attempt_count"],
         "expected_owner":member["expected"]["owner"],"ordered_record_tags":" ".join(member["windows"])}
        for pair,info in custody["B"].items() for binder,member in info["members"].items()])


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("directory",type=Path)
    args=cli.parse_args()
    export(json.loads((args.directory/"reconciliation.json").read_bytes()),
           json.loads((args.directory/"input-custody.json").read_bytes()),args.directory)
