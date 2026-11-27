"""A synchronous copy ledger shared by CPU and stock instruction observers."""
import dis
import hashlib
import json
import struct
import sys
from pathlib import Path


PHASES = ("C0_raw", "C1_post_rep", "C2_post_page")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def code_identity(code):
    # Filename is recorded separately. Use the executable bytecode and source statement map.
    return {"qualname": code.co_qualname, "code_sha256": digest(code.co_code),
            "positions_sha256": digest(code.co_linetable),
            "source_sha256": digest(Path(code.co_filename).read_bytes())}


def line_offset(code, line):
    found = [i.offset for i in dis.get_instructions(code) if i.starts_line == line]
    if not found:
        raise ValueError(f"expected a statement entry at {code.co_qualname}:{line}, found {found}")
    return found[0]


class InstructionMonitor:
    """Observe a live executing frame; event arguments alone cannot identify its receiver."""
    def __init__(self, bindings, visit):
        self.bindings = bindings
        self.visit = visit
        self.tool = 4

    def _instruction(self, code, offset):
        tag = self.bindings[code].get(offset)
        if tag is None:
            return sys.monitoring.DISABLE
        frame = sys._getframe(1)
        if frame.f_code is not code or frame.f_lasti != offset:
            raise RuntimeError("ambiguous executing frame or instruction")
        self.visit(tag, frame)

    def __enter__(self):
        mon = sys.monitoring
        mon.use_tool_id(self.tool, "eld-stock-43")
        try:
            mon.register_callback(self.tool, mon.events.INSTRUCTION, self._instruction)
            for code in self.bindings:
                mon.set_local_events(self.tool, code, mon.events.INSTRUCTION)
        except BaseException:
            self.__exit__(None, None, None)
            raise
        return self

    def __exit__(self, *unused):
        mon = sys.monitoring
        for code in self.bindings:
            mon.set_local_events(self.tool, code, 0)
        mon.register_callback(self.tool, mon.events.INSTRUCTION, None)
        mon.free_tool_id(self.tool)


class CaptureAdapter:
    def __init__(self, code, copier, run):
        self.code = code
        self.identity = code_identity(code)
        self.copier = copier
        self.run = run
        self.events = []

    def copy(self, row, frame, source, alias=False):
        if frame.f_code is not self.code:
            raise ValueError("wrong live code")
        seq = len(self.events) + 1
        cid = f"{self.run}/{row}/{seq}"
        data, transport = self.copier(source, alias)
        event = {**self.identity, **transport, "run": self.run, "row": row,
                 "seq": seq, "id": cid, "offset": frame.f_lasti,
                 "frame": id(frame), "receiver": id(frame.f_locals.get("self",frame.f_code)), "source": id(source),"payload_sha256":digest(data)}
        self.events.append(event)
        return {"copy": cid, "data": data, "complete": True, "dtype": "f32le"}


def pack_word(word):
    if not isinstance(word, str) or len(word) != 8:
        raise ValueError("binary32 word requires eight hex digits")
    return struct.pack("<I", int(word, 16))


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))
