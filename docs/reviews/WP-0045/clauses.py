"""Independent finite realizations. No fixture identities enter this interface."""
from collections import Counter
from fractions import Fraction
import json
import math
import struct


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def provenance(rel, atoms):
    expected, observed, evidence = (rel[k] for k in ("expected", "observed", "evidence"))
    assert expected.keys() == atoms.keys() == evidence.keys()
    values, source, reason = {}, {}, {}
    for key, prescribed in atoms.items():
        hint = evidence[key]
        source[key] = hint["source"]
        if key not in observed or hint != prescribed:
            values[key], reason[key] = "U", "unresolved"
        elif encoded(expected[key]) != encoded(observed[key]):
            values[key] = "M"
            reason[key] = ("unauthorized_writer" if key == "B.writer" else
                           "wrong_origin" if key in {"E.caller", "E.child", "B.origin"} else "integrity")
        else:
            values[key] = "P"
    order = ("M", "U", "P").index
    groups = {group: min((v for k, v in values.items() if k.startswith(group + ".")), key=order)
              for group in "LIEACB"}
    custody = min((groups[k] for k in "LIEAB"), key=order)
    first = None
    if reason:
        times = [evidence[k]["at"] for k in reason]
        at = None if None in times else min(times)
        first = dict(at=at, keys=sorted(k for k in reason if at is None or evidence[k]["at"] == at))
    return dict(values=values, source=source, reason=reason, coordinates=groups, custody=custody,
                status=min(custody, groups["C"], key=order), content=values["content.bytes"], first=first,
                conflicts=sorted(k for k,v in values.items() if v=="M"),
                missing=sorted(k for k,v in values.items() if v=="U"))


def branch(row):
    mode, k, a, selected = (row[n] for n in ("mode", "k", "a", "select"))
    choices = {"stock": {"stock"}, "duplicate": {"stock", "duplicate"}, "literal": {f"k{k}"}}
    if selected not in choices[mode] or (k >= 1) != (mode == "literal"):
        return dict(status="M", reason="invalid_selection", commits=0, history=[])
    calls, decoded, candidates = [], [], {}
    def evaluate(name, x, readout):
        hidden = x + 1
        calls.append([name, x, hidden])
        if readout:
            decoded.append([name, hidden])
            candidates[name] = ["u:" + name, hidden, "g:" + name]
        return hidden
    hidden = evaluate("stock", a, mode != "literal")
    if mode == "duplicate":
        evaluate("duplicate", a, True)
    if mode == "literal":
        for index in range(1, k+1):
            hidden = evaluate(f"k{index}", hidden, index == k)
    chosen = candidates[selected]
    history = [chosen.copy()] if row["commit"] else []
    return dict(status="P", calls=calls, decoded=decoded, selected=selected, transition=chosen,
                commits=len(history), history=history)


def scores(row):
    phases = ["raw", "repeat", "page"]
    data = {phase: row[phase] for phase in phases}
    num = lambda word: struct.unpack(">f", bytes.fromhex(word))[0]
    conflicts = [["raw", i] for i, word in enumerate(data["raw"]) if not math.isfinite(num(word))]
    active = set(range(len(data["raw"])))
    for prev, phase in zip(phases, phases[1:]):
        blocked = set(row[phase + "_block"])
        active -= blocked
        for i, word in enumerate(data[phase]):
            intended = "ff800000" if i in blocked else data[prev][i]
            if word != intended:
                conflicts.append([phase, i])
    if not active:
        conflicts.append(["support", -1])
    winner = None if conflicts else min(active, key=lambda i: (-num(data["page"][i]), i))
    return dict(**data, status="M" if conflicts else "P", conflicts=conflicts,
                first=conflicts[0] if conflicts else None, allowed=sorted(active), winner=winner)


def query(row):
    if row["mode"] == "exact":
        candidates = set(map(tuple, row["F"]))
        if len(candidates) <= 1:
            return dict(status="IDENTIFIED" if candidates else "CONFLICT", action=None)
        columns = [Counter(col) for col in zip(*candidates)]
        cost, index = min((sum(c*c for c in counts.values()), i)
                          for i, counts in enumerate(columns) if len(counts) > 1)
        return dict(status="QUERY", action=index)
    p = list(map(Fraction, row["p"]))
    budget, used = row["budget"], set(row["used"])
    actions = {a["id"]: (a["source"], [[Fraction(v) for v in line] for line in a["law"]])
               for a in row["actions"]}
    obs = row["observation"]
    if obs is not None:
        source, law = actions[obs["action"]]
        if budget and source not in used:
            weighted = [v * line[obs["outcome"]] for v, line in zip(p, law)]
            mass = sum(weighted)
            if mass == 0:
                return dict(status="MODEL_CONFLICT", posterior=None, action=None, gain=None)
            p = [v/mass for v in weighted]
            budget -= 1
            used.add(source)
    answer = dict(status="UNRESOLVED", posterior=list(map(str,p)), action=None, gain=None)
    if max(p) >= Fraction(row["threshold"]):
        return dict(answer, status="ACCEPT")
    if not budget:
        return answer
    choices = []
    for number, (source, law) in actions.items():
        if source in used:
            continue
        # Each outcome contributes its positive probability times the squared posterior change.
        gain = Fraction(0)
        for column in zip(*law):
            w = [v*l for v,l in zip(p,column)]
            mass = sum(w)
            if mass:
                gain += mass * sum((wi/mass - v)**2 for wi,v in zip(w,p))
        if gain > 0:
            choices.append((-gain, number))
    if choices:
        minus_gain, number = min(choices)
        answer.update(status="QUERY", action=number, gain=str(-minus_gain))
    return answer

