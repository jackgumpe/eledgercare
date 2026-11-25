"""Enumerate exact supports for signed, measured-minus-true ledger errors."""

from itertools import combinations


def _columns(n, trusted):
    """Columns in mutable cell order, with the total discrepancy in the last row."""
    for row in range(n):
        column = [0] * (n + 1)
        column[row] = -1
        column[-1] = 1
        yield f"A{row + 1}", column

    for index in range(1 if trusted else 0, n + 1):
        column = [0] * (n + 1)
        if index > 0:
            column[index - 1] = 1
        if index < n:
            column[index] = -1
        yield f"B{index}", column

    yield "T", [0] * n + [-1]


def _solve_pair(first, second, target, finite, families):
    first_name, left = first
    second_name, right = second
    pivot = next(i for i, entry in enumerate(left) if entry)

    # The pivot entry is a unit (+1 or -1). Parametrize its equation as
    # x = offset + slope*c, where c is the signed error of the second cell.
    offset = target[pivot] // left[pivot]
    slope = -right[pivot] // left[pivot]
    parameter = None
    for a, b, value in zip(left, right, target):
        # Every other row now imposes coefficient*c = remainder.
        coefficient = a * slope + b
        remainder = value - a * offset
        if coefficient == 0:
            if remainder != 0:
                return
            continue
        quotient, residue = divmod(remainder, coefficient)
        if residue or (parameter is not None and parameter != quotient):
            return
        parameter = quotient

    if parameter is None:
        # Parallel columns. Only the two endpoint balances of a one-row
        # ledger have this property. Their opposite unit columns give slope 1.
        families.append({
            "support": [first_name, second_name],
            "parameter": "c",
            "domain": "Z",
            "offset": [offset, 0],
            "slope": [slope, 1],
            "excluded": sorted({0, -offset // slope}),
        })
    else:
        first_error = offset + slope * parameter
        if first_error and parameter:
            finite.append([[first_name, first_error], [second_name, parameter]])


def solve(observed):
    """Return all zero-, one- and two-cell explanations of an observed ledger."""
    domain = observed["domain"]
    if domain not in ("OCR_OPEN", "TRUSTED_OPEN"):
        raise ValueError("unknown opening domain")
    trusted = domain == "TRUSTED_OPEN"
    balances = observed["balances"]
    if trusted and balances[0] != observed["anchor"]:
        return {
            "status": "OUT_OF_DOMAIN_TRUSTED_OPENING",
            "anchor_status": "CONFLICT",
            "solve_skipped": True,
            "rho": None,
            "D": None,
            "clean": False,
            "finite": [],
            "families": [],
        }

    amounts = observed["amounts"]
    if not amounts or len(balances) != len(amounts) + 1:
        raise ValueError("expected an opening balance and one closing balance per row")
    rho = [balances[i + 1] - balances[i] - amount for i, amount in enumerate(amounts)]
    discrepancy = sum(amounts) - observed["total"]
    target = [*rho, discrepancy]
    columns = list(_columns(len(amounts), trusted))
    finite = []
    families = []

    for name, column in columns:
        pivot = next(i for i, entry in enumerate(column) if entry)
        error = target[pivot] // column[pivot]
        if error and all(entry * error == value for entry, value in zip(column, target)):
            finite.append([[name, error]])

    for first, second in combinations(columns, 2):
        _solve_pair(first, second, target, finite, families)

    return {
        "status": "ADMITTED",
        "anchor_status": "VERIFIED" if trusted else "OCR_READ",
        "solve_skipped": False,
        "rho": rho,
        "D": discrepancy,
        "clean": not any(target),
        "finite": finite,
        "families": families,
    }
