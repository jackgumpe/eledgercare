"""Minimum simultaneous exact reads for the signed WP-0038 ledger candidates."""

from itertools import combinations


def _integers(values):
    if not isinstance(values, list) or any(type(v) is not int for v in values):
        raise ValueError("expected an integer vector")
    return values


def _true_vector(observed, indices, cells, errors):
    """Subtract one sparse signed-error vector from the dense observation."""
    if len(cells) != len(set(cells)):
        raise ValueError("repeated cell in a support")
    result = list(observed)
    for cell, error in zip(cells, _integers(errors), strict=True):
        result[indices[cell]] -= error
    return tuple(result)


def _decode(record):
    answer = record["answer"]
    if answer["anchor_status"] not in ("VERIFIED", "OCR_READ") or answer["solve_skipped"] is not False:
        raise ValueError("unknown admission representation")
    mutable = record["mutable"]
    observed = _integers(record["observed"])
    if not isinstance(mutable, list) or not all(isinstance(cell, str) for cell in mutable):
        raise ValueError("expected mutable cell names")
    indices = {cell: i for i, cell in enumerate(mutable)}
    if len(indices) != len(mutable) or len(mutable) != len(observed):
        raise ValueError("inconsistent coordinate system")

    if type(answer["clean"]) is not bool or not isinstance(answer["finite"], list):
        raise ValueError("unknown finite representation")
    points = [tuple(observed)] if answer["clean"] else []
    for hypothesis in answer["finite"]:
        if not isinstance(hypothesis, list):
            raise ValueError("expected sparse finite errors")
        cells = []
        errors = []
        for cell, error in hypothesis:
            cells.append(cell)
            errors.append(error)
        points.append(_true_vector(observed, indices, cells, errors))

    families = answer["families"]
    if not isinstance(families, list) or len(families) > 1:
        raise ValueError("expected at most one affine integer family")
    family = None
    if families:
        entry = families[0]
        fields = {"domain", "parameter", "support", "offset", "slope", "excluded"}
        if set(entry) != fields or entry["domain"] != "Z" or entry["parameter"] != "c":
            raise ValueError("unknown affine family representation")
        cells = entry["support"]
        if not isinstance(cells, list):
            raise ValueError("expected sparse affine support")
        intercept = _true_vector(observed, indices, cells, entry["offset"])
        slope = _true_vector([0] * len(observed), indices, cells, entry["slope"])
        if not any(slope):
            raise ValueError("expected a nonconstant affine family")
        family = intercept, slope, set(_integers(entry["excluded"]))
    return len(mutable), points, family


def _difference_mask(left, right):
    return sum(1 << i for i, (a, b) in enumerate(zip(left, right, strict=True)) if a != b)


def _point_family_masks(point, intercept, slope, excluded):
    """Yield every support against one fixed point, with an admissible integer witness.

    In a constant coordinate equality is always true or always false. In a
    moving coordinate it holds at most at the single root (point - intercept)
    / slope. Grouping integral, allowed roots by parameter clears exactly the
    coordinates equal at that SAME parameter. At every other allowed integer
    all moving coordinates differ. One integer past all excluded and exceptional
    values witnesses this entire remaining class, regardless of their magnitude.
    """
    generic = 0
    equal_at = {}
    for i, (value, base, step) in enumerate(zip(point, intercept, slope, strict=True)):
        bit = 1 << i
        if step:
            generic |= bit
            c, remainder = divmod(value - base, step)
            if remainder == 0 and c not in excluded:
                equal_at[c] = equal_at.get(c, 0) | bit
        elif value != base:
            generic |= bit
    for c, equal in equal_at.items():
        yield generic & ~equal, c
    yield generic, max(excluded | equal_at.keys(), default=-1) + 1


def difference_supports(points, family):
    """Map every distinct nonempty difference support to one actual ledger pair.

    The finite list uses the input indices, including the leading clean point
    when present. A zero difference compares the same ledger and contributes
    no constraint. Duplicate supports are equivalent for every query mask.
    """
    supports = {}
    for (i, left), (j, right) in combinations(enumerate(points), 2):
        mask = _difference_mask(left, right)
        if mask:
            supports.setdefault(mask, [{"i": i}, {"i": j}])

    if family is not None:
        intercept, slope, excluded = family
        # Any two different family parameters differ on exactly the moving
        # coordinates: their difference is the nonzero integer gap times slope.
        self_mask = sum(1 << i for i, step in enumerate(slope) if step)
        c = max(excluded, default=-1) + 1
        supports.setdefault(self_mask, [{"c": c}, {"c": c + 1}])
        for i, point in enumerate(points):
            for mask, c in _point_family_masks(point, intercept, slope, excluded):
                if mask:
                    supports.setdefault(mask, [{"i": i}, {"c": c}])
    return supports


def _no_plan(status):
    return {"status": status, "k": None, "minima": [], "checks": []}


def plan(record):
    """Return exact projected distances, collision witnesses and tied minima."""
    try:
        status = record["answer"]["status"]
        if status == "OUT_OF_DOMAIN_TRUSTED_OPENING":
            return _no_plan(status)
        if status != "ADMITTED":
            return _no_plan("UNSUPPORTED")
        width, points, family = _decode(record)
    except (KeyError, TypeError, ValueError):
        return _no_plan("UNSUPPORTED")
    if not points and family is None:
        return _no_plan("ADMITTED_EMPTY")

    supports = difference_supports(points, family)
    checks = []
    minima = []
    k = width + 1
    for query in range(1 << width):
        # Hamming distance on query is the size of its intersection with a
        # difference support. A missed support supplies a concrete collision.
        distance = None
        collision = None
        for support, pair in supports.items():
            overlap = (query & support).bit_count()
            if overlap == 0:
                distance, collision = 0, pair
                break
            if distance is None or overlap < distance:
                distance = overlap
        checks.append({"d": distance, "pair": collision})
        if distance != 0:
            size = query.bit_count()
            if size < k:
                k = size
                minima = []
            if size == k:
                minima.append(query)
    return {"status": "OK", "k": k, "minima": minima, "checks": checks}
