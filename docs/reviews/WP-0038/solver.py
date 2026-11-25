"""Complete ledgers from observed cells outside each exact support."""

from itertools import combinations
from typing import NamedTuple


class Cell(NamedTuple):
    name: str
    start: int
    end: int
    observed: int


def _balances_from_fixed_cells(cells, holes, vertex_count):
    """Propagate true balances, with one arbitrary zero per component."""
    neighbors = [[] for _ in range(vertex_count)]
    for cell in cells:
        if cell in holes:
            continue
        neighbors[cell.start].append((cell.end, cell.observed))
        neighbors[cell.end].append((cell.start, -cell.observed))

    balances = [None] * vertex_count
    components = 0
    for vertex in range(vertex_count):
        if balances[vertex] is not None:
            continue
        components += 1
        balances[vertex] = 0
        stack = [vertex]
        while stack:
            current = stack.pop()
            for other, step in neighbors[current]:
                implied = balances[current] + step
                if balances[other] is None:
                    balances[other] = implied
                    stack.append(other)
                elif balances[other] != implied:
                    return None
    return balances, components


def _endpoint_family(holes, errors):
    # Only both missing endpoint readings on one OCR row can detach a
    # component. Translating its two true balances shifts both errors equally.
    # Choose its origin so the closing error is zero at c=0.
    opening_offset = errors[0] - errors[1]
    return {
        "support": [cell.name for cell in holes],
        "parameter": "c",
        "domain": "Z",
        "offset": [opening_offset, 0],
        "slope": [1, 1],
        "excluded": sorted({-opening_offset, 0}),
    }


def solve(observed):
    trusted = observed["domain"] == "TRUSTED_OPEN"
    readings = observed["balances"]
    if trusted and readings[0] != observed["anchor"]:
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
    total = observed["total"]
    n = len(amounts)
    # Vertices 0..n are true balances. The last vertex is the monetary
    # origin: distances from it are absolute balance readings.
    origin = n + 1
    cells = [Cell(f"A{i}", i - 1, i, a) for i, a in enumerate(amounts, 1)]
    cells.extend(Cell(f"B{i}", origin, i, b) for i, b in enumerate(readings))
    cells.append(Cell("T", 0, n, total))
    mutable = [cell for cell in cells if not (trusted and cell.name == "B0")]

    result = {
        "status": "ADMITTED",
        "anchor_status": "VERIFIED" if trusted else "OCR_READ",
        "solve_skipped": False,
        "rho": [readings[i + 1] - readings[i] - a for i, a in enumerate(amounts)],
        "D": sum(amounts) - total,
        "clean": False,
        "finite": [],
        "families": [],
    }
    for size in range(3):
        for holes in combinations(mutable, size):
            completed = _balances_from_fixed_cells(cells, holes, n + 2)
            if completed is None:
                continue
            balances, components = completed
            errors = [
                cell.observed - (balances[cell.end] - balances[cell.start])
                for cell in holes
            ]
            if components > 1:
                assert n == 1 and [cell.name for cell in holes] == ["B0", "B1"]
                result["families"].append(_endpoint_family(holes, errors))
            elif not holes:
                result["clean"] = True
            elif all(errors):
                result["finite"].append(
                    [[cell.name, error] for cell, error in zip(holes, errors)]
                )
    return result
