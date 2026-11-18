"""Pinned identities and shared helpers for the WP-0016 escrow reviewer (eld-rd-reviewer). Stdlib only.

Never imports torch, never queries a device and never resolves Packet B. Third-party sources that decide
outcomes (the frozen scorer, the frozen native adapter and the public title<LEVELn> rule) are materialised
from exact Git blobs into a new directory, verified by SHA-256 and only then loaded or executed. The title
rule is extracted from the committed rescore.py by AST inspection; that file is never executed.
"""
import ast
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PACKET = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0016")
FAMILIES = ("H", "A")  # Packet B stays sealed: never resolved, read or scored by these tools.
LABEL_FAMILY = {"h": "H", "a": "A"}
PAGE_ID = 128827
WINDOW = 3
MIB = 2 ** 20

CONTROL = "61bec47689dcdf272a525185013f2dce6335fa24"
COORD = "9522d7d181958eb87636a94a5e8588388cf537fb"
PLANS_COMMIT = "be8c7f1ea16b99662e614d6eb4a2e4c8923114fa"
RULE_COMMIT = "0186467670074761a777602d77b53deff3451300"
WP15_REVIEW = "565d67400c07d5ece61257a9633a67e9bd779e87"
CUSTODY = "7598bf4155452c4a1294b7421595009d39ea1bc9"

# name -> (commit, path, sha256 of blob bytes)
PINS = {
    "score.py": (CONTROL, "docs/evaluation/WP-0015/score.py",
                 "1ceb36fe922ef63ea8cd9b2dc2ff55b48abe1193bb818430ddb1531f364f4bf7"),
    "formats.py": (CONTROL, "docs/research/WP-0015/astra/formats.py",
                   "b832a7ee452f807a01a4acaa4d63fed927241f73b75fc1a47c7ae830ce28c0a6"),
    "rescore.py": (RULE_COMMIT, "docs/research/WP-0015/astra/sensitivity-title-level/rescore.py",
                   "86b9606468d12afff952b0b24dc7fcd1de932aa9c18400c966a3789e1609b700"),
    "commitments.json": (CUSTODY, "docs/evaluation/WP-0015/commitments.json",
                         "5ee817bdd5b7b776c5098186b425b6039ab224abb0ae37a081917dc4148606db"),
    "g0-plans.json": (PLANS_COMMIT, "docs/coordination/WP-0016/g0-plans.json",
                      "53be595ad05302c43aadf76bc8e04af929532877aed2a9ee08c12f32923854fb"),
    "wp15-H-inventory.json": (WP15_REVIEW, "docs/reviews/WP-0015/evidence/H-blind-inventory.json",
                              "32274a7415077ee7d2fd998d6cd3bf1aba5746dcdfcc3cfd59e08e0d38b0cd6f"),
    "wp15-A-recovery-inventory.json": (WP15_REVIEW, "docs/reviews/WP-0015/evidence/A-recovery-blind-inventory.json",
                                       "54c9a7cbc3aaf8bd6cbded192ae5bb2a7269fc4bcad48db46aa18047b4691d00"),
    "wp15-A-inventory.json": (WP15_REVIEW, "docs/reviews/WP-0015/evidence/A-blind-inventory.json",
                              "84eee0e2d8e7af90e84a55e6a29f6a5cb719fd7485b1c1dad36338814a3e6622"),
}
SCORER_SHA = PINS["score.py"][2]
TITLE_PATTERN = r"(<BLOCK>title)<LEVEL(\d+)>(?=\s*\[\s*\d+,\s*\d+,\s*\d+,\s*\d+\s*\]<FORK>)"
TITLE_TEMPLATE = r"\1"

# Stored WP-0015 Windows references (same prediction bytes in both WP-0015 orders; clocks differ).
# primary = the Windows run paired with a complete native in AB order (H 1.023.. s, A 15.6546455 s).
WINDOWS_REFS = {
    "H": dict(inventory="wp15-H-inventory.json",
              primary=("h-r1-ab", "04-h-windows"), sensitivity=("h-r2-ba", "03-h-windows"), declared_primary_s=1.023),
    "A": dict(inventory="wp15-A-recovery-inventory.json", sensitivity_inventory="wp15-A-inventory.json",
              primary=("a-recovery-ab", "04-a-windows"), sensitivity=("a-scale-ba", "03-a-windows"),
              declared_primary_s=15.6546455),
}

# Pre-registered numerical gates (assignment table at 9522d7d).
G0 = dict(cer_delta_max=0.01, cell_delta_min=-0.02, peak_mib_max=10000, new_unflagged_critical_max=0)
EPS = 1e-12


def sha(data):
    return hashlib.sha256(data).hexdigest()


def sha_file(path):
    return sha(Path(path).read_bytes())


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def write_new(path, obj):
    """Exclusive-create JSON write; never overwrites evidence."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(obj, indent=1, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    with path.open("xb") as fh:
        fh.write(data)
    return sha(data)


def git_blob(commit, path):
    return subprocess.run(["git", "-C", str(REPO), "cat-file", "blob", f"{commit}:{path}"],
                          check=True, capture_output=True).stdout


def materialize(dest):
    """Write every pinned blob into a NEW directory after SHA-256 verification; return its manifest."""
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=False)
    manifest = {}
    for name, (commit, path, want) in PINS.items():
        data = git_blob(commit, path)
        got = sha(data)
        if got != want:
            raise SystemExit(f"pinned blob {commit}:{path} has {got}, expected {want}")
        (dest / name).write_bytes(data)
        manifest[name] = dict(commit=commit, path=path, sha256=got)
    rule = title_rule(dest)
    manifest["title_rule"] = dict(pattern=rule.pattern, template=TITLE_TEMPLATE, extracted_by="ast")
    write_new(dest / "manifest.json", manifest)
    return manifest


def check_pins(pins, names=("score.py", "formats.py", "rescore.py")):
    pins = Path(pins)
    for name in names:
        got = sha_file(pins / name)
        if got != PINS[name][2]:
            raise SystemExit(f"pinned file {pins / name} has {got}, expected {PINS[name][2]}")


def is_pinned(path, name):
    return Path(path).is_file() and sha_file(path) == PINS[name][2]


def title_rule(pins):
    """Extract TITLE and its substitution template from the committed rule without executing it."""
    check_pins(pins, ("rescore.py",))
    tree = ast.parse((Path(pins) / "rescore.py").read_bytes())
    patterns = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "TITLE" for t in node.targets):
            call = node.value
            if not (isinstance(call, ast.Call) and ast.unparse(call.func) == "re.compile" and len(call.args) == 1
                    and not call.keywords):
                raise SystemExit("TITLE is not a single-argument re.compile")
            patterns.append(ast.literal_eval(call.args[0]))
    subs = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and ast.unparse(n.func) == "TITLE.sub"]
    templates = {ast.literal_eval(n.args[0]) for n in subs}
    if patterns != [TITLE_PATTERN] or templates != {TITLE_TEMPLATE}:
        raise SystemExit(f"committed rule differs: patterns={patterns!r} templates={templates!r}")
    return re.compile(patterns[0])


def load_formats(pins):
    """Load the pinned frozen adapter as an isolated module object (no sys.path change)."""
    check_pins(pins, ("formats.py",))
    spec = importlib.util.spec_from_file_location("wp16_pinned_formats", Path(pins) / "formats.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_score(pins, truth, prediction, out, baseline=None):
    """Frozen common scorer in its own OS process; output file must be new."""
    check_pins(pins, ("score.py",))
    out = Path(out)
    if out.exists():
        raise SystemExit(f"score output exists: {out}")
    cmd = [sys.executable, "-I", "-B", str(Path(pins) / "score.py"), str(truth), str(prediction)]
    if baseline is not None:
        cmd += ["--baseline", str(baseline)]
    cmd += ["--out", str(out)]
    subprocess.run(cmd, check=True, cwd=str(pins), stdin=subprocess.DEVNULL)
    return load(out)


def run_title_adapter(pins, doc, out_prediction, out_receipt):
    """Public title<LEVELn> adapter in its own OS process; outputs must be new."""
    cmd = [sys.executable, "-I", "-B", str(HERE / "title_adapt.py"), "--pins", str(pins), "--doc", str(doc),
           "--out", str(out_prediction), "--receipt", str(out_receipt)]
    subprocess.run(cmd, check=True, cwd=str(pins), stdin=subprocess.DEVNULL)
    return load(out_prediction), load(out_receipt)


def split_segments(requests):
    """Same contiguous-mode split as the frozen WP-0015 Carbon launcher."""
    segments = []
    for req in requests:
        if not segments or segments[-1][0] != req["mode"]:
            segments.append((req["mode"], [req]))
        else:
            segments[-1][1].append(req)
    return segments


def layout(run, requests):
    """Yield (segment index, mode, segment dir, request, document folder) for the segmented layout."""
    for si, (mode, reqs) in enumerate(split_segments(requests), 1):
        seg = Path(run) / f"segment-{si:02d}-{mode}"
        for i, req in enumerate(reqs, 1):
            yield si, mode, seg, req, seg / f"{i:02d}-{req['label']}-{req['mode']}"


def order_of(plans_record, plan_sha):
    hits = [o for o, b in plans_record["orders"].items() if b["sha256"] == plan_sha]
    return hits[0] if len(hits) == 1 else None


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
