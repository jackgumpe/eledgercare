"""Independent expected decisions on signed, mutable ledger coordinates."""

from collections import Counter


def columns(mask, size):
    return [j for j in range(size) if mask & (1 << j)]


def point_at(line, c):
    return tuple(a + c * b for a, b in zip(line["h"], line["s"], strict=True))


def on_family(point, line):
    pivot = next(j for j, slope in enumerate(line["s"]) if slope)
    parameter, remainder = divmod(point[pivot] - line["h"][pivot], line["s"][pivot])
    return not remainder and parameter not in line["excluded"] and point_at(line, parameter) == point


def compatible(points, line, selected, returned, radius):
    """Find every compatible ledger and the exact minimum mismatch count."""
    survivors = set()
    minimum = len(selected) + 1
    for point in points:
        misses = sum(point[j] != returned[j] for j in selected)
        minimum = min(minimum, misses)
        if misses <= radius:
            survivors.add(point)

    if line is not None:
        # At a generic parameter every selected moving coordinate misses. Each
        # divisible equality subtracts one miss at its own allowed integer.
        generic = 0
        discounts = Counter()
        for j in selected:
            h, s = line["h"][j], line["s"][j]
            if s == 0:
                generic += h != returned[j]
                continue
            generic += 1
            parameter, remainder = divmod(returned[j] - h, s)
            if not remainder and parameter not in line["excluded"]:
                discounts[parameter] += 1
        minimum = min(minimum, generic - max(discounts.values(), default=0))
        if generic <= radius:
            # Even integers outside the finite root set qualify. Every root
            # only improves the fit, so the entire allowed family survives.
            return sorted(survivors), line, "infinite", minimum
        for parameter, discount in discounts.items():
            if generic - discount <= radius:
                survivors.add(point_at(line, parameter))

    return sorted(survivors), None, len(survivors), minimum


def choose(r, full):
    arm = r["arm"]
    if arm == "H":
        return r["q"], r["radius"], []
    if arm == "E":
        threshold, radius = 1, 0
    else:
        if r["dist"][full] < 2:
            return None, None, []
        if arm in ("F", "T"):
            return full, 1, []
        if arm != "R":
            raise ValueError("unknown policy arm")
        threshold, radius = min(3, r["dist"][full]), 1

    feasible = [mask for mask, d in enumerate(r["dist"]) if d >= threshold]
    k = min(mask.bit_count() for mask in feasible)
    ties = [mask for mask in feasible if mask.bit_count() == k]
    areas = r["areas"]

    def cost(mask):
        return sum(areas[j] for j in columns(mask, len(areas))), mask

    return min(ties, key=cost), radius, ties


def evaluate(r):
    result = dict(status="UNSUPPORTED", q=None, d=None, ties=[], points=[], line=None, count=None, diag=None)
    if r["status"] != "ADMITTED":
        if r["status"] == "OUT_OF_DOMAIN_TRUSTED_OPENING":
            result["status"] = r["status"]
        return result

    line = r["line"]
    points = {tuple(p) for p in r["points"]}
    if line is not None:
        if any(line["s"]):
            points = {p for p in points if not on_family(p, line)}
        else:
            points.add(tuple(line["h"]))
            line = None
    arm = r["arm"]
    if line is None and not points:
        result["status"] = "ADMITTED_EMPTY"
        return result
    if line is None and len(points) == 1 and arm != "H":
        result.update(status="FIRST_PASS_SINGLETON", q=0, points=[list(points.pop())], count=1)
        return result

    if arm == "B":
        result.update(status="FIRST_PASS_AMBIGUOUS", q=0, d=r["dist"][0])
        return result
    size = len(r["names"])
    full = (1 << size) - 1
    mask, radius, ties = choose(r, full)
    if mask is None:
        result["status"] = "INSUFFICIENT_SEPARATION"
        return result
    result.update(q=mask, d=r["dist"][mask], ties=ties)
    if r["read_status"] != "OK":
        result["status"] = r["read_status"]
        return result

    returned = r["y"]
    finite, family, count, misses = compatible(points, line, columns(mask, size), returned, radius)
    status = {0: "INCONSISTENT", 1: "RESOLVED"}.get(count, "AMBIGUOUS")
    result.update(status=status, points=[list(p) for p in finite], line=family, count=count)
    if arm in ("F", "T"):
        reference = next(iter(points)) if line is None else line["h"]
        constant = [j for j in range(size)
                    if (line is None or line["s"][j] == 0)
                    and all(p[j] == reference[j] for p in points)]
        constant_mask = sum(1 << j for j in constant)
        active = columns(full ^ constant_mask, size)
        _, _, active_count, min_active = compatible(points, line, active, returned, 1)
        result["diag"] = dict(constant_mask=constant_mask,
                              mc=sum(returned[j] != reference[j] for j in constant),
                              min_active=min_active, active_count=active_count,
                              full_count=count, exact_full=misses == 0)
    return result
