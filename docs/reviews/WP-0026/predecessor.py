"""Read every member and recompute cross-mode EOS parity and the four WP25 H captures."""
import argparse
from itertools import combinations
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_common import ARCHIVE25, ROOT, SCRATCH, blob, cpu, reference, sample, save, sha, stream

def inspect():
    cpu()
    from h0_inputs import check
    name = "docs/reviews/WP-0025/window-repeat-r1"
    inventory = json.loads(blob(ARCHIVE25, name+"-inventory.json"))
    archive = ROOT/(name+".zip")
    assert sha(archive.read_bytes()) == inventory["archive"]["sha256"] == "85efa292f454eed04fe73a6d8c4280db619ca97b5a031dbb31e88b84804ff764"
    samples, traces, streams = {}, {}, {}
    with TemporaryDirectory(dir=SCRATCH) as tmp, ZipFile(archive) as z:
        assert z.testzip() is None
        assert len(z.namelist()) == len(set(z.namelist())) == 108 and set(z.namelist()) == inventory["files"].keys()
        for key, expected in inventory["files"].items():
            raw = z.read(key)
            assert len(raw) == expected["size"] and sha(raw) == expected["sha256"]
        for order, modes in (("p1","SHHS"),("p2","HSSH")):
            for ordinal, mode in enumerate(modes,1):
                tag = f"{order.upper()}J{ordinal}{mode}"
                prefix = f"runs/{order}/sensor/{tag}/"
                directory = Path(tmp)/tag
                directory.mkdir()
                for key in z.namelist():
                    if key.startswith(prefix):
                        (directory/key.removeprefix(prefix)).write_bytes(z.read(key))
                samples[tag] = sample(directory, mode == "H", reference())
                streams[tag] = stream(directory)
                if mode == "H":
                    traces[tag] = [(directory/file).read_bytes() for file in ("token_hidden.bf16","pooled.f32","through-eos.u32le")]
    warmed = [key for key in traces if "J1" not in key]
    pairs = []
    for a,b in combinations(warmed,2):
        assert traces[a] == traces[b]
        pairs.append({"left":a,"right":b,"bytes":[len(s) for s in traces[a]]})
    matched = []
    for ordinal in range(1,5):
        a,b = [key for key in streams if "J"+str(ordinal) in key]
        assert streams[a] == streams[b]
        matched.append([a,b,sha(streams[a])])
    assert len(set(streams.values())) == 2 and len(pairs) == 3 and len(traces) == 4
    assert all(samples[key]["pooled_bit_exact"] == 14 and samples[key]["positions"] == 284 for key in traces)
    assert traces["P2J1H"][0][:2560] != traces[warmed[0]][0][:2560]
    return {"archive_revision":ARCHIVE25, "archive":inventory["archive"], "verified_members":108,
            "samples":samples, "matched_ordinal_S_H":matched, "later_H_raw_byte_comparisons":pairs,
            "bit_exact_pools_reconstructed":sum(samples[key]["pooled_bit_exact"] for key in traces),
            "first_recorded_consumed_row_differs_from_warm":True, "h0_inputs":check(),
            "model_calls":0}

if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("output", type=Path)
    save(cli.parse_args().output, inspect())
