"""Select minimum simultaneous exact reads by comparing projected true ledgers."""

from collections import Counter
from itertools import combinations
from typing import NamedTuple


class Line(NamedTuple):
    origin: tuple
    slope: tuple
    excluded: frozenset


def _integer(value):
    if type(value) is not int:
        raise ValueError("integer cents or integer parameter required")
    return value


def _points_and_line(record):
    answer = record["answer"]
    observed = tuple(map(_integer, record["observed"]))
    positions = {name: i for i, name in enumerate(record["mutable"])}
    if len(positions) != len(observed) or len(positions) != len(record["mutable"]):
        raise ValueError("mutable names and observed values must correspond")
    if type(answer["clean"]) is not bool or not isinstance(answer["finite"], list):
        raise ValueError("invalid finite candidate representation")
    # Assign references before coalescing any duplicate true points.
    points = {observed: {"i": 0}} if answer["clean"] else {}
    for i, errors in enumerate(answer["finite"], start=int(answer["clean"])):
        point = list(observed)
        used = set()
        for name, cents in errors:
            if name in used:
                raise ValueError("repeated coordinate in point")
            used.add(name)
            point[positions[name]] -= _integer(cents)
        points.setdefault(tuple(point), {"i": i})

    families = answer["families"]
    if not isinstance(families, list) or len(families) > 1:
        raise ValueError("expected at most one integer affine family")
    if not families:
        return points, None
    family = families[0]
    fields = {"parameter", "domain", "support", "offset", "slope", "excluded"}
    if set(family) != fields or family["parameter"] != "c" or family["domain"] != "Z":
        raise ValueError("unrecognized family representation")
    if len(set(family["support"])) != len(family["support"]):
        raise ValueError("repeated family coordinate")
    origin = list(observed)
    slope = [0] * len(observed)
    for name, bias, step in zip(
        family["support"], family["offset"], family["slope"], strict=True
    ):
        j = positions[name]
        origin[j] -= _integer(bias)
        slope[j] = -_integer(step)
    if not any(slope):
        raise ValueError("family must be nonconstant")
    excluded = set(map(_integer, family["excluded"]))
    # Keep references to finite points first. If the representation overlaps,
    # remove exactly those parameter values from the remaining infinite set.
    pivot = next(j for j, step in enumerate(slope) if step)
    for point in points:
        c, remainder = divmod(point[pivot] - origin[pivot], slope[pivot])
        if not remainder and all(a + c * b == x for a, b, x in zip(origin, slope, point)):
            excluded.add(c)
    return points, Line(tuple(origin), tuple(slope), frozenset(excluded))


def _two_parameters(excluded):
    # Each excluded integer can delay at most one element of this enumeration.
    allowed = (c for c in range(len(excluded) + 2) if c not in excluded)
    return next(allowed), next(allowed)


def _point_to_line(point, origin, slope, excluded, default_c):
    """Find one allowed parameter attaining the nearest projected family member."""
    fixed_misses = varying = 0
    matches = Counter()
    for x, a, b in zip(point, origin, slope):
        if b == 0:
            fixed_misses += x != a
            continue
        varying += 1
        c, remainder = divmod(x - a, b)
        if remainder == 0 and c not in excluded:
            matches[c] += 1
    # Coordinates vote for at most one c. Only votes for the SAME c can
    # count together. All other allowed integers match zero varying cells.
    c = max(matches, key=matches.get, default=default_c)
    return fixed_misses + varying - matches[c], c


def _check(points, line, columns):
    def project(values):
        return tuple(values[j] for j in columns)

    projected = [(project(point), ref) for point, ref in points.items()]
    best = None
    for (left, left_ref), (right, right_ref) in combinations(projected, 2):
        d = sum(x != y for x, y in zip(left, right))
        if d == 0:
            return {"d": 0, "pair": [left_ref, right_ref]}
        best = d if best is None else min(d, best)

    if line is not None:
        origin, slope = project(line.origin), project(line.slope)
        first, second = _two_parameters(line.excluded)
        # Every two distinct integer parameters disagree on precisely the
        # nonconstant projected coordinates, regardless of their separation.
        internal = sum(b != 0 for b in slope)
        if internal == 0:
            return {"d": 0, "pair": [{"c": first}, {"c": second}]}
        best = internal if best is None else min(best, internal)
        for point, ref in projected:
            d, c = _point_to_line(point, origin, slope, line.excluded, first)
            if d == 0:
                return {"d": 0, "pair": [ref, {"c": c}]}
            best = min(best, d)
    return {"d": best, "pair": None}


def _stop(status):
    return {"status": status, "k": None, "minima": [], "checks": []}


def plan(record):
    """Return the exact projected distance and collision witness on every subset."""
    try:
        answer = record["answer"]
        if answer["status"] == "OUT_OF_DOMAIN_TRUSTED_OPENING":
            return _stop("OUT_OF_DOMAIN_TRUSTED_OPENING")
        if answer["status"] != "ADMITTED" or answer["solve_skipped"] is not False:
            return _stop("UNSUPPORTED")
        points, line = _points_and_line(record)
    except (KeyError, TypeError, ValueError):
        return _stop("UNSUPPORTED")
    if not points and line is None:
        return _stop("ADMITTED_EMPTY")

    size = len(record["mutable"])
    checks = []
    separating = []
    for mask in range(1 << size):
        columns = [j for j in range(size) if mask & (1 << j)]
        check = _check(points, line, columns)
        checks.append(check)
        if check["d"] != 0:  # Includes the null distance of a singleton.
            separating.append(mask)
    k = min(mask.bit_count() for mask in separating)
    return {
        "status": "OK",
        "k": k,
        "minima": [mask for mask in separating if mask.bit_count() == k],
        "checks": checks,
    }
