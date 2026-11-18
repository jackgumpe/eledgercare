"""Pinned identities and shared helpers for the WP-0017 escrow reviewer (eld-rd-reviewer). Stdlib only.

Never imports torch, never queries a device, never resolves Packet B and never opens H/A truth or the
private WP-0016 score-detail files. Every committed input is read from an exact Git blob and verified by
SHA-256 before use; every on-disk run file is re-hashed against the committed WP-0016 blind inventory.
"""
import hashlib
import json
import subprocess
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SPEED = Path("C:/Users/jackg/eLedgerCare-Speed")
WP16_RUNS = SPEED / "WP-0016/review/runs"
WP16_INPUTS = SPEED / "WP-0016/review/inputs"
WP17 = SPEED / "WP-0017"
MODEL_DIR = Path("C:/Users/jackg/eLedgerCare-Q0/WP-0005/models/Unlimited_OCR_2_04809669")

FAMILIES = ("H", "A")  # Packet B stays sealed: never resolved, read or scored by these tools.
PAGE_ID = 128827
BLOCK_ID = 128828
FORK_ID = 128829
EOS_ID = 1

INTEGRATION_BASE = "1e75ebe25814227ef6450913bce301ba9e2ef0f2"
RELEASE_COMMIT = "0d50f40b6520604c2c92f31d3afd74d097149fd5"
DECISION_ANCHOR = "9510d089c074288f9ba5a4bc6e18d7e48e899034"
ENGINE_BASE = "61bec47689dcdf272a525185013f2dce6335fa24"
WRAPPER = "c7b2ee3663317e42a0e9bdd7ff9e17f16747d2cf"
MODEL_REVISION = "0480966938291445591f69f08a13b041c073a96a"
INVENTORY_COMMIT = "6f3273278215fd0ced7555a84e1e692f144b5b69"
STAGE1_COMMIT = "7b70d674457a23a9254756c958db87d68a81da23"
PLANS_COMMIT = "be8c7f1ea16b99662e614d6eb4a2e4c8923114fa"
CARBON_002 = "docs/agent-reports/eld-rd-carbon/WP-0016/002_2026-11-18_research_eld-rd-carbon.md"

# name -> (commit, path, sha256 of the blob bytes)
BLOBS = {
    "specification.pdf": (RELEASE_COMMIT, "docs/coordination/WP-0017/specification.pdf",
                          "6d9de7f13134c1bbe4110f1cce02e369b7f9543a515c1b3205dbe16a5c5d89cd"),
    "G0-blind-inventory.json": (INVENTORY_COMMIT, "docs/reviews/WP-0016/evidence/G0-blind-inventory.json",
                                "366bf5ebb7dc2527c4b11e6f110aa4c08b9f71b6f165d327565b40158bf9ac04"),
    "g0-plans.json": (PLANS_COMMIT, "docs/coordination/WP-0016/g0-plans.json",
                      "53be595ad05302c43aadf76bc8e04af929532877aed2a9ee08c12f32923854fb"),
    "score.py": (ENGINE_BASE, "docs/evaluation/WP-0015/score.py",
                 "1ceb36fe922ef63ea8cd9b2dc2ff55b48abe1193bb818430ddb1531f364f4bf7"),
    "formats.py": (ENGINE_BASE, "docs/research/WP-0015/astra/formats.py",
                   "b832a7ee452f807a01a4acaa4d63fed927241f73b75fc1a47c7ae830ce28c0a6"),
    "rescore.py": ("0186467670074761a777602d77b53deff3451300",
                   "docs/research/WP-0015/astra/sensitivity-title-level/rescore.py",
                   "86b9606468d12afff952b0b24dc7fcd1de932aa9c18400c966a3789e1609b700"),
    "commitments.json": ("7598bf4155452c4a1294b7421595009d39ea1bc9", "docs/evaluation/WP-0015/commitments.json",
                         "5ee817bdd5b7b776c5098186b425b6039ab224abb0ae37a081917dc4148606db"),
}
# Files on disk outside Git, bound by SHA-256 only.
DISK = {
    "tokenizer.json": (MODEL_DIR / "tokenizer.json",
                       "c55c165e32c5a67830362a53e1f548c8930dcc8469efa30ff3252a982799c589"),
    "A/rasters.input.json": (WP16_INPUTS / "A/rasters.input.json",
                             "54ac686476e7f0691a2d69d420c2591f1e22994a95f2ba1212fc4ed978a6de9d"),
}
# Paths a WP-0017 tool must never open (pre-key stages). Checked by guard_path().
FORBIDDEN_NAMES = ("truth.json", "details.json", "escrow-stage2.json", "g0-quality-return.json")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def sha_file(path):
    return sha(Path(path).read_bytes())


def ids_sha(ids):
    """Canonical opaque digest of a token-id sequence: SHA-256 of compact JSON '[a,b,...]' in ASCII."""
    return sha(json.dumps([int(i) for i in ids], separators=(",", ":")).encode("ascii"))


def guard_path(path):
    p = Path(path)
    low = p.as_posix().lower()
    if p.name in FORBIDDEN_NAMES or "/b/" in low or low.endswith("/b") or "packet-b" in low:
        raise SystemExit(f"refusing to open a sealed or private path: {p}")
    return p


def read_bytes(path):
    return guard_path(path).read_bytes()


def load(path):
    return json.loads(read_bytes(path).decode("utf-8-sig"))


def utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def dumps(obj):
    return (json.dumps(obj, indent=1, ensure_ascii=False, allow_nan=False, sort_keys=False) + "\n").encode("utf-8")


def write_new(path, obj):
    """Exclusive-create JSON write; never overwrites evidence. Returns the SHA-256 of the bytes written."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = dumps(obj)
    with path.open("xb") as fh:
        fh.write(data)
    return sha(data)


def git(*args):
    return subprocess.run(["git", "-C", str(REPO), *args], check=True, capture_output=True).stdout


def blob(name):
    """Return the exact committed bytes of a pinned blob after SHA-256 verification."""
    commit, path, want = BLOBS[name]
    data = git("cat-file", "blob", f"{commit}:{path}")
    got = sha(data)
    if got != want:
        raise SystemExit(f"pinned blob {commit}:{path} has {got}, expected {want}")
    return data


def disk(name):
    path, want = DISK[name]
    data = read_bytes(path)
    got = sha(data)
    if got != want:
        raise SystemExit(f"pinned file {path} has {got}, expected {want}")
    return data


def materialize(dest, names):
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=False)
    manifest = {}
    for name in names:
        data = blob(name)
        (dest / name).write_bytes(data)
        manifest[name] = dict(commit=BLOBS[name][0], path=BLOBS[name][1], sha256=sha(data))
    write_new(dest / "manifest.json", manifest)
    return manifest


def tree_hashes(run):
    run = Path(run)
    return {f.relative_to(run).as_posix(): sha_file(f) for f in sorted(run.rglob("*")) if f.is_file()}


class Check:
    """Collects failures; a failed check never raises so every problem is reported together."""

    def __init__(self):
        self.failures = []
        self.count = 0

    def __call__(self, ok, what):
        self.count += 1
        if not ok:
            self.failures.append(what)
        return bool(ok)


# ---- frozen scorer in its own OS process, and transition accounting ---------------------------------

def check_pins(pins, names=("score.py",)):
    for name in names:
        got = sha_file(Path(pins) / name)
        if got != BLOBS[name][2]:
            raise SystemExit(f"pinned file {Path(pins) / name} has {got}, expected {BLOBS[name][2]}")


def run_score(pins, truth, prediction, out, baseline=None, python=None):
    """Frozen common scorer (SHA-256 1ceb36fe...) in its own OS process; output file must be new.
    The truth path is passed to the scorer process; this process never parses it."""
    import sys as _sys
    check_pins(pins)
    out = Path(out)
    if out.exists():
        raise SystemExit(f"score output exists: {out}")
    cmd = [python or _sys.executable, "-I", "-B", str(Path(pins) / "score.py"), str(truth), str(prediction)]
    if baseline is not None:
        cmd += ["--baseline", str(baseline)]
    cmd += ["--out", str(out)]
    subprocess.run(cmd, check=True, cwd=str(pins), stdin=subprocess.DEVNULL)
    return json.loads(out.read_bytes())


def transitions(base, trial, kind="critical"):
    """Per matched reference path, base -> trial (same rules as the WP-0016 escrow, README rule 2/3)."""
    from collections import Counter
    seq_b = [(c["at"], c) for p in base["pages"] for c in p[kind]]
    seq_t = [c["at"] for p in trial["pages"] for c in p[kind]]
    t = {c["at"]: c for p in trial["pages"] for c in p[kind]}
    k, rows, new = Counter(), [], []
    for at, x in seq_b:
        y = t.get(at)
        if y is None:
            k["unmatched"] += 1
            continue
        fx, fy = bool(x.get("flagged")), bool(y.get("flagged"))
        if x["correct"] and y["correct"]:
            c = "stable_correct"
        elif x["correct"]:
            c = "abstain" if y["observed"] is None else "regress"
        elif y["correct"]:
            c = "repair"
        else:
            c = "persist_same" if (x["observed"], fx) == (y["observed"], fy) else "persist_changed"
        k[c] += 1
        nu = (not y["correct"]) and not fy and (x["correct"] or fx)
        if nu:
            new.append(at)
        if c != "stable_correct":
            rows.append(dict(at=at, kind=c, expected=x.get("expected"), base=x["observed"], trial=y["observed"],
                             base_flagged=fx, trial_flagged=fy, new_unflagged=nu))
    names = ("stable_correct", "regress", "abstain", "repair", "persist_same", "persist_changed")
    return dict(paths=len(seq_b), matched_paths=[a for a, _ in seq_b] == seq_t and not k["unmatched"],
                counts={n: k[n] for n in names},
                four_way=dict(CC=k["stable_correct"], CW=k["regress"] + k["abstain"], WC=k["repair"],
                              WW=k["persist_same"] + k["persist_changed"]),
                net_recovery=k["repair"] - k["regress"] - k["abstain"],
                new_unflagged=len(new), new_unflagged_paths=new), rows


def all_flags_false(prediction):
    """True iff every span and every table cell in a prediction carries flagged == False (locked behaviour)."""
    for p in prediction["pages"]:
        for s in p.get("spans", []):
            if s.get("flagged") is not False:
                return False
        for t in p.get("tables", []):
            for row in t.get("rows", []):
                for c in row:
                    if isinstance(c, dict) and c.get("flagged") is not False:
                        return False
    return True


# ---- byte-level BPE decoding (stdlib re-implementation of the GPT-2 byte map) -------------------------

def _bytes_to_unicode():
    bs = list(range(ord("!"), ord("~") + 1)) + list(range(ord("\xa1"), ord("\xac") + 1)) + \
        list(range(ord("\xae"), ord("\xff") + 1))
    cs = bs[:]
    n = 0
    for b in range(256):
        if b not in bs:
            bs.append(b)
            cs.append(256 + n)
            n += 1
    return {chr(c): b for b, c in zip(bs, cs)}


class Vocab:
    """id -> bytes for the pinned tokenizer.json (ByteLevel BPE). Added/special tokens map to their content."""

    def __init__(self, data):
        tok = json.loads(data.decode("utf-8"))
        if tok["model"]["type"] != "BPE" or tok["decoder"]["type"] != "ByteLevel":
            raise SystemExit("unexpected tokenizer type")
        u2b = _bytes_to_unicode()
        self.special = {a["id"]: a["content"] for a in tok["added_tokens"]}
        self.bytes = {}
        for s, i in tok["model"]["vocab"].items():
            if i not in self.special:
                self.bytes[i] = bytes(u2b[c] for c in s)
        for i, s in self.special.items():
            self.bytes[i] = s.encode("utf-8")

    def piece(self, i):
        return self.bytes[int(i)]

    def text(self, i):
        return self.piece(i).decode("utf-8", errors="backslashreplace")

    def decode(self, ids):
        return b"".join(self.piece(i) for i in ids).decode("utf-8", errors="strict")
