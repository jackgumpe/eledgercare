"""Signed owner diagnostics on a fixed literal axis, after both independent reads."""
FLOOR = 1e-6
NAMES = ("Alder", "Cedar")
TIMES = ("t1", "t2", "t3")


def margin(scores):
    if any(scores.get(name) is None for name in NAMES):
        return None
    return scores["Alder"] - scores["Cedar"]


def derived(a, c, initial):
    complete = a is not None and c is not None
    mu = (a + c) / 2 if complete else None
    delta = a - c if complete else None
    change = delta - initial if complete and initial is not None else None
    ratio = delta / initial if change is not None and abs(initial) > FLOOR else None
    win = a > 0 > c if complete else None
    equivalent = delta > 2 * abs(mu) if complete else None
    if win != equivalent:
        raise ValueError("strict paired-win equivalence failed")
    return {"margin_Alder_input": a, "margin_Cedar_input": c, "mu": mu, "delta": delta,
            "D": change, "ratio": ratio, "positive_response": delta > 0 if complete else None,
            "correct_paired_win": win, "delta_gt_twice_abs_mu": equivalent}


def trajectory(members):
    owner = {row["owner"]: row["checkpoints"] for row in members}
    if len(members) != 2 or set(owner) != set(NAMES):
        raise ValueError("expected one member for each owner")
    rows = {}
    initial = None
    for t in TIMES:
        a, c = (margin(owner[name][t]["scores"]) for name in NAMES)
        if t == "t1" and a is not None and c is not None:
            initial = a - c
        rows[t] = derived(a, c, initial)
    return rows


def controls():
    cases = {}
    for name, args, expected in (
        ("positive", (0.25, -0.25, 0.25), (0.25, 2.0)),
        ("negative_initial", (0.25, -0.25, -0.25), (0.75, -2.0)),
        ("negative_delta", (-0.25, 0.25, -0.25), (-0.25, 2.0)),
        ("zero", (0.25, -0.25, 0.0), (0.5, None)),
        ("near_zero", (0.25, -0.25, FLOOR/2), (0.5-FLOOR/2, None)),
        ("at_floor", (0.25, -0.25, -FLOOR), (0.5+FLOOR, None)),
        ("missing_initial", (0.25, -0.25, None), (None, None)),
        ("missing_checkpoint", (0.25, None, 0.25), (None, None)),
    ):
        row = derived(*args)
        if (row["D"], row["ratio"]) != expected:
            raise ValueError(name)
        cases[name] = {"initial": args[2], **row}
    raw = {"Alder": 0.125, "Cedar": 0.125}
    row = derived(margin(raw), -0.25, 0.25)
    if row["correct_paired_win"] or row["delta"] != 2*abs(row["mu"]):
        raise ValueError("actual equal leaders counted as paired win")
    cases["tied_leaders"] = {"Alder_input_raw_scores": raw, **row}
    return cases
