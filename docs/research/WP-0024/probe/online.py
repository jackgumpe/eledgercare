"""Public online cues. Nothing in the state machine accepts truth or a binder identifier."""
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
import html
import json
from pathlib import Path
import re
import sys
import time

import numpy as np
import torch


def clean(value):
    return " ".join(html.unescape(value).split())


def key(value):
    return clean(value).casefold()


def number(value):
    value = clean(value).replace(",", "")
    if not re.fullmatch(r"-?\d+(?:\.\d+)?", value):
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


@dataclass(frozen=True)
class Span:
    index: int
    page: int
    kind: str
    block_kind: str
    text: str
    cells: tuple
    box: tuple


@dataclass(frozen=True)
class Window:
    spans: tuple
    features: torch.Tensor


def load_window(directory):
    directory = Path(directory)
    data = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))
    spans = []
    for index, item in enumerate(data["spans"]):
        if item["index"] != index or item["kind"] not in {"row", "block"}:
            raise ValueError("span index or kind mismatch")
        cells = tuple(clean(c if isinstance(c, str) else c["text"]) for c in item["cells"])
        box = tuple(item["bbox999"])
        if len(box) != 4 or any(not (0 <= c <= 999) for c in box):
            raise ValueError("invalid normalized PDF box")
        if item["page"] not in (1, 2, 3):
            raise ValueError("window-local page outside [1,3]")
        spans.append(Span(index, item["page"], item["kind"], item["block_kind"],
                          item["text"], cells, box))
    path = directory / "pooled.f32"
    if path.stat().st_size != len(spans) * 1280 * 4:
        raise ValueError("incorrect feature byte length")
    matrix = np.fromfile(path, dtype="<f4").reshape(len(spans), 1280)
    if not np.isfinite(matrix).all():
        raise ValueError("nonfinite sensor feature")
    return Window(tuple(spans), torch.from_numpy(matrix))


@dataclass(frozen=True)
class Event:
    kind: str
    value: object
    # (one-based window, window-local page, sensor span index)
    ptr: tuple
    literal: str


def identify(span, ordinal):
    ptr = (ordinal, span.page, span.index)
    if span.kind == "row":
        cells = span.cells
        if cells and key(cells[0]) == "item" and len(cells) >= 2:
            yield Event("HEADER", cells, ptr, span.text)
        if cells and key(cells[0]) in {"posting", "maint-summary"}:
            yield Event("TARGET", cells, ptr, span.text)
        return
    # The separate row records carry table grammar and targets. A block wrapping
    # rows remains a neural observation but must not open/close/post them twice.
    if key(span.block_kind) == "table":
        return
    for line in span.text.splitlines():
        line = clean(line)
        label, sep, value = line.partition(":")
        label, value = key(label), clean(value)
        if sep and value:
            if ordinal == 1 and span.page == 1 and label in ("owners", "units", "schema"):
                values = tuple(clean(v) for v in value.split("/"))
                if len(values) >= 2 and all(values):
                    yield Event("DIRECTORY_" + label.upper(), values, ptr, line)
            elif label in {"ledger", "unit", "unit amendment", "schedule subtotal"}:
                kind = {"ledger": "OPEN_LEDGER", "unit": "DECLARE_UNIT",
                        "unit amendment": "AMEND_UNIT", "schedule subtotal": "TENTATIVE_CLOSE"}[label]
                yield Event(kind, value, ptr, line)
        elif label in ("supporting schedule", "schedule closed"):
            kind = "OPEN_CHILD" if label == "supporting schedule" else "CONFIRM_POP"
            yield Event(kind, None, ptr, line)


@dataclass
class Registry:
    owners: set = field(default_factory=set)
    units: set = field(default_factory=set)
    schemas: set = field(default_factory=set)

    def update(self, event):
        if event.kind == "DIRECTORY_OWNERS":
            self.owners.update(event.value)
        elif event.kind == "DIRECTORY_UNITS":
            self.units.update(event.value)
        elif event.kind == "DIRECTORY_SCHEMA":
            self.schemas.add(event.value)

    def choices(self):
        # Sort by content. No document position, order, source ID, ownership
        # association, number of occurrences, or stored feature enters an anchor.
        sort = lambda items: tuple(sorted(items, key=lambda v: (key(v), v)))
        columns = {schema[1] for schema in self.schemas}
        return {"owner": sort(self.owners), "unit": sort(self.units),
                "column": sort(columns), "subtotal_status": ("BALANCED", "UNBALANCED")}

    def size(self):
        return len(self.owners) + len(self.units) + len(self.schemas)


@dataclass
class Controller:
    depth: int = 0
    held: list = field(default_factory=lambda: [False] * 8)
    fault: str = ""

    def apply(self, event):
        if event.kind == "OPEN_CHILD":
            if self.depth == 7:
                self.fault = "scope_overflow"
            else:
                self.depth += 1
                self.held[self.depth] = False
        elif event.kind == "TENTATIVE_CLOSE" and self.depth > 0:
            self.held[self.depth] = True
        elif event.kind == "CONFIRM_POP":
            if self.depth == 0:
                self.fault = "unmatched_pop"
            else:
                self.held[self.depth] = False
                self.depth -= 1

    def ambiguous(self):
        if self.fault:
            return self.fault
        if self.depth > 0:
            return "shadow_hold" if self.held[self.depth] else "open_child_no_return"
        return ""


@dataclass
class Frame:
    owner: object = None
    unit: object = None
    header: object = None
    subtotal: object = None


def abstain(reason):
    return {"type": "ABSTAIN", "reason": reason}


class Discrete:
    def __init__(self, candidates=None):
        self.registry = candidates if candidates is not None else Registry()
        self.controller = Controller()
        self.frames = [Frame() for _ in range(8)]
        self.trace = []
        self.outputs = []
        self.summary_outputs = []
        self.lookup_ns = 0
        self.registry_growth = []

    def consume(self, event):
        self.registry.update(event)
        depth = self.controller.depth
        frame = self.frames[depth]
        self.controller.apply(event)
        if event.kind == "OPEN_LEDGER":
            frame.owner = event
        elif event.kind in ("DECLARE_UNIT", "AMEND_UNIT"):
            frame.unit = event
        elif event.kind == "HEADER":
            frame.header = event
        elif event.kind == "OPEN_CHILD" and self.controller.depth > depth:
            self.frames[self.controller.depth] = Frame()
        elif event.kind == "TENTATIVE_CLOSE" and depth:
            frame.subtotal = event
        elif event.kind == "CONFIRM_POP" and self.controller.depth < depth:
            self.frames[self.controller.depth].subtotal = frame.subtotal
            self.frames[depth] = Frame()
        elif event.kind == "TARGET":
            self.outputs.append(self.post(frame, event))
            if key(event.value[0]) == 'maint-summary':
                self.summary_outputs.append(self.summary(frame, event))
        self.trace.append({"event": event.kind, "ptr": event.ptr, "literal": event.literal,
                           "depth_after": self.controller.depth,
                           "shadow_hold": self.controller.held[self.controller.depth]})

    def summary(self, frame, target):
        if self.controller.ambiguous():
            return abstain(self.controller.ambiguous())
        observed = number(target.value[1]) if len(target.value) > 1 else None
        subtotal = number(frame.subtotal.value) if frame.subtotal else None
        if observed is None or subtotal is None:
            return abstain("unobserved_subtotal")
        return {"type": "STATUS", "subtotal_status": "BALANCED" if observed == subtotal else "UNBALANCED"}

    def post(self, frame, target):
        ambiguity = self.controller.ambiguous()
        if ambiguity:
            return abstain(ambiguity)
        if not all((frame.owner, frame.unit, frame.header)):
            return abstain("incomplete_frame")
        begin = time.perf_counter_ns()
        choices = self.registry.choices()
        fields = {}
        for name, value in (("owner", frame.owner.value), ("unit", frame.unit.value),
                            ("column", frame.header.value[1])):
            match = [v for v in choices[name] if key(v) == key(value)]
            if len(match) != 1 or len(choices[name]) < 2:
                self.lookup_ns += time.perf_counter_ns() - begin
                return abstain("unresolved_candidate_" + name)
            fields[name] = match[0]
        self.lookup_ns += time.perf_counter_ns() - begin
        fields["subtotal_status"] = None
        if key(target.value[0]) == "maint-summary":
            summary = self.summary(frame, target)
            if summary["type"] == "ABSTAIN":
                return summary
            fields["subtotal_status"] = summary["subtotal_status"]
        return {"type": "Posting", **fields}

    def window(self, window, ordinal):
        for span in window.spans:
            for event in identify(span, ordinal):
                self.consume(event)
        self.registry_growth.append(self.registry.size())


def single(outputs):
    if len(outputs) == 1:
        return outputs[0]
    return abstain("no_target" if not outputs else "multiple_targets")


def reachable_size(obj, seen=None):
    """Bounded object graph for live discrete inference state, including literal strings."""
    if seen is None:
        seen = set()
    if id(obj) in seen:
        return 0
    seen.add(id(obj))
    total = sys.getsizeof(obj)
    if isinstance(obj, dict):
        total += sum(reachable_size(k, seen) + reachable_size(v, seen) for k, v in obj.items())
    elif isinstance(obj, (list, tuple, set)):
        total += sum(reachable_size(v, seen) for v in obj)
    elif hasattr(obj, "__dict__"):
        total += reachable_size(vars(obj), seen)
    return total
