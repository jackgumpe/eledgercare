"""Post-freeze non-author audit. Run in the repository with the original input batch."""

import gzip
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path


UPSTREAM = "5cd88ed3f38dd23102045cb8c32580b310dc1424"
TABLES = "fc9cec5661056ef93d7e6f631a6f03db559ce8f4"
ROUTES = [
    ("845a9ebfe088cd4c893f53e27bec4668e4332239", "research"),
    ("8fd868a70882985e2cdf88603fa068c91916a499", "reviews"),
]


def blob(sha, path):
    return subprocess.check_output(["git", "cat-file", "blob", sha + ":" + path])


def rows(data):
    return [json.loads(line) for line in data.splitlines()]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def view_from_upstream(row):
    o = row["observed"]
    amounts = [(f"A{i}", a) for i, a in enumerate(o["amounts"], 1)]
    balances = [(f"B{i}", b) for i, b in enumerate(o["balances"])]
    if o["domain"] == "TRUSTED_OPEN":
        balances = balances[1:]
    names, values = zip(*(amounts + balances + [("T", o["total"])]))
    return dict(mutable=list(names), observed=list(values), answer=row["answer"])


def check_geometry(view, results, scored):
    names, obs, answer = view["mutable"], view["observed"], view["answer"]
    index = {name: j for j, name in enumerate(names)}
    finite = [obs[:]] if answer["clean"] else []
    for changes in answer["finite"]:
        x = obs[:]
        for cell, err in changes:
            x[index[cell]] -= err
        finite.append(x)
    family = answer["families"]
    origin, step = obs[:], [0] * len(names)
    excluded = set()
    if family:
        f, = family
        for cell, a, b in zip(f["support"], f["offset"], f["slope"], strict=True):
            origin[index[cell]] -= a
            step[index[cell]] = -b
        excluded = set(f["excluded"])

    def vector(ref):
        if set(ref) == {"i"}:
            assert type(ref["i"]) is int and 0 <= ref["i"] < len(finite)
            return finite[ref["i"]]
        assert set(ref) == {"c"} and family and type(ref["c"]) is int and ref["c"] not in excluded
        return [a + ref["c"] * b for a, b in zip(origin, step)]

    def on_line(point, columns):
        # Every moving coordinate adds an exact equation for the same integer.
        required = set()
        for j in columns:
            gap = point[j] - origin[j]
            if step[j] == 0:
                if gap:
                    return False
            elif gap % step[j]:
                return False
            else:
                required.add(gap // step[j])
        return len(required) <= 1 and required.isdisjoint(excluded)

    assert len(set(map(tuple, finite))) == len(finite)
    assert not family or all(not on_line(p, range(len(names))) for p in finite)
    single = len(finite) == 1 and not family
    distances = []
    counts = Counter()
    for mask in range(1 << len(names)):
        cols = [j for j in range(len(names)) if mask & (1 << j)]
        values = {tuple(p[j] for j in cols) for p in finite}
        collision = len(values) < len(finite)
        if family:
            collision |= not any(step[j] for j in cols) or any(on_line(p, cols) for p in finite)
        if single:
            d = None
        elif collision:
            d = 0
        else:
            # Removing a differing coordinate of a closest pair reduces its
            # distance by one. A single deletion cannot reduce it by more.
            d = 1 + min(distances[mask ^ (1 << j)] for j in cols)
        distances.append(d)
        for r in results:
            check = r["checks"][mask]
            assert check["d"] == d
            if collision:
                left, right = map(vector, check["pair"])
                assert left != right and all(left[j] == right[j] for j in cols)
            else:
                assert check["pair"] is None
        if collision:
            counts["collisions"] += 1
            counts["witness_pairs_different"] += results[0]["checks"][mask]["pair"] != results[1]["checks"][mask]["pair"]
    assert distances == scored["distance_by_mask"]
    hits = [q for q, d in enumerate(distances) if d != 0]
    k = min(q.bit_count() for q in hits)
    ties = [q for q in hits if q.bit_count() == k]
    assert all(r["minima"] == ties and r["k"] == k and r["status"] == "OK" for r in results)
    assert all(len(r["checks"]) == len(distances) for r in results)
    assert ties == scored["minimum_masks"] and k == scored["k"]
    balance_mask = sum(1 << j for j, name in enumerate(names) if name.startswith("B"))
    assert distances[balance_mask] != 0 and k <= balance_mask.bit_count()
    counts["masks"] = len(distances)
    counts["tied_sets"] = len(ties)
    counts["smaller"] = sum(q.bit_count() < k for q in range(len(distances)))
    counts["tied_size_collisions"] = sum(q.bit_count() == k and d == 0 for q, d in enumerate(distances))
    counts["ambiguous_can_correct_one_on_full_set"] = int(not single and distances[-1] >= 3)
    return counts


def audit(batch_path):
    raw_batch = batch_path.read_bytes()
    assert digest(raw_batch) == "d2f64e31f668cad2aa11a75dab0697b45f61ea2f9d9226dd1c14295b9f16f611"
    batch = rows(raw_batch)
    raw_routes = []
    for rev, area in ROUTES:
        path = f"docs/{area}/WP-0039/evidence/run-01/"
        zipped = blob(rev, path + "outputs.jsonl.gz")
        receipt = json.loads(blob(rev, path + "runtime.json"))
        assert digest(zipped) == receipt["outputs_sha256"]
        records = rows(gzip.decompress(zipped))
        assert len(records) == len(batch) == receipt["rows"] == 310
        assert all(r["exception"] is None for r in records)
        raw_routes.append([r["answer"] for r in records])
    groups = {}
    seen = set()
    for section in ("grid", "named", "interface"):
        upstream = {}
        if section != "interface":
            data = blob(UPSTREAM, f"docs/coordination/WP-0038/results/{section}.jsonl")
            upstream = {(r["id"], r["variant"]): r for r in rows(data)}
        totals = Counter()
        table = rows(blob(TABLES, f"docs/coordination/WP-0039/results/{section}.jsonl"))
        for r in table:
            i = r["operator_row"]
            assert 0 <= i < len(batch) and i not in seen
            seen.add(i)
            view = batch[i]
            if section != "interface":
                source = upstream.pop((r["id"], r["variant"]))
                assert view_from_upstream(source) == view
                assert source["generated_grid_id"] == r["generated_grid_id"]
            outcomes = [route[i] for route in raw_routes]
            state = view["answer"]["status"]
            if state == "ADMITTED" and section != "interface":
                totals.update(check_geometry(view, outcomes, r))
                totals[f"k{r['k']}"] += 1
            else:
                if state == "OUT_OF_DOMAIN_TRUSTED_OPENING":
                    ans = view["answer"]
                    assert ans["solve_skipped"] and ans["D"] is None and ans["rho"] is None
                    assert not (ans["clean"] or ans["finite"] or ans["families"])
                    expected = state
                else:
                    expected = "ADMITTED_EMPTY" if state == "ADMITTED" else "UNSUPPORTED"
                stop = dict(status=expected, k=None, minima=[], checks=[])
                assert all(result == stop for result in outcomes)
                assert r["status"] == expected and not r["checked_masks"]
                totals[expected] += 1
        assert not upstream
        groups[section] = totals
    assert seen == set(range(len(batch)))
    return groups


if __name__ == "__main__":
    print(json.dumps(audit(Path(sys.argv[1])), indent=2, sort_keys=True))
