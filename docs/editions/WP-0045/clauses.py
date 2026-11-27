"""Edition 02.1, finite normal entry. python clauses.py < one-input.json"""
from collections import Counter
from dataclasses import dataclass
from fractions import Fraction
import json
import math
import struct
import sys


@dataclass(frozen=True)
class Branch:
    name: str
    argument: int
    hidden: int
    update: str

    @classmethod
    def evaluate(cls, name, argument):
        return cls(name, argument, argument + 1, "u:" + name)

    def decode(self):
        return (self.update, self.hidden, "g:" + self.name)


def token(row):
    mode, k, choice = row["mode"], row["k"], row["select"]
    allowed = {"stock": {"stock"}, "duplicate": {"stock", "duplicate"},
               "literal": {f"k{k}"}}[mode]
    if choice not in allowed:
        return {"status": "M", "reason": "invalid_selection", "commits": 0, "history": []}
    anchor = row["a"]
    branches = [Branch.evaluate("stock", anchor)]
    if mode == "duplicate":
        branches.append(Branch.evaluate("duplicate", anchor))
    for step in range(1, k + 1):
        branches.append(Branch.evaluate(f"k{step}", branches[-1].hidden))
    readouts = branches if mode == "duplicate" else branches[-1:]
    tuples = {branch.name: branch.decode() for branch in readouts}
    selected = list(tuples[choice])
    history = [selected.copy()] if row["commit"] else []
    return {"status": "P", "calls": [[b.name, b.argument, b.hidden] for b in branches],
            "decoded": [[name, t[1]] for name, t in tuples.items()], "selected": choice,
            "transition": selected, "commits": len(history), "history": history}


def number(word):
    return struct.unpack(">f", bytes.fromhex(word))[0]


def decode(row):
    raw = row["raw"]
    conflicts = [["raw", j] for j, word in enumerate(raw) if not math.isfinite(number(word))]
    allowed = set(range(len(raw)))
    previous = raw
    for phase in ("repeat", "page"):
        blocked = set(row[phase + "_block"])
        allowed.difference_update(blocked)
        observed = row[phase]
        for j, word in enumerate(observed):
            required = "ff800000" if j in blocked else previous[j]
            if word != required:
                conflicts.append([phase, j])
        previous = observed
    if not allowed:
        conflicts.append(["support", -1])
    ordered = sorted(allowed)
    winner = None if conflicts else max(ordered, key=lambda j: number(previous[j]))
    return {"status": "M" if conflicts else "P", "first": conflicts[0] if conflicts else None,
            "conflicts": conflicts, "allowed": ordered, "winner": winner,
            **{phase: row[phase] for phase in ("raw", "repeat", "page")}}


def exact(rows):
    feasible = set(map(tuple, rows))
    if len(feasible) <= 1:
        return {"status": "IDENTIFIED" if feasible else "CONFLICT", "action": None}
    objectives = []
    for field, column in enumerate(zip(*feasible)):
        counts = Counter(column)
        if len(counts) > 1:
            objectives.append((sum(n*n for n in counts.values()), field))
    return {"status": "QUERY", "action": min(objectives)[1]}


def masses(p, action):
    for likelihoods in zip(*action["law"]):
        yield [prior * Fraction(likelihood) for prior, likelihood in zip(p, likelihoods)]


def gain(p, action):
    expected = Fraction(0)
    for joint in masses(p, action):
        probability = sum(joint)
        if probability:
            expected += sum(value * value for value in joint) / probability
    return expected - sum(prior * prior for prior in p)


def reconcile(row):
    p = list(map(Fraction, row["p"]))
    actions = {a["id"]: a for a in row["actions"]}
    used, budget = set(row["used"]), row["budget"]
    observation = row["observation"]
    if observation is not None and budget:
        action = actions[observation["action"]]
        if action["source"] not in used:
            joint = list(masses(p, action))[observation["outcome"]]
            marginal = sum(joint)
            if not marginal:
                return {"status": "MODEL_CONFLICT", "posterior": None, "action": None, "gain": None}
            p = [value / marginal for value in joint]
            used.add(action["source"])
            budget -= 1
    result = {"status": "UNRESOLVED", "posterior": list(map(str, p)), "action": None, "gain": None}
    if max(p) >= Fraction(row["threshold"]):
        result["status"] = "ACCEPT"
    elif budget:
        best = Fraction(0)
        for key in sorted(actions):
            act = actions[key]
            if act["source"] not in used:
                candidate = gain(p, act)
                if candidate > best:
                    best = candidate
                    result.update(status="QUERY", action=key, gain=str(best))
    return result


def evaluate(row):
    if row["clause"] == "A1":
        return token(row)
    if row["clause"] == "A2":
        return decode(row)
    if row["clause"] == "C1":
        return exact(row["F"]) if row["mode"] == "exact" else reconcile(row)
    raise ValueError("unknown clause")


if __name__ == "__main__":
    print(json.dumps(evaluate(json.load(sys.stdin)), allow_nan=False))
