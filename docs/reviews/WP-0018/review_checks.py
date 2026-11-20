"""WP-0018 /003 independent non-author checks (eld-rd-reviewer).

CPU-only replay over the admitted reviewer copies of the saved WP-0015 Windows predictions for
packets H and A. No OCR, WinRT call, GPU, rasterization, network or product code is used.
Written and frozen in Git before decisive execution; it imports no WP-0018 author source.

Subcommands
  phase1     custody/commitments, structural invariants, independent reproduction of the pinned
             adapter output from raw WinRT words, separate-process baseline scoring against the
             published counts and lookups, and the supplied constructed scorer control.
  witnesses  four frozen witness traces: H p2 t1 r2c1, A p60 t1 r2c2, H p1 line 2, H p2 line 2.
  paired     pages[*].tables=[] paired accounting. H/A execution is HELD: without
             --execute-held-paired only the constructed control is evaluated.
"""
import sys

sys.dont_write_bytecode = True

import argparse
import bisect
import copy
import datetime
import hashlib
import json
import os
import platform
import re
import subprocess
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
DEFAULT_DATA = REPO.parent / "wp0018-data" / "review"
ORIGINAL_ROOT = Path(os.environ.get("USERPROFILE", "")) / "eLedgerCare-Speed" / "WP-0015" / "review"
KIT = REPO / "docs" / "coordination" / "WP-0018" / "kit"

SCORER_SHA256 = "1ceb36fe922ef63ea8cd9b2dc2ff55b48abe1193bb818430ddb1531f364f4bf7"
SCORER_COMMIT = "7598bf4155452c4a1294b7421595009d39ea1bc9"
SCORER_PATH = "docs/evaluation/WP-0015/score.py"
COMMITMENTS_PATH = "docs/evaluation/WP-0015/commitments.json"
SUMMARY_COMMIT = "ce4206f20d63101f6344121eaaeeeb86d2ec85a0"
SUMMARY_PATH = "docs/reviews/WP-0015/evidence/scored-H-A.json"
RECEIPT_PATH = "docs/reviews/WP-0015/evidence/H-scored-receipt.json"
ADAPTER_COMMIT = "a0e738bc03e515999659dda09c5ee76d08fb37df"
KIT_ZIP_SHA256 = "2504bbb624bc17a437d84ec2bf6ea03ebf95a9dacdbaa691aa86e293a89fab28"

FAMILIES = {
    "H": dict(run="h-r1-ab", folder="04-h-windows", pages=4, named_files=14,
              inventory_commit="bd48af1a7f968b2231fe1d870a22c88f265ae347",
              inventory_path="docs/reviews/WP-0015/evidence/H-blind-inventory.json",
              inventory_blob="8e72acfc3f307da7e0f074edd937e61ce22f64ce",
              receipt_key="analysis-H-stage2/score-h-r1-ab-windows.json",
              gate=dict(correct_cells=15, reference_cells=20, unflagged_critical_errors=8, critical_values=19)),
    "A": dict(run="a-recovery-ab", folder="04-a-windows", pages=60, named_files=182,
              inventory_commit="ce4206f20d63101f6344121eaaeeeb86d2ec85a0",
              inventory_path="docs/reviews/WP-0015/evidence/A-recovery-blind-inventory.json",
              inventory_blob="156e53d20f448d2410e218b961ae6a1630e9a978",
              receipt_key=None,
              gate=dict(correct_cells=235, reference_cells=300, unflagged_critical_errors=94, critical_values=252)),
}
# Mapping of published "official" keys onto the frozen scorer result.
FAULT_KEYS = dict(missing="missing_page", duplicate="duplicate_page", out_of_range="out_of_range",
                  sequence_fault="page_sequence", incomplete="incomplete_page", unexpected_blank="unexpected_blank",
                  ink_on_blank="ink_on_blank", invalid_geometry="invalid_geometry")
WITNESSES = [
    dict(id="W1", family="H", page=2, kind="cell", table=1, row=2, col=1),
    dict(id="W2", family="A", page=60, kind="cell", table=1, row=2, col=2),
    dict(id="W3", family="H", page=1, kind="line", line=2),
    dict(id="W4", family="H", page=2, kind="line", line=2),
]


# ----------------------------------------------------------------------------- utilities
def sha256(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def git_bytes(*args):
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, check=True).stdout


def git_show(commit, path):
    return git_bytes("show", f"{commit}:{path}")


def utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def dump(path, obj):
    data = (json.dumps(obj, indent=1, ensure_ascii=True, allow_nan=False) + "\n").encode()
    Path(path).write_bytes(data)
    return sha256(data)


def adapter_bytes(obj):
    """Byte serialization used by the pinned WP-0015 formats.publish."""
    return (json.dumps(obj, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n").encode()


class Ledger:
    def __init__(self):
        self.checks = []

    def check(self, cid, scope, ok, observed=None, expected=None, note=None):
        self.checks.append(dict(id=cid, scope=scope, ok=bool(ok), observed=observed, expected=expected, note=note))
        return bool(ok)

    def summary(self):
        failed = [c for c in self.checks if not c["ok"]]
        return dict(total=len(self.checks), passed=len(self.checks) - len(failed),
                    failed=len(failed), failed_ids=[f"{c['id']}:{c['scope']}" for c in failed])


def load_scorer(path):
    """Execute exactly the hash-verified bytes; never writes a bytecode cache beside the copy."""
    data = Path(path).read_bytes()
    if sha256(data) != SCORER_SHA256:
        raise SystemExit("frozen scorer copy hash mismatch; refusing to import")
    mod = types.ModuleType("wp0015_frozen_score")
    mod.__file__ = str(path)
    exec(compile(data, str(path), "exec"), mod.__dict__)
    return mod


def run_scorer(score_path, truth, prediction, out, cwd):
    """Frozen scorer in a separate isolated interpreter process."""
    cmd = [sys.executable, "-I", str(score_path), str(truth), str(prediction), "--out", str(out)]
    began = utc()
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    return dict(command=cmd, cwd=str(cwd), began_utc=began, ended_utc=utc(), returncode=proc.returncode,
                stdout_chars=len(proc.stdout), stderr_tail=proc.stderr[-4000:],
                output_sha256=sha256(Path(out).read_bytes()) if Path(out).exists() else None)


def environment():
    return dict(python=sys.version, executable=sys.executable, platform=platform.platform(),
                script=str(Path(__file__).resolve()), script_sha256=sha256(Path(__file__).read_bytes()),
                repo_head=git_bytes("rev-parse", "HEAD").decode().strip(),
                repo_status_porcelain=git_bytes("status", "--porcelain").decode(),
                argv=sys.argv, started_utc=utc())


def fresh_dir(path):
    path = Path(path)
    if path.exists():
        raise SystemExit(f"output directory already exists; refusing to overwrite evidence: {path}")
    path.mkdir(parents=True)
    return path


# ----------------------------------------------------------------- independent adapter model
def project(bbox, points, width, height):
    # Pinned visual.layout: round(x*points[i%2]/(width,height)[i%2],3)
    return [round(x * points[i % 2] / (width, height)[i % 2], 3) for i, x in enumerate(bbox)]


def raw_words(raw):
    reader = raw["reader_result"]
    words = []
    for li, line in enumerate(reader["lines"]):
        for wi, word in enumerate(line["words"]):
            words.append(dict(text=word["text"], px=word["bbox"], line=li, word=wi,
                              bbox=project(word["bbox"], raw["points"], reader["width"], reader["height"])))
    return words


def adapter_layout(words, grids):
    """Independent re-implementation of pinned visual.layout (bisect_right == np.searchsorted right)."""
    assigned, tables, chunks, membership = set(), [], [], {}
    for gi, grid in enumerate(grids):
        xs, ys = grid["xs"], grid["ys"]
        if list(xs) != sorted(xs) or list(ys) != sorted(ys):
            raise ValueError("unsorted rule grid")
        cells = {}
        for i, w in enumerate(words):
            x = (w["bbox"][0] + w["bbox"][2]) / 2
            y = (w["bbox"][1] + w["bbox"][3]) / 2
            if xs[0] <= x < xs[-1] and ys[0] <= y < ys[-1]:
                col = bisect.bisect_right(xs, x) - 1
                row = bisect.bisect_right(ys, y) - 1
                cells.setdefault((row, col), []).append(i)
                assigned.add(i)
                membership.setdefault(i, []).append([gi, row, col])
        rows = []
        for r in range(len(ys) - 1):
            row = []
            for c in range(len(xs) - 1):
                ws = [words[i] for i in cells.get((r, c), [])]
                row.append(" ".join(w["text"] for w in sorted(ws, key=lambda v: (v["line"], v["bbox"][0]))))
            rows.append(row)
        tables.append(dict(bbox=[xs[0], ys[0], xs[-1], ys[-1]], rows=rows))
        chunks.append((ys[0], xs[0], " ".join(v for row in rows for v in row)))
    lines = {}
    for i, w in enumerate(words):
        if i not in assigned:
            lines.setdefault(w["line"], []).append(w)
    for ws in lines.values():
        boxes = [w["bbox"] for w in ws]
        box = [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)]
        chunks.append((box[1], box[0], " ".join(w["text"] for w in ws)))
    spans = [dict(text=w["text"], bbox=w["bbox"], flagged=False) for w in words]
    text = " ".join(" ".join(v[2] for v in sorted(chunks)).split())
    return dict(text=text, spans=spans, tables=tables), membership


def family_paths(data, fam):
    root = Path(data) / "inputs" / fam
    return dict(root=root, truth=root / "truth.json", pdf=root / "source.pdf", rasters=root / "rasters.json",
                rasters_input=root / "rasters.input.json", plan=root / "plan.json",
                historical=root / "historical-score.json", windows=root / "windows",
                prediction=root / "windows" / "prediction.json", timing=root / "windows" / "timing.json")


def page_file(paths, kind, n):
    return paths["windows"] / f"{kind}-{n:03d}.json"


# ---------------------------------------------------------------------------------- phase 1
def custody(ledger, data):
    admission_path = Path(data) / "admission.json"
    admission = load(admission_path)
    report = dict(admission_sha256=sha256(admission_path.read_bytes()), failures_field=admission.get("failures"))
    ledger.check("C1.0", "admission", admission.get("failures") in ({}, [], None), admission.get("failures"), {})
    control = Path(data) / "inputs" / "control"
    entries = sorted(p.name for p in control.iterdir())
    ledger.check("C1.1", "control/entry-set", entries == sorted(admission["controlSha256"]), entries,
                 sorted(admission["controlSha256"]), "no extra entries such as a bytecode cache")
    top = sorted(p.name for p in (Path(data) / "inputs").iterdir())
    ledger.check("C1.1", "inputs/entry-set", top == ["A", "H", "control"], top, ["A", "H", "control"])
    for name, want in admission["controlSha256"].items():
        got = sha256((control / name).read_bytes())
        ledger.check("C1.1", f"control/{name}", got == want, got, want)
    # Kit receipt and copies of the kit members retained in this repository at the starting pin.
    receipt = load(KIT / "receipt.json")
    ledger.check("C1.2", "kit/zip", receipt["zipSha256"] == KIT_ZIP_SHA256, receipt["zipSha256"], KIT_ZIP_SHA256)
    for name in ("archive-pins.json", "constructed-scorer-control.json"):
        repo_bytes, copy_bytes = (KIT / name).read_bytes(), (control / name).read_bytes()
        ledger.check("C1.2", f"kit/{name}", sha256(repo_bytes) == receipt["members"][name] and repo_bytes == copy_bytes,
                     sha256(copy_bytes), receipt["members"][name])
    blob = git_show(SCORER_COMMIT, SCORER_PATH)
    copy_bytes = (control / "score.py").read_bytes()
    ledger.check("C1.3", "score.py", blob == copy_bytes and sha256(blob) == SCORER_SHA256, sha256(copy_bytes), SCORER_SHA256,
                 f"{SCORER_COMMIT}:{SCORER_PATH}")
    summary_blob = git_show(SUMMARY_COMMIT, SUMMARY_PATH)
    ledger.check("C1.4", "scored-H-A.json", summary_blob == (control / "scored-H-A.json").read_bytes(),
                 sha256((control / "scored-H-A.json").read_bytes()), sha256(summary_blob), f"{SUMMARY_COMMIT}:{SUMMARY_PATH}")
    pins = load(control / "archive-pins.json")
    ledger.check("C1.4", "archive-pins/scorer", pins["scorer_sha256"] == SCORER_SHA256, pins["scorer_sha256"], SCORER_SHA256)
    commitments = json.loads(git_show(SCORER_COMMIT, COMMITMENTS_PATH))
    h_receipt = json.loads(git_show(SUMMARY_COMMIT, RECEIPT_PATH))
    originals = []
    for fam, spec in FAMILIES.items():
        paths = family_paths(data, fam)
        fam_adm = admission["families"][fam]
        ledger.check("C1.5", f"{fam}/admission-run", (fam_adm["run"], fam_adm["folder"], fam_adm["inventoryGitBlob"]) ==
                     (spec["run"], spec["folder"], spec["inventory_blob"]),
                     [fam_adm["run"], fam_adm["folder"], fam_adm["inventoryGitBlob"]],
                     [spec["run"], spec["folder"], spec["inventory_blob"]])
        records = fam_adm["records"]
        listed = set()
        for rec in records:
            target = Path(data) / "inputs" / rec["copy"]
            listed.add(rec["copy"])
            raw = target.read_bytes()
            ledger.check("C1.6", rec["copy"], sha256(raw) == rec["sha256"] and len(raw) == rec["bytes"],
                         [sha256(raw), len(raw)], [rec["sha256"], rec["bytes"]])
            original = ORIGINAL_ROOT / rec["source"]  # exact named path only; no enumeration
            try:
                obytes = original.read_bytes()
                originals.append(dict(copy=rec["copy"], original=str(original), sha256=sha256(obytes),
                                      equal_to_copy=obytes == raw))
                ledger.check("C1.7", f"original/{rec['source']}", obytes == raw, sha256(obytes), rec["sha256"])
            except OSError as exc:
                originals.append(dict(copy=rec["copy"], original=str(original), unavailable=repr(exc)))
                ledger.check("C1.7", f"original/{rec['source']}", False, "unavailable", rec["sha256"], repr(exc))
        present = {f"{fam}/{p.name}" for p in paths["root"].iterdir() if p.is_file()} | \
                  {f"{fam}/windows/{p.name}" for p in paths["windows"].iterdir()}
        ledger.check("C1.8", f"{fam}/copy-set", present == listed, sorted(present - listed), sorted(listed - present),
                     "copy directory equals admission record set")
        win_records = [r for r in records if r["copy"].startswith(f"{fam}/windows/")]
        ledger.check("C1.8", f"{fam}/named-file-count", len(win_records) == spec["named_files"] == fam_adm["namedWindowsFiles"],
                     len(win_records), spec["named_files"])
        # Commitments at the scorer custody commit.
        com = commitments["packets"][fam]
        for name in ("source.pdf", "truth.json", "rasters.json"):
            got = sha256((paths["root"] / name).read_bytes())
            ledger.check("C1.9", f"{fam}/commitments/{name}", got == com["files"][name], got, com["files"][name])
        ledger.check("C1.9", f"{fam}/commitments/pages+bytes",
                     (com["pages"], com["pdf_bytes"]) == (spec["pages"], paths["pdf"].stat().st_size),
                     [com["pages"], com["pdf_bytes"]], [spec["pages"], paths["pdf"].stat().st_size])
        for name, want in pins["families"][fam]["source_commitments_sha256"].items():
            got = sha256((paths["root"] / name).read_bytes())
            ledger.check("C1.9", f"{fam}/archive-pins/{name}", got == want, got, want)
        # Inventory blob identity and named-run file digests.
        inv_bytes = git_show(spec["inventory_commit"], spec["inventory_path"])
        blob_id = git_bytes("rev-parse", f"{spec['inventory_commit']}:{spec['inventory_path']}").decode().strip()
        ledger.check("C1.10", f"{fam}/inventory-blob", blob_id == spec["inventory_blob"], blob_id, spec["inventory_blob"])
        inventory = json.loads(inv_bytes)
        for name, want in inventory["input"].items():
            got = sha256((paths["root"] / name).read_bytes())
            ledger.check("C1.10", f"{fam}/inventory-input/{name}", got == want, got, want)
        runs = [r for r in inventory["runs"] if r["run"] == spec["run"]]
        ledger.check("C1.10", f"{fam}/inventory-run-unique", len(runs) == 1, len(runs), 1)
        run = runs[0]
        ledger.check("C1.10", f"{fam}/inventory-run-status", (run["returncode"], run["guard_reason"]) == (0, None),
                     [run["returncode"], run["guard_reason"]], [0, None])
        got = sha256(paths["plan"].read_bytes())
        ledger.check("C1.10", f"{fam}/plan", got == run["plan_sha256"], got, run["plan_sha256"])
        prefix = spec["folder"] + "/"
        inv_files = {k[len(prefix):]: v for k, v in run["files"].items() if k.startswith(prefix)}
        ledger.check("C1.10", f"{fam}/inventory-named-count", len(inv_files) == spec["named_files"], len(inv_files), spec["named_files"])
        copy_names = {p.name for p in paths["windows"].iterdir()}
        ledger.check("C1.10", f"{fam}/inventory-name-set", set(inv_files) == copy_names,
                     sorted(copy_names - set(inv_files)), sorted(set(inv_files) - copy_names))
        for name, want in sorted(inv_files.items()):
            got = sha256((paths["windows"] / name).read_bytes())
            ledger.check("C1.10", f"{fam}/inventory/{name}", got == want, got, want)
        pred_want = run["predictions"][prefix + "prediction.json"]
        ledger.check("C1.10", f"{fam}/inventory-prediction", sha256(paths["prediction"].read_bytes()) == pred_want,
                     sha256(paths["prediction"].read_bytes()), pred_want)
        for rel, want in pins["families"][fam]["relative_files_in_named_run_sha256"].items():
            got = sha256((paths["windows"] / rel.split("/", 1)[1]).read_bytes())
            ledger.check("C1.11", f"{fam}/archive-pins/{rel}", got == want, got, want)
        hist = sha256(paths["historical"].read_bytes())
        if spec["receipt_key"]:
            want = h_receipt["private_evidence_sha256"][spec["receipt_key"]]
            ledger.check("C1.12", f"{fam}/historical-score-receipt", hist == want, hist, want, f"{SUMMARY_COMMIT}:{RECEIPT_PATH}")
        else:
            report[f"{fam}_historical_score_git_pin"] = "none; compared below by full scorer reproduction only"
    report["originals"] = originals
    return report, pins


def structure(ledger, data, fam):
    spec, paths = FAMILIES[fam], family_paths(data, fam)
    truth, timing = load(paths["truth"]), load(paths["timing"])
    pred_bytes = paths["prediction"].read_bytes()
    pred = json.loads(pred_bytes.decode("utf-8"))
    rasters, rasters_in = load(paths["rasters"]), load(paths["rasters_input"])
    sha = truth["source_sha256"]
    n = spec["pages"]
    pdf_sha = sha256(paths["pdf"].read_bytes())
    ledger.check("C2.1", f"{fam}/source", sha == pdf_sha == pred["source_sha256"] == timing["request"]["sha256"],
                 [sha, pred["source_sha256"], timing["request"]["sha256"]], pdf_sha)
    ledger.check("C2.1", f"{fam}/pages", [p["page"] for p in pred["pages"]] == list(range(1, n + 1)) == [p["page"] for p in truth["pages"]],
                 [p["page"] for p in pred["pages"]], list(range(1, n + 1)))
    ledger.check("C2.2", f"{fam}/timing", (timing["status"], timing["complete_pages"], timing["request"]["pages"],
                                           timing["request"]["mode"], timing["prediction_sha256"]) ==
                 ("completed", n, n, "windows", sha256(pred_bytes)),
                 [timing["status"], timing["complete_pages"], timing["request"]["pages"], timing["request"]["mode"],
                  timing["prediction_sha256"]], ["completed", n, n, "windows", sha256(pred_bytes)])
    pin_rgb = [p["rgb_sha256"] for p in rasters["pages"]]
    ledger.check("C2.3", f"{fam}/rgb-pins", pin_rgb == [p["rgb_sha256"] for p in rasters_in["pages"]] == timing["request"]["rgb_sha256"],
                 None, None, "rasters.json == rasters.input.json == timing.request.rgb_sha256")
    reproduced_pages, rebuilt_pages = 0, []
    for i, page in enumerate(pred["pages"], 1):
        pf = page_file(paths, "page", i).read_bytes()
        raw, window = load(page_file(paths, "raw", i)), load(page_file(paths, "window", i))
        ledger.check("C2.4", f"{fam}/p{i}/page-file", json.loads(pf.decode("utf-8")) == page and pf == adapter_bytes(page),
                     None, None, "prediction.json page equals page-NNN.json and its pinned serialization")
        reader = raw["reader_result"]
        rp = rasters["pages"][i - 1]
        ledger.check("C2.5", f"{fam}/p{i}/raw-identity",
                     (raw["page"], raw["source_sha256"], raw["rgb_sha256"], raw["width"], raw["height"]) ==
                     (i, sha, pin_rgb[i - 1], rp["width_px"], rp["height_px"]) and
                     (reader["width"], reader["height"]) == (raw["width"], raw["height"]),
                     [raw["page"], raw["rgb_sha256"], raw["width"], raw["height"], reader["width"], reader["height"]],
                     [i, pin_rgb[i - 1], rp["width_px"], rp["height_px"]])
        words = raw_words(raw)
        ledger.check("C2.6", f"{fam}/p{i}/word-counts",
                     len(words) == raw["word_count"] == window["windows_ocr_words"] == len(page["spans"]),
                     [len(words), raw["word_count"], window["windows_ocr_words"], len(page["spans"])], None)
        ledger.check("C2.7", f"{fam}/p{i}/window", (window["first_page"], window["pages"], window["source_sha256"]) == (i, 1, sha),
                     [window["first_page"], window["pages"]], [i, 1])
        ledger.check("C2.8", f"{fam}/p{i}/state+flags", page["state"] == "complete" and
                     all(s.get("flagged") is False for s in page["spans"]), page["state"], "complete")
        rebuilt, _ = adapter_layout(words, window["rule_tables"])
        full = dict(source_sha256=sha, page=i, state="complete", **rebuilt)
        same = adapter_bytes(full) == pf
        reproduced_pages += same
        rebuilt_pages.append(full)
        detail = None
        if not same:
            detail = dict(text=full["text"] == page["text"], spans=full["spans"] == page["spans"],
                          tables=full["tables"] == page["tables"])
        ledger.check("C3.1", f"{fam}/p{i}/adapter-rebuild-bytes", same, detail, True,
                     "page-NNN bytes rebuilt from raw words, window rule_tables and pinned projection/rounding")
    whole = adapter_bytes(dict(source_sha256=sha, pages=rebuilt_pages))
    ledger.check("C3.2", f"{fam}/adapter-rebuild-prediction", whole == pred_bytes, sha256(whole), sha256(pred_bytes))
    return dict(pages=n, adapter_pages_reproduced=reproduced_pages, prediction_sha256=sha256(pred_bytes))


def official_view(result):
    counts = fault_counts(result)
    out = dict(complete=result["packet_complete"])
    c = result["counts"]
    for key in ("edits", "reference_chars", "correct_cells", "reference_cells", "extra_cells", "correct_lines",
                "reference_lines", "critical_values", "critical_errors", "unflagged_critical_errors",
                "flagged_critical", "wrong_source"):
        out[key] = c[key]
    out["cer"] = round(c["cer"], 4) if c["cer"] is not None else None
    out["cell_accuracy"] = round(c["cell_accuracy"], 4) if c["cell_accuracy"] is not None else None
    for key, issue in FAULT_KEYS.items():
        out[key] = counts.get(issue, 0)
    return out


def fault_counts(result):
    counts = {}
    for f in result["faults"]:
        counts[f["issue"]] = counts.get(f["issue"], 0) + 1
    return counts


def baseline(ledger, data, fam, out, score_path, pins, summary):
    spec, paths = FAMILIES[fam], family_paths(data, fam)
    runs = []
    for k in (1, 2):
        target = out / f"baseline-{fam}-run{k}.json"
        runs.append(run_scorer(score_path, paths["truth"], paths["prediction"], target, out))
    ok_proc = all(r["returncode"] == 0 for r in runs)
    ledger.check("C4.0", f"{fam}/scorer-process", ok_proc, [r["returncode"] for r in runs], [0, 0])
    if not ok_proc:
        return dict(runs=runs, gate=False)
    b1, b2 = (out / f"baseline-{fam}-run{k}.json" for k in (1, 2))
    ledger.check("C4.1", f"{fam}/repeat-bytes", b1.read_bytes() == b2.read_bytes(), runs[1]["output_sha256"], runs[0]["output_sha256"])
    hist = paths["historical"].read_bytes()
    result = load(b1)
    ledger.check("C4.2", f"{fam}/historical-bytes", b1.read_bytes() == hist, runs[0]["output_sha256"], sha256(hist),
                 "separate-process result equals retained historical score copy byte for byte")
    ledger.check("C4.2", f"{fam}/historical-parsed", result == json.loads(hist.decode("utf-8")), None, None)
    published = pins["families"][fam]["published_windows"]
    c = result["counts"]
    pairs = dict(matching_reference_cells=c["correct_cells"], reference_cells=c["reference_cells"],
                 extra_cells=c["extra_cells"], matching_reference_lines=c["correct_lines"],
                 reference_lines=c["reference_lines"], unflagged_critical_errors=c["unflagged_critical_errors"],
                 reference_criticals=c["critical_values"])
    for key, got in pairs.items():
        ledger.check("C4.3", f"{fam}/archive-pins/{key}", got == published[key], got, published[key])
    official = summary[fam]["runs"][spec["run"]]["windows"]["official"]
    view = official_view(result)
    for key, want in official.items():
        ledger.check("C4.4", f"{fam}/published-official/{key}", view.get(key) == want, view.get(key), want)
    ledger.check("C4.4", f"{fam}/published-prediction-sha", summary[fam]["runs"][spec["run"]]["windows"]["prediction_sha256"] ==
                 sha256(paths["prediction"].read_bytes()), None, None)
    gate = {k: c[k] for k in spec["gate"]}
    gate_ok = gate == spec["gate"]
    ledger.check("C4.5", f"{fam}/assignment-gate", gate_ok, gate, spec["gate"],
                 "assignment step 1: stop the affected pair if this fails")
    modes = dict(grid=0, span_fallback=0)
    for p in result["pages"]:
        for cell in p["cells"]:
            modes["grid" if cell["reported_table_bbox"] is not None else "span_fallback"] += 1
    return dict(runs=runs, gate=gate_ok, counts=c, packet_complete=result["packet_complete"],
                faults=result["faults"], baseline_cell_modes=modes, published_supplementary_unreproduced=dict(
                    missing_numeric_tokens_supplementary=published.get("missing_numeric_tokens_supplementary"),
                    reason="definition belongs to an unadmitted private WP-0015 sensitivity tool; not reproduced"))


def lookups(ledger, data, fam, out, summary, scorer):
    paths = family_paths(data, fam)
    truth, rasters = load(paths["truth"]), load(paths["rasters"])
    result = load(out / f"baseline-{fam}-run1.json")
    look = summary[fam]["source_linked_lookup"]
    pred = json.loads(paths["prediction"].read_bytes().decode("utf-8"))
    n = len(truth["pages"])
    ledger.check("C5.0", f"{fam}/lookup-header",
                 (look["source_pdf_sha256"], look["final_page"], look["final_page_has_table"], look["late_table_page"]) ==
                 (truth["source_sha256"], n, bool(truth["pages"][-1]["tables"]),
                  max(p["page"] for p in truth["pages"] if p["tables"])),
                 [look["source_pdf_sha256"], look["final_page"], look["final_page_has_table"], look["late_table_page"]], None)
    checked = []
    for key, entry in look["pages"].items():
        num = int(key)
        arm = entry["arms"]["windows"]
        raw = load(page_file(paths, "raw", num))
        page = pred["pages"][num - 1]
        rec = result["pages"][num - 1]
        tp = truth["pages"][num - 1]
        pin = rasters["pages"][num - 1]["rgb_sha256"]
        ledger.check("C5.1", f"{fam}/p{num}/identity",
                     (entry["rgb_pin"], entry["truth_lines"], entry["truth_tables"], arm["raw_page"], arm["raw_source_sha256"],
                      arm["raw_rgb_sha256"], arm["rgb_matches_pin"], arm["source_matches"]) ==
                     (pin, len(tp["lines"]), len(tp["tables"]), raw["page"], raw["source_sha256"], raw["rgb_sha256"],
                      raw["rgb_sha256"] == pin, raw["source_sha256"] == truth["source_sha256"]), None, None)
        ledger.check("C5.2", f"{fam}/p{num}/prediction-shape",
                     (arm["predicted_spans"], arm["predicted_tables"], arm["predicted_table_bboxes"]) ==
                     (len(page["spans"]), len(page["tables"]), [t["bbox"] for t in page["tables"]]),
                     [len(page["spans"]), len(page["tables"])], [arm["predicted_spans"], arm["predicted_tables"]])
        cl = arm.get("critical_line")
        if cl:
            line = next(x for x in rec["lines"] if x["at"] == cl["at"])
            crit = next(x for x in rec["critical"] if x["at"] == cl["at"])
            got = dict(at=line["at"], expected=crit["expected"], observed=line["observed"], correct=crit["correct"],
                       reference_bbox=line["reference_bbox"], reported_span_boxes=line["reported_span_boxes"])
            ledger.check("C5.3", f"{fam}/p{num}/critical_line", got == cl, got, cl)
            checked.append(cl["at"])
        cc = arm.get("critical_cell")
        if cc:
            cell = next(x for x in rec["cells"] if x["at"] == cc["at"])
            m = re.fullmatch(r"page/(\d+)/table/(\d+)/row/(\d+)/col/(\d+)", cc["at"])
            ti, ri, ci = (int(m.group(k)) for k in (2, 3, 4))
            region = tp["tables"][ti - 1]["rows"][ri - 1][ci - 1]["bbox"]
            centred = [dict(text=s["text"], bbox=s["bbox"]) for s in page["spans"]
                       if region[0] <= (s["bbox"][0] + s["bbox"][2]) / 2 < region[2] and
                       region[1] <= (s["bbox"][1] + s["bbox"][3]) / 2 < region[3]]
            in_cell = [dict(text=s["text"], bbox=s["bbox"]) for s in page["spans"] if scorer.in_cell(s["bbox"], region)]
            got = dict(at=cell["at"], row=ri, col=ci, expected=cell["expected"], observed=cell["observed"],
                       correct=cell["correct"], reference_bbox=cell["reference_bbox"],
                       reported_table_bbox=cell["reported_table_bbox"], spans_centred_in_cell=centred)
            ledger.check("C5.4", f"{fam}/p{num}/critical_cell", got == cc, got, cc)
            ledger.check("C5.5", f"{fam}/p{num}/centred-vs-scorer-in_cell", centred == in_cell, in_cell, centred,
                         "published centre-only membership equals the frozen scorer in_cell predicate here")
            checked.append(cc["at"])
    return dict(lookup_locations=checked)


def constructed_control(ledger, control_path, scorer):
    ctl = load(control_path)
    ref, pred, sha = ctl["reference_page"], ctl["prediction_page"], ctl["source_sha256_placeholder"]
    before = scorer.layout(copy.deepcopy(ref), copy.deepcopy(pred), sha)
    stripped = copy.deepcopy(pred)
    stripped["tables"] = []
    after = scorer.layout(copy.deepcopy(ref), stripped, sha)
    inv = prediction_page_invariants(pred, stripped)
    ledger.check("C6.0", "control/prediction-invariants", not inv, inv, [])

    def view(res):
        return dict(cells=[[c["at"], c["expected"], c["observed"], c["correct"]] for c in res["cells"]],
                    lines=[[l["at"], l["observed"], l["correct"]] for l in res["lines"]],
                    extra_cells=res["extra_cells"], faults=res["faults"])
    for name, res in (("before", before), ("after", after)):
        got = view(res)
        ledger.check("C6.1", f"control/{name}", got == ctl[name], got, ctl[name])
    ledger.check("C6.2", "control/lines-identical", before["lines"] == after["lines"], None, None)
    line_crit = lambda res: [c for c in res["critical"] if "/line/" in c["at"]]
    ledger.check("C6.2", "control/critical-lines-identical", line_crit(before) == line_crit(after), None, None)
    rows = [classify_cell(b, a, None, None) for b, a in zip(before["cells"], after["cells"])]
    tally = tally_cells(rows)
    ledger.check("C6.3", "control/gain-loss", (tally["gain"], tally["loss"], tally["net"]) == (1, 1, 0),
                 [tally["gain"], tally["loss"], tally["net"]], [1, 1, 0],
                 "method control: one gain and one loss at zero net change")
    return dict(before=view(before), after=view(after), accounting=rows, tally=tally)


def cmd_phase1(args):
    out = fresh_dir(args.out)
    env = environment()
    ledger = Ledger()
    data = Path(args.data)
    score_path = data / "inputs" / "control" / "score.py"
    scorer = load_scorer(score_path)
    summary = load(data / "inputs" / "control" / "scored-H-A.json")
    report = dict(kind="WP-0018/003 reviewer phase1", environment=env)
    report["custody"], pins = custody(ledger, data)
    for fam in FAMILIES:
        report[f"structure_{fam}"] = structure(ledger, data, fam)
        report[f"baseline_{fam}"] = baseline(ledger, data, fam, out, score_path, pins, summary)
        report[f"lookups_{fam}"] = lookups(ledger, data, fam, out, summary, scorer)
    report["constructed_control"] = constructed_control(ledger, data / "inputs" / "control" / "constructed-scorer-control.json", scorer)
    report["checks"] = ledger.checks
    report["summary"] = ledger.summary()
    report["ended_utc"] = utc()
    digest = dump(out / "phase1.json", report)
    print(json.dumps(dict(out=str(out / "phase1.json"), sha256=digest, **report["summary"]), indent=1))
    return 0 if not report["summary"]["failed"] else 1


# ---------------------------------------------------------------------------------- paired
def prediction_page_invariants(before, after):
    issues = []
    if set(before) - {"tables"} != set(after) - {"tables"}:
        issues.append("page keys differ")
    for key in before:
        if key == "tables":
            continue
        if before.get(key) != after.get(key):
            issues.append(f"field {key} changed")
    if after.get("tables") != []:
        issues.append("tables not emptied")
    return issues


def prediction_invariants(before, after):
    issues = []
    for key in set(before) | set(after):
        if key != "pages" and before.get(key) != after.get(key):
            issues.append(f"document field {key} changed")
    if [p.get("page") for p in before["pages"]] != [p.get("page") for p in after["pages"]]:
        issues.append("page order changed")
    for b, a in zip(before["pages"], after["pages"]):
        issues += [f"page {b.get('page')}: {x}" for x in prediction_page_invariants(b, a)]
    return issues


def classify_cell(b, a, grid_ptr, span_ptrs):
    assert (b["at"], b["expected"]) == (a["at"], a["expected"])
    klass = {(False, True): "gain", (True, False): "loss", (True, True): "unchanged_right",
             (False, False): "unchanged_wrong"}[(bool(b["correct"]), bool(a["correct"]))]
    mode = lambda c: "grid" if c.get("reported_table_bbox") is not None else "span_fallback"
    return dict(at=b["at"], expected=b["expected"], klass=klass,
                before=dict(observed=b["observed"], correct=b["correct"], flagged=b["flagged"], mode=mode(b),
                            grid_pointer=grid_ptr),
                after=dict(observed=a["observed"], correct=a["correct"], flagged=a["flagged"], mode=mode(a),
                           span_pointers=span_ptrs),
                already_fallback=mode(b) == "span_fallback",
                unavailable_before=b["observed"] is None, unavailable_after=a["observed"] is None)


def tally_cells(rows):
    out = dict(gain=0, loss=0, unchanged_right=0, unchanged_wrong=0)
    for r in rows:
        out[r["klass"]] += 1
    out["net"] = out["gain"] - out["loss"]
    out["unavailable_before"] = sum(r["unavailable_before"] for r in rows)
    out["unavailable_after"] = sum(r["unavailable_after"] for r in rows)
    out["already_fallback"] = sum(r["already_fallback"] for r in rows)
    for scope in ("grid", "span_fallback"):
        sub = [r for r in rows if r["before"]["mode"] == scope]
        out[f"by_before_mode/{scope}"] = {k: sum(r["klass"] == k for r in sub)
                                          for k in ("gain", "loss", "unchanged_right", "unchanged_wrong")}
    return out


def scorer_span_cells(scorer, ref, page, sha):
    """Replicates the frozen scorer's first-cell span assignment, returning span indices per cell."""
    out = {}
    num, width, height = ref["page"], ref["width"], ref["height"]
    for si, s in enumerate(page.get("spans", [])):
        if s.get("source_sha256", sha) != sha or s.get("page", num) != num or not scorer.valid_box(s.get("bbox"), width, height):
            continue
        done = False
        for ti, table in enumerate(ref["tables"]):
            for ri, row in enumerate(table["rows"]):
                for ci, cell in enumerate(row):
                    if scorer.in_cell(s["bbox"], cell["bbox"]):
                        out.setdefault((ti, ri, ci), []).append(si)
                        done = True
                        break
                if done:
                    break
            if done:
                break
    return out


def score_invariants(sb, sa):
    issues = []
    for key in ("family", "source_sha256", "packet_complete", "expected_pages", "output_pages", "observed_order"):
        if sb[key] != sa[key]:
            issues.append(f"{key} changed")
    for key in ("edits", "reference_chars", "cer", "correct_lines", "reference_lines", "wrong_source"):
        if sb["counts"][key] != sa["counts"][key]:
            issues.append(f"counts.{key} changed")
    nontable = lambda faults: [f for f in faults if not str(f.get("at", "")).startswith("tables/")]
    if nontable(sb["faults"]) != nontable(sa["faults"]):
        issues.append("non-table faults changed")
    for pb, pa in zip(sb["pages"], sa["pages"]):
        for key in ("page", "state", "reference_chars", "edit_distance", "lines"):
            if pb[key] != pa[key]:
                issues.append(f"page {pb['page']}: {key} changed")
        lc = lambda p: [c for c in p["critical"] if "/line/" in c["at"]]
        if lc(pb) != lc(pa):
            issues.append(f"page {pb['page']}: critical line verdicts changed")
        if [c["at"] for c in pb["cells"]] != [c["at"] for c in pa["cells"]]:
            issues.append(f"page {pb['page']}: cell locations changed")
    return issues


def paired_family(ledger, data, fam, out, score_path, scorer):
    paths = family_paths(data, fam)
    pred_bytes = paths["prediction"].read_bytes()
    before_pred = json.loads(pred_bytes.decode("utf-8"))
    truth = load(paths["truth"])
    ledger.check("P0", f"{fam}/tables-key-present", all("tables" in p for p in before_pred["pages"]), None, None)
    after_pred = copy.deepcopy(before_pred)
    for p in after_pred["pages"]:
        p["tables"] = []
    inv = prediction_invariants(before_pred, after_pred)
    ledger.check("P1", f"{fam}/prediction-invariants", not inv, inv, [])
    stripped = out / f"{fam}-prediction-tables-empty.json"
    stripped.write_bytes(adapter_bytes(after_pred))
    before_out, after_out = out / f"paired-{fam}-before.json", out / f"paired-{fam}-after.json"
    runs = [run_scorer(score_path, paths["truth"], paths["prediction"], before_out, out),
            run_scorer(score_path, paths["truth"], stripped, after_out, out)]
    ledger.check("P2", f"{fam}/scorer-process", all(r["returncode"] == 0 for r in runs), [r["returncode"] for r in runs], [0, 0])
    ledger.check("P2", f"{fam}/before-equals-historical", before_out.read_bytes() == paths["historical"].read_bytes(), None, None)
    sb, sa = load(before_out), load(after_out)
    sinv = score_invariants(sb, sa)
    ledger.check("P3", f"{fam}/score-invariants", not sinv, sinv, [])
    rows, extra = [], []
    pred_sha = sha256(pred_bytes)
    for pi, (pb, pa) in enumerate(zip(sb["pages"], sa["pages"])):
        ref = truth["pages"][pi]
        page = before_pred["pages"][pi]
        spans_after = scorer_span_cells(scorer, ref, after_pred["pages"][pi], truth["source_sha256"])
        crit_at = {c["at"] for c in pb["critical"]}
        idx = 0
        for ti, table in enumerate(ref["tables"]):
            for ri, row in enumerate(table["rows"]):
                for ci, _ in enumerate(row):
                    b, a = pb["cells"][idx], pa["cells"][idx]
                    idx += 1
                    grid_ptr = None
                    if b["reported_table_bbox"] is not None:
                        ks = [k for k, t in enumerate(page["tables"]) if t["bbox"] == b["reported_table_bbox"]]
                        grid_ptr = [dict(prediction_sha256=pred_sha, pointer=f"/pages/{pi}/tables/{k}/rows/{ri}/{ci}",
                                         present=ri < len(page["tables"][k]["rows"]) and ci < len(page["tables"][k]["rows"][ri]))
                                    for k in ks]
                    span_ptrs = [dict(prediction_sha256=pred_sha, pointer=f"/pages/{pi}/spans/{si}",
                                      text=page["spans"][si]["text"]) for si in spans_after.get((ti, ri, ci), [])]
                    row_rec = classify_cell(b, a, grid_ptr, span_ptrs)
                    row_rec["critical"] = b["at"] in crit_at
                    rows.append(row_rec)
        extra.append(dict(page=pb["page"], before=pb["extra_cells"], after=pa["extra_cells"]))
    tally = tally_cells(rows)
    tally["critical_only"] = tally_cells([r for r in rows if r["critical"]])
    tally["extra_cells_before"] = sb["counts"]["extra_cells"]
    tally["extra_cells_after"] = sa["counts"]["extra_cells"]
    for key in ("correct_cells", "reference_cells", "cell_accuracy", "unflagged_critical_errors", "critical_errors"):
        tally[f"{key}_before"], tally[f"{key}_after"] = sb["counts"][key], sa["counts"][key]
    ledger.check("P4", f"{fam}/tally-consistency",
                 sb["counts"]["correct_cells"] + tally["gain"] - tally["loss"] == sa["counts"]["correct_cells"],
                 None, None)
    return dict(runs=runs, prediction_invariant_issues=inv, score_invariant_issues=sinv, tally=tally,
                cells=rows, extra_by_page=extra, stripped_sha256=sha256(stripped.read_bytes()))


def cmd_paired(args):
    out = fresh_dir(args.out)
    env = environment()
    ledger = Ledger()
    data = Path(args.data)
    score_path = data / "inputs" / "control" / "score.py"
    scorer = load_scorer(score_path)
    report = dict(kind="WP-0018/003 reviewer paired", environment=env)
    report["constructed_control"] = constructed_control(ledger, data / "inputs" / "control" / "constructed-scorer-control.json", scorer)
    if args.execute_held_paired:
        for fam in FAMILIES:
            report[f"paired_{fam}"] = paired_family(ledger, data, fam, out, score_path, scorer)
    else:
        report["held"] = "H/A tables=[] execution held pending a separate coordinator instruction"
    report["checks"] = ledger.checks
    report["summary"] = ledger.summary()
    report["ended_utc"] = utc()
    digest = dump(out / "paired.json", report)
    print(json.dumps(dict(out=str(out / "paired.json"), sha256=digest, held=not args.execute_held_paired,
                          **report["summary"]), indent=1))
    return 0 if not report["summary"]["failed"] else 1


# -------------------------------------------------------------------------------- witnesses
def align(a, b):
    """One minimal Levenshtein alignment of expected a to observed b (diagonal preferred)."""
    n, m = len(a), len(b)
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        d[i][0] = i
    for j in range(m + 1):
        d[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] != b[j - 1]))
    ops, i, j = [], n, m
    while i or j:
        if i and j and d[i][j] == d[i - 1][j - 1] + (a[i - 1] != b[j - 1]):
            if a[i - 1] != b[j - 1]:
                ops.append(dict(op="substitute", expected=a[i - 1], observed=b[j - 1], expected_index=i - 1))
            i, j = i - 1, j - 1
        elif i and d[i][j] == d[i - 1][j] + 1:
            ops.append(dict(op="delete", expected=a[i - 1], observed=None, expected_index=i - 1))
            i -= 1
        else:
            ops.append(dict(op="insert", expected=None, observed=b[j - 1], expected_index=i))
            j -= 1
    return dict(distance=d[n][m], ops=list(reversed(ops)))


def stage_divergence(expected, stages, norm):
    first = None
    rows = []
    for name, value in stages:
        same = value is not None and norm(value) == norm(expected)
        rows.append(dict(stage=name, value=value, equals_expected=same))
        if not same and first is None:
            first = name
    return rows, first


def witness_trace(w, data, scorer, baseline_paths):
    fam, num = w["family"], w["page"]
    paths = family_paths(data, fam)
    truth = load(paths["truth"])
    pred_bytes = paths["prediction"].read_bytes()
    pred = json.loads(pred_bytes.decode("utf-8"))
    raw_path, page_path, win_path = (page_file(paths, k, num) for k in ("raw", "page", "window"))
    raw, page, window = load(raw_path), load(page_path), load(win_path)
    result = load(baseline_paths[fam])
    ref = truth["pages"][num - 1]
    sha = truth["source_sha256"]
    words = raw_words(raw)
    rebuilt, membership = adapter_layout(words, window["rule_tables"])
    files = {name: dict(path=str(p), sha256=sha256(Path(p).read_bytes())) for name, p in
             (("truth", paths["truth"]), ("raw", raw_path), ("page", page_path), ("window", win_path),
              ("prediction", paths["prediction"]), ("baseline_score", baseline_paths[fam]))}
    reader = raw["reader_result"]
    trace = dict(id=w["id"], witness=w, files=files,
                 raster=dict(rgb_sha256=raw["rgb_sha256"], width_px=raw["width"], height_px=raw["height"],
                             points=raw["points"], winrt_bitmap=[reader["width"], reader["height"]], angle=reader["angle"],
                             scale=[raw["points"][0] / reader["width"], raw["points"][1] / reader["height"]]))
    span_rec = lambda k: dict(span_pointer=f"/spans/{k}", prediction_pointer=f"/pages/{num-1}/spans/{k}",
                              stored=page["spans"][k], projected=words[k]["bbox"],
                              projection_equal=page["spans"][k]["bbox"] == words[k]["bbox"] and page["spans"][k]["text"] == words[k]["text"],
                              raw_pointer=f"/reader_result/lines/{words[k]['line']}/words/{words[k]['word']}",
                              winrt_line_ordinal=words[k]["line"], winrt_word_ordinal=words[k]["word"],
                              text=words[k]["text"], px_bbox=words[k]["px"], adapter_grid_membership=membership.get(k, []))
    raw_line = lambda li: dict(raw_pointer=f"/reader_result/lines/{li}", ordinal=li, text=reader["lines"][li]["text"],
                               words=[dict(text=x["text"], px_bbox=x["bbox"]) for x in reader["lines"][li]["words"]])
    pi = num - 1
    if w["kind"] == "cell":
        ti, ri, ci = w["table"] - 1, w["row"] - 1, w["col"] - 1
        cell = ref["tables"][ti]["rows"][ri][ci]
        region = cell["bbox"]
        at = f"page/{num}/table/{ti+1}/row/{ri+1}/col/{ci+1}"
        trace["reference"] = dict(at=at, truth_pointer=f"/pages/{pi}/tables/{ti}/rows/{ri}/{ci}", text=cell["text"],
                                  bbox=region, critical=cell["critical"], table_bbox=ref["tables"][ti]["bbox"])
        centred = [k for k, x in enumerate(words) if region[0] <= (x["bbox"][0] + x["bbox"][2]) / 2 < region[2]
                   and region[1] <= (x["bbox"][1] + x["bbox"][3]) / 2 < region[3]]
        incell = [k for k, s in enumerate(page["spans"]) if scorer.in_cell(s["bbox"], region)]
        scorer_cells = scorer_span_cells(scorer, ref, page, sha)
        scorer_assigned = scorer_cells.get((ti, ri, ci), [])
        ious = [dict(predicted_table_index=k, bbox=t["bbox"], iou=scorer.iou(ref["tables"][ti]["bbox"], t["bbox"]))
                for k, t in enumerate(page["tables"])]
        matched = [x for x in ious if x["iou"] >= 0.5]
        grids = []
        for g, (grid, table) in enumerate(zip(window["rule_tables"], page["tables"])):
            gwords = [k for k, mem in membership.items() if [g, ri, ci] in mem]
            grids.append(dict(window_pointer=f"/rule_tables/{g}", xs=grid["xs"], ys=grid["ys"],
                              page_table_pointer=f"/tables/{g}", table_bbox=table["bbox"],
                              emitted_row=table["rows"][ri] if ri < len(table["rows"]) else None,
                              emitted_cell_pointer=f"/pages/{pi}/tables/{g}/rows/{ri}/{ci}",
                              emitted_cell=table["rows"][ri][ci] if ri < len(table["rows"]) and ci < len(table["rows"][ri]) else None,
                              rebuilt_cell=rebuilt["tables"][g]["rows"][ri][ci] if ri < len(rebuilt["tables"][g]["rows"]) else None,
                              prediction_cell=(pred["pages"][pi]["tables"][g]["rows"][ri][ci]
                                               if ri < len(table["rows"]) and ci < len(table["rows"][ri]) else None),
                              adapter_words_in_cell=gwords,
                              adapter_join_order=[words[k]["text"] for k in sorted(gwords, key=lambda k: (words[k]["line"], words[k]["bbox"][0]))]))
        idx = next(k for k, c in enumerate(result["pages"][pi]["cells"]) if c["at"] == at)
        scored = result["pages"][pi]["cells"][idx]
        cidx = [k for k, c in enumerate(result["pages"][pi]["critical"]) if c["at"] == at]
        involved = sorted(set(centred) | set(incell) | {k for gg in grids for k in gg["adapter_words_in_cell"]})
        trace["words"] = [dict(**span_rec(k), centre_in_reference_cell=k in centred, scorer_in_cell=k in incell,
                               scorer_first_cell_assignment=k in scorer_assigned) for k in involved]
        trace["winrt_lines"] = [raw_line(li) for li in sorted({words[k]["line"] for k in involved})]
        trace["grid"] = grids
        trace["table_match"] = dict(candidates=ious, matched=matched, threshold=0.5)
        trace["scored_selection"] = dict(score_pointer=f"/pages/{pi}/cells/{idx}",
                                         critical_pointers=[f"/pages/{pi}/critical/{k}" for k in cidx], record=scored,
                                         mechanism="grid" if scored["reported_table_bbox"] is not None else "span_fallback")
        trace["scorer_span_geometry"] = dict(
            note="frozen scorer in_cell/first-cell assignment evaluated on stored spans for this one reference cell; no tables=[] scoring run",
            spans=[dict(pointer=f"/pages/{pi}/spans/{k}", text=page["spans"][k]["text"]) for k in scorer_assigned],
            joined_in_scorer_order=scorer.joined([page["spans"][k] for k in scorer_assigned])[0])
        raw_text = " ".join(words[k]["text"] for k in involved) if involved else None
        emitted = grids[matched[0]["predicted_table_index"]]["emitted_cell"] if matched else None
        stages = [("winrt_raw_words", raw_text), ("adapter_spans", " ".join(page["spans"][k]["text"] for k in involved) if involved else None),
                  ("adapter_emitted_grid_cell", emitted), ("scored_observed", scored["observed"])]
    else:
        li = w["line"] - 1
        line = ref["lines"][li]
        at = f"page/{num}/line/{li+1}"
        trace["reference"] = dict(at=at, truth_pointer=f"/pages/{pi}/lines/{li}", text=line["text"], bbox=line["bbox"],
                                  critical=line["critical"])
        incell_any = set()
        for t in ref["tables"]:
            for row in t["rows"]:
                for c in row:
                    incell_any |= {k for k, s in enumerate(page["spans"]) if scorer.in_cell(s["bbox"], c["bbox"])}
        assigned = []
        eligible_rows = []
        for k, s in enumerate(page["spans"]):
            if k in incell_any:
                continue
            elig = [j for j, ln in enumerate(ref["lines"]) if scorer.on_line(s["bbox"], ln["bbox"])]
            if elig:
                centre = lambda b: (b[1] + b[3]) / 2
                pick = min(elig, key=lambda j: abs(centre(ref["lines"][j]["bbox"]) - centre(s["bbox"])))
                if li in elig:
                    eligible_rows.append(dict(span=k, eligible_lines=[j + 1 for j in elig], chosen_line=pick + 1))
                if pick == li:
                    assigned.append(k)
        scored_idx = next(k for k, x in enumerate(result["pages"][pi]["lines"]) if x["at"] == at)
        scored = result["pages"][pi]["lines"][scored_idx]
        cidx = [k for k, c in enumerate(result["pages"][pi]["critical"]) if c["at"] == at]
        crit = result["pages"][pi]["critical"][cidx[0]] if cidx else None
        winrt_lines = sorted({words[k]["line"] for k in assigned})
        trace["words"] = [span_rec(k) for k in assigned]
        trace["winrt_lines"] = [raw_line(x) for x in winrt_lines]
        trace["line_assignment"] = dict(eligible=eligible_rows, assigned_spans=assigned,
                                        scorer_join_order=[s["text"] for s in sorted([page["spans"][k] for k in assigned],
                                                                                     key=lambda s: (s["bbox"][0], s["bbox"][1]))],
                                        joined=scorer.joined([page["spans"][k] for k in assigned])[0])
        if line["critical"]:
            wanted = line["critical"]
            pattern = r"(?<![\w.,+-])" + re.escape(wanted) + r"(?![\w+-]|[.,]\d)"
            numbered = lambda s: [t for t in re.findall(r"[+-]?[\w]+(?:[.,-][\w]+)*", s) if any(c.isdigit() for c in t)]
            obs = scored["observed"]
            trace["critical_check"] = dict(token=wanted, pattern=pattern,
                                           token_found=obs is not None and re.search(pattern, obs) is not None,
                                           numbered_expected=numbered(line["text"]),
                                           numbered_observed=numbered(obs) if obs is not None else None,
                                           record=crit, critical_pointer=f"/pages/{pi}/critical/{cidx[0]}" if cidx else None)
        trace["page_text_contains_winrt_line"] = [reader["lines"][x]["text"] in page["text"] for x in winrt_lines]
        trace["scored_selection"] = dict(score_pointer=f"/pages/{pi}/lines/{scored_idx}", record=scored,
                                         mechanism="scorer line assembly from adapter spans (adapter emits no line objects)")
        raw_text = " ".join(reader["lines"][x]["text"] for x in winrt_lines) if winrt_lines else None
        stages = [("winrt_raw_line_text", raw_text),
                  ("adapter_spans_in_scorer_order", trace["line_assignment"]["joined"]),
                  ("scored_observed", scored["observed"])]
    expected = trace["reference"]["text"]
    trace["stages"], trace["first_divergent_stage"] = stage_divergence(expected, stages, scorer.norm)
    trace["alignments"] = {name: align(scorer.norm(expected), scorer.norm(v)) for name, v in stages if v is not None}
    trace["flags"] = dict(all_spans_unflagged=all(s["flagged"] is False for s in page["spans"]),
                          winrt_confidence_exposed=False)
    trace["cannot_distinguish"] = [
        "No raster was re-rendered or re-recognized; source pixel appearance and WinRT internals are not observed.",
        "WinRT exposes no per-word confidence here and the adapter sets every span flagged=false, so flags cannot separate these cases.",
        "Window rule_tables came from the original raster analysis and are taken as recorded; only their use downstream is reproduced.",
    ]
    return trace


def cmd_witnesses(args):
    out = fresh_dir(args.out)
    env = environment()
    data = Path(args.data)
    score_path = data / "inputs" / "control" / "score.py"
    scorer = load_scorer(score_path)
    runs, baseline_paths = {}, {}
    for fam in ("H", "A"):
        paths = family_paths(data, fam)
        target = out / f"baseline-{fam}.json"
        runs[fam] = run_scorer(score_path, paths["truth"], paths["prediction"], target, out)
        if runs[fam]["returncode"] != 0:
            raise SystemExit(f"baseline scorer failed for {fam}")
        baseline_paths[fam] = target
    index = dict(kind="WP-0018/003 reviewer witness traces", environment=env, baseline_runs=runs, traces=[])
    for w in WITNESSES:
        trace = witness_trace(w, data, scorer, baseline_paths)
        digest = dump(out / f"witness-{w['id']}.json", trace)
        index["traces"].append(dict(id=w["id"], file=f"witness-{w['id']}.json", sha256=digest,
                                    first_divergent_stage=trace["first_divergent_stage"]))
    index["ended_utc"] = utc()
    digest = dump(out / "witnesses.json", index)
    print(json.dumps(dict(out=str(out / "witnesses.json"), sha256=digest, traces=index["traces"]), indent=1))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("phase1", "witnesses", "paired"):
        p = sub.add_parser(name)
        p.add_argument("--data", default=str(DEFAULT_DATA))
        p.add_argument("--out", required=True, help="new output directory (must not exist)")
        if name == "paired":
            p.add_argument("--execute-held-paired", action="store_true",
                           help="run H/A tables=[] accounting; only after a separate coordinator instruction")
    args = ap.parse_args()
    return dict(phase1=cmd_phase1, witnesses=cmd_witnesses, paired=cmd_paired)[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
