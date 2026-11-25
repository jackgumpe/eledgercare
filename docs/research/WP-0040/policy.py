"""Selective reread policy for the WP-0040 signed-ledger CPU controls."""


def _coordinates(mask, width):
    return [j for j in range(width) if mask & (1 << j)]


def _select(distances, target, areas):
    feasible = [q for q, distance in enumerate(distances) if distance >= target]
    size = min(q.bit_count() for q in feasible)
    ties = [q for q in feasible if q.bit_count() == size]

    def acquisition_cost(q):
        return sum(areas[j] for j in _coordinates(q, len(areas))), q

    return min(ties, key=acquisition_cost), ties


def _at(line, parameter):
    return tuple(h + s * parameter for h, s in zip(line["h"], line["s"], strict=True))


def _on_family(point, line):
    j = next(j for j, s in enumerate(line["s"]) if s)
    parameter, remainder = divmod(point[j] - line["h"][j], line["s"][j])
    return not remainder and parameter not in line["excluded"] and point == _at(line, parameter)


def _decode(points, line, query, radius, y):
    """Return finite survivors, any surviving full family, and minimum mismatch count."""
    survivors = set()
    nearest = None
    for point in points:
        misses = sum(point[j] != y[j] for j in query)
        nearest = misses if nearest is None else min(nearest, misses)
        if misses <= radius:
            survivors.add(point)

    if line is None:
        return survivors, None, nearest

    # Every integer outside the finite root/exclusion set has the generic cost.
    # Each exact moving-coordinate root reduces that cost by one for its parameter.
    generic_cost = 0
    root_matches = {}
    for j in query:
        h, slope = line["h"][j], line["s"][j]
        if slope == 0:
            generic_cost += (h != y[j])
            continue
        generic_cost += 1
        parameter, remainder = divmod(y[j] - h, slope)
        if remainder == 0 and parameter not in line["excluded"]:
            root_matches[parameter] = root_matches.get(parameter, 0) + 1

    family_nearest = generic_cost - max(root_matches.values(), default=0)
    nearest = family_nearest if nearest is None else min(nearest, family_nearest)
    if generic_cost <= radius:
        # Exceptional parameters only improve on generic cost. Keep the original
        # exclusions intact; a separately supplied point can fill an excluded hole.
        return {p for p in survivors if not _on_family(p, line)}, line, nearest

    survivors.update(_at(line, c) for c, matches in root_matches.items()
                     if generic_cost - matches <= radius)
    return survivors, None, nearest


def _constant_cells(points, line, width):
    # An excluded intercept is still the common value wherever its slope is zero.
    reference = line["h"] if line is not None else next(iter(points))
    mask = 0
    for j in range(width):
        if line is not None and line["s"][j]:
            continue
        if all(point[j] == reference[j] for point in points):
            mask |= 1 << j
    return mask, reference


def evaluate(r):
    """Evaluate a single blinded record using its frozen projected distances."""
    result = dict(status="UNSUPPORTED", q=None, d=None, ties=[], points=[],
                  line=None, count=None, diag=None)
    if r["status"] != "ADMITTED":
        if r["status"] == "OUT_OF_DOMAIN_TRUSTED_OPENING":
            result["status"] = r["status"]
        return result

    points = {tuple(point) for point in r["points"]}
    line = r["line"]
    if line is not None and not any(line["s"]):
        points.add(tuple(line["h"]))
        line = None

    arm = r["arm"]
    if line is None and not points:
        result["status"] = "ADMITTED_EMPTY"
        return result
    if line is None and len(points) == 1 and arm != "H":
        result.update(status="FIRST_PASS_SINGLETON", q=0,
                      points=[list(next(iter(points)))], count=1)
        return result

    width = len(r["names"])
    full = (1 << width) - 1
    distances = r["dist"]
    if arm == "B":
        result.update(status="FIRST_PASS_AMBIGUOUS", q=0, d=distances[0])
        return result
    if arm in ("R", "F", "T") and distances[full] < 2:
        result["status"] = "INSUFFICIENT_SEPARATION"
        return result

    radius = 1
    if arm in ("E", "R"):
        target = 1 if arm == "E" else min(3, distances[full])
        q, result["ties"] = _select(distances, target, r["areas"])
        if arm == "E":
            radius = 0
    elif arm in ("F", "T"):
        q = full
    elif arm == "H":
        q, radius = r["q"], r["radius"]
    else:
        raise ValueError(f"unknown arm {arm!r}")

    result.update(q=q, d=distances[q])
    if r["read_status"] != "OK":
        result["status"] = r["read_status"]
        return result

    y = r["y"]
    survivors, surviving_line, nearest = _decode(points, line, _coordinates(q, width), radius, y)
    count = "infinite" if surviving_line is not None else len(survivors)
    status = {0: "INCONSISTENT", 1: "RESOLVED"}.get(count, "AMBIGUOUS")
    result.update(status=status, points=[list(p) for p in sorted(survivors)],
                  line=surviving_line, count=count)

    if arm in ("F", "T"):
        constants, reference = _constant_cells(points, line, width)
        active = _coordinates(full ^ constants, width)
        active_points, active_line, min_active = _decode(points, line, active, radius, y)
        result["diag"] = dict(
            constant_mask=constants,
            mc=sum(y[j] != reference[j] for j in _coordinates(constants, width)),
            min_active=min_active,
            active_count="infinite" if active_line is not None else len(active_points),
            full_count=count,
            exact_full=(nearest == 0),
        )
    return result
