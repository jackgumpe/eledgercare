"""WP-0017 pre-output decision arithmetic. Inputs are reviewer-verified summaries."""
from itertools import combinations
from math import isfinite


SWITCHES = ("S0", "S1a", "S1b", "S1c", "S2", "S3")
WINDOWS = ("019", "037")
NUMERIC_FLOOR_NATS = 1e-5
IDS = ("I08O1-388", "8OI10-774")
ALTERNATES = ("108O1-388", "80I10-774")
A2_ORDERS = (("native", "carbon_bf16", "carbon_surgical"),
             ("carbon_surgical", "carbon_bf16", "native"))


def bits(enabled):
    return "".join("1" if s in enabled else "0" for s in SWITCHES)


def matrix():
    rows = {"native": bits(()), "carbon_bf16": bits(SWITCHES)}
    rows.update(("add_" + s, bits((s,))) for s in SWITCHES)
    rows.update(("remove_" + s, bits(set(SWITCHES) - {s})) for s in SWITCHES)
    return rows


def numbers(values, length, positive=False):
    if not isinstance(values, (list, tuple)) or len(values) != length:
        raise ValueError("incomplete paired observations")
    if any(type(x) not in (int, float) or not isfinite(x) or
           (positive and x <= 0) for x in values):
        raise ValueError("invalid measurement")
    return values


def qualifying_pairs(native, full, additions):
    """Inputs are [pass][window]. A documented aligned free-ID flip also qualifies."""
    for endpoint in (native, full):
        if len(endpoint) != 2:
            raise ValueError("expected two independent endpoint probe passes")
        for run in endpoint:
            numbers(run, 2)
    if set(additions) != set(SWITCHES):
        raise ValueError("expected all six additions")
    noise = [max(NUMERIC_FLOOR_NATS, abs(native[0][w] - native[1][w]),
                 abs(full[0][w] - full[1][w])) for w in range(2)]
    qualifying = []
    for s in SWITCHES:
        row = additions[s]
        deltas = [a - n for a, n in zip(numbers(row["d"], 2), native[0], strict=True)]
        if row["anchored_id_flip"] is True:
            qualifying.append(s)
        elif row["anchored_id_flip"] is not False:
            raise ValueError("ambiguous free-ID flip status")
        elif any(abs(x) > e for x, e in zip(deltas, noise, strict=True)):
            repeat = numbers(row["repeat_d"], 2)
            for w, delta in enumerate(deltas):
                again = repeat[w] - native[1][w]
                if min(abs(again), abs(delta)) > noise[w] and again * delta > 0:
                    qualifying.append(s)
                    break
    return list(combinations(qualifying, 2))


def rank_restorations(removals, rows):
    """Call on complete singles first, then complete eligible pairs only if necessary."""
    if set(rows) != set(removals) or len(set(removals)) != len(removals):
        raise ValueError("missing or duplicate removal trials")
    winners = []
    for removal in removals:
        row = rows[removal]
        times = numbers(row["ordinary_window_seconds"], 2, positive=True)
        if len(row["free_ids"]) != 2 or row["probe_and_bindings_verified"] is not True:
            raise ValueError("incomplete removal evidence")
        if tuple(row["free_ids"]) == IDS:
            winners.append((len(removal), sum(times), tuple(SWITCHES.index(s) for s in removal), removal))
    return min(winners)[-1] if winners else None


def a2(times, new_silent, complete):
    """Orders indexed AB,BA. Silent counts indexed AB/frozen, AB/title, BA/frozen, BA/title."""
    if set(times) != set(A2_ORDERS[0]):
        raise ValueError("expected three timed arms")
    for arm in times:
        numbers(times[arm], 2, positive=True)
    if len(new_silent) != 4 or any(type(n) is not int or n < 0 for n in new_silent):
        raise ValueError("missing matched-view critical counts")
    n, f, s = (times[arm] for arm in A2_ORDERS[0])
    full = [ni - fi for ni, fi in zip(n, f, strict=True)]
    saving = [ni - si for ni, si in zip(n, s, strict=True)]
    spreads = {arm: abs(v[0] - v[1]) for arm, v in times.items()}
    ratios = [ds / df if df > 0 else None for ds, df in zip(saving, full, strict=True)]
    advance = (complete is True and max(new_silent) == 0 and
               all(df > 0 and ds >= 0.60 * df for df, ds in zip(full, saving, strict=True)) and
               min(saving) > max(spreads["native"], spreads["carbon_surgical"]))
    return dict(advance=advance, full_saving=full, surgical_saving=saving,
                retention=ratios, spreads=spreads)
