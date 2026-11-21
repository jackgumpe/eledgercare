"""Package replayed line states, target locators and measured R/W word differences by document."""
from argparse import ArgumentParser
import json
from pathlib import Path

from replay import load, overlap


def save(path, value):
    # One record per line keeps the exact state, raw words and pointers readable and searchable.
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write("{\n")
        for field_no, (field, contents) in enumerate(value.items()):
            if field_no:
                f.write(",\n")
            f.write(json.dumps(field) + ": [\n")
            for index, record in enumerate(contents):
                if index:
                    f.write(",\n")
                f.write(json.dumps(record, ensure_ascii=False, separators=(",", ": ")))
            f.write("\n]")
        f.write("\n}\n")


def align_words(rendered, native):
    mapped = []
    for r in rendered:
        viable = [(overlap(r["bbox"], w["bbox"]), n, w) for n,w in native
                  if overlap(r["bbox"],w["bbox"]) > 0]
        if not viable:
            mapped.append({"R": r["ref"], "W": [], "box_delta_W_minus_R": None})
            continue
        viable.sort(key=lambda triple:-triple[0])
        best = viable[0][2]
        delta = [round(x-y, 6) for x,y in zip(best["bbox"],r["bbox"])]
        mapped.append({"R": r["ref"],"W":[w["ref"] for _,_,w in viable],
                       "box_delta_W_minus_R":delta,"same_spelling_best_overlap":r["text"] == best["text"]})
    return mapped


def build(replay, out):
    out.mkdir(parents=True,exist_ok=True)
    for origin in sorted(replay.glob("history-R-*.json")):
        doc = origin.stem.split("-")[-1]
        states, by_state, observations = [], {}, []
        def snapshot(stack):
            key = json.dumps(stack, sort_keys=True)
            if key not in by_state:
                by_state[key] = len(states)
                states.append(stack)
            return by_state[key]
        for arm in ("R","W"):
            history = load(replay / f"history-{arm}-{doc}.json")
            for entry in history:
                result = entry["output"]
                observations.append({"arm":arm,"page":entry["page"],"line":entry["line"],
                                     "words":entry["words"], "before":snapshot(entry["before"]),
                                     "after":snapshot(entry["after"]),"reader_output":result})
        targets = []
        for path in sorted(replay.glob(doc + "-T*.json")):
            row = load(path)
            target = {"key":row["target"]}
            for arm in ("R","W"):
                result = row[arm]
                lines = [{k:v for k,v in line.items() if k in ("line","header_deltas_pt","physical_header_deltas_pt")}
                         for line in result["trace"]]
                target[arm] = {k:v for k,v in result.items() if k != "trace"}
                target[arm]["lines"] = lines
            r, w = row["R"]["trace"], row["W"]["trace"]
            rw = [(line["line"], word) for line in w for word in line["words"]]
            target["R_to_W_by_positive_area"] = [align_words(line["words"],rw) for line in r]
            targets.append(target)
        save(out / (doc + ".json"), {"frame_states":states,"observations":observations,"targets":targets})


if __name__ == "__main__":
    cli = ArgumentParser(description=__doc__)
    cli.add_argument("replay", type=Path)
    cli.add_argument("out", type=Path)
    args = cli.parse_args()
    build(args.replay,args.out)

