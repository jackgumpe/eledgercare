"""Replay frozen WP-0027 Part B. Inputs and outputs are explicitly bound by the caller."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
from importlib.metadata import version
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from time import perf_counter_ns

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from fixtures import (ARCHIVE_SHA, PLAN_SHA, SYNTHETIC, bound, development, printed_fixture,
                      synthetic_native, synthetic_sections)
from reader import (MARKER, ROOT, SPAN_SHA, TOKENIZER_SHA, Reader, check_hash, digest,
                    packed, parse_json, require, uint32_bytes)

SPEED = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0027")
INPUT = SPEED / "coordination/inputs/k0014"
Q0 = Path("C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe")
K_NATIVE = "ce9d03a8d73ecf4366b96bc2dbbf9e129f5a2ca30265876a16b17c07cc20b169"
K_SOURCE = "10aea96000abf9bd571f95cee7bf2270d1854b1c3c6341ff8548d2bc9593be32"
CACHE_KEYS = ("TEMP", "TMP", "TMPDIR", "HF_HOME", "HF_HUB_CACHE", "HF_ASSETS_CACHE", "TRANSFORMERS_CACHE",
              "TORCH_HOME", "XDG_CACHE_HOME", "MPLCONFIGDIR", "NUMBA_CACHE_DIR", "LOCALAPPDATA", "APPDATA",
              "PYTHONPYCACHEPREFIX", "TORCH_EXTENSIONS_DIR", "TRITON_HOME", "HF_MODULES_CACHE")


def observed_environment(run):
    require(Path(sys.executable).resolve() == Q0.resolve() and sys.flags.isolated and sys.dont_write_bytecode
            and not sys.flags.optimize, "isolated_Q0_required")
    require(os.environ["CUDA_VISIBLE_DEVICES"] == "-1" and all(os.environ[k] == "1" for k in
            ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "HF_DATASETS_OFFLINE")), "offline_cpu_required")
    require(run.parent in ((SPEED / "reader").resolve(), (SPEED / "review").resolve()), "unowned_run")
    for key in CACHE_KEYS:
        require(Path(os.environ[key]).resolve().is_relative_to(run), "unowned_cache:" + key)
    return dict(executable=sys.executable, python=sys.version, isolated=bool(sys.flags.isolated),
                dont_write_bytecode=sys.dont_write_bytecode, cuda_visible_devices=os.environ["CUDA_VISIBLE_DEVICES"],
                offline={k:os.environ[k] for k in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "HF_DATASETS_OFFLINE")},
                cache_environment={k:os.environ[k] for k in CACHE_KEYS},
                packages={k:version(k) for k in ("tokenizers", "Pillow", "pypdfium2")})


def witness(reader, folder):
    # The SHA below comes from the independent coordinator, never from the case directory.
    source_bytes = (INPUT / "source.json").read_bytes()
    check_hash(source_bytes, K_SOURCE, "coordinator_manifest_pin")
    source = parse_json(source_bytes)
    native = (INPUT / "native.json").read_bytes()
    check_hash(native, K_NATIVE, "disclosed_native_pin")
    require(source["tag"] == "k0014" and source["window"] == 6 and source["native_sha256"] == K_NATIVE
            and source["source_page_count"] >= 18, "disclosed_call")
    require([p["page_number"] for p in source["pages"]] == [16, 17, 18], "disclosed_page_order")
    images, pages = [], []
    for p in source["pages"]:
        number = p["page_number"]
        require(p["png_file"] == f"page-{number:03}.png", "disclosed_raster_name")
        images.append((INPUT / p["png_file"]).read_bytes())
        pages.append(dict(page=number, png_sha256=p["png_sha256"], rgb_sha256=p["rgb_sha256"],
                          size=[p["width"], p["height"]], lines=p["source_lines"]))
    binding = bound("WP-0026/blind-c1-r1/k0014", source["source_pdf_sha256"], source["native_sha256"], pages)
    record = json.loads(native)
    try:
        reader.original_map(record)
    except ValueError as exc:
        old = str(exc)
    else:
        old = "unexpected_original_acceptance"
    observed = reader.observe(record)
    require(old == "Expected three grounded native pages"
            and [s["marker_token"] for s in observed["sections"]] == [0, 42, 81, 121]
            and observed["ids_through_eos"][-1] == 1, "original_rejection_not_reproduced")
    (folder / "k0014-native.json").write_bytes(native)
    (folder / "k0014-source.json").write_bytes(source_bytes)
    (folder / "k0014-ids-through-eos.u32le").write_bytes(uint32_bytes(observed["ids_through_eos"]))
    return native, binding, images, dict(original_decision="rejected", original_exception=old,
                                        observation=observed, coordinator_source_sha256=K_SOURCE)


class Cases:
    def __init__(self, reader, folder):
        self.reader = reader
        self.folder = folder
        self.rows = []

    def run(self, name, native, binding, images, reason, *, pin=None, evidence=None):
        expected = "accepted" if reason in ("one_empty_terminal_marker", "ordinary") else "unresolved"
        pinned = pin if pin is not None else digest(binding)
        start = perf_counter_ns()
        actual = self.reader.map(native, binding, pinned, images)
        elapsed = perf_counter_ns() - start
        row = dict(case=name, expected=dict(decision=expected, reason=reason),
                   actual={k:actual[k] for k in ("decision", "reason")},
                   native_sha256=digest(native), binding_sha256=digest(binding), trusted_binding_sha256=pinned,
                   ordered_image_sha256=[digest(i) for i in images],
                   cpu_wall_ns=elapsed, result_sha256=digest(packed(actual)))
        row["matched"] = row["expected"] == row["actual"]
        if evidence is not None:
            filename = name + ".json"
            (self.folder / filename).write_bytes(packed(dict(evidence, candidate=actual)))
            row["witness"] = filename
        self.rows.append(row)
        return actual


def development_cases(cases):
    for tag, native, binding, images, metadata, observations in development():
        meta, trace = json.loads(metadata), json.loads(observations)
        old = cases.reader.original_map(json.loads(native))
        actual = cases.run(tag, native, binding, images, "ordinary")
        unchanged = actual.get("projection") == old == {k:meta[k] for k in old}
        require(unchanged, f"{tag}_historical_projection")
        raw = json.loads(native)
        positions = trace["absolute_positions"]
        first = len(raw["prompt_token_ids"])
        require(trace["ids"] == raw["token_ids"] and positions == list(range(first, first+len(trace["ids"]))),
                f"{tag}_archive_positions")
        selections = []
        for span in actual["projection"]["spans"]:
            indices = span["token_indices"]
            absolute = [positions[i] for i in indices]
            archived = [positions[i] for i in meta["spans"][span["index"]]["token_indices"]]
            require(absolute == archived, f"{tag}_historical_feature_selection")
            selections.append(dict(span=span["index"], emitted_indices=indices, absolute_positions=absolute))
        filename = tag + ".json"
        (cases.folder / filename).write_bytes(packed(dict(candidate=actual, historical_projection_sha256=digest(packed(old)),
             archive_metadata_sha256=digest(metadata), archived_observed_positions_sha256=digest(observations),
             feature_position_selections=selections, full_projection_exact=unchanged,
             ordered_input_authority=dict(archive_sha256=ARCHIVE_SHA, plan_sha256=PLAN_SHA,
                                          source_pdf_sha256=json.loads(binding)["document_sha256"]))))
        cases.rows[-1]["witness"] = filename
    return raw["prompt_token_ids"]


def synthetic_cases(cases, prompt):
    pages, images = printed_fixture(SYNTHETIC)
    sections = synthetic_sections(SYNTHETIC)
    doc = digest(packed([p["png_sha256"] for p in pages]))
    a, b, c = sections
    def one(name, sections, reason, *, source=pages, raster=images, change_native=None, change_binding=None):
        native = synthetic_native(cases.reader, sections, prompt)
        if change_native:
            change_native(native)
        raw = packed(native)
        binding = bound(name, doc, digest(raw), source)
        pin = digest(binding)
        if change_binding:
            binding = change_binding(binding)
        return cases.run(name, raw, binding, raster, reason, pin=pin)
    one("synthetic-ordinary", sections, "ordinary")
    one("synthetic-terminal", [*sections, MARKER], "one_empty_terminal_marker")
    one("interior-empty", [a, MARKER, c, MARKER], "empty_input_section")
    one("multiple-terminal", [*sections, MARKER, MARKER], "section_count")
    for name, payload in (("text", "x"), ("space", " "), ("newline", "\n"), ("markup", "<i></i>")):
        one("extra-"+name, [*sections, MARKER+payload], "extra_section_has_payload")
    one("missing-section", [a, c], "section_count")
    one("merged-section", [a+b[len(MARKER):], c], "section_count")
    # All of the following have three plausible populated sections and the exact terminal shape.
    one("source-page-reordered", [b, a, c, MARKER], "source_line_sequence_mismatch")
    one("source-page-duplicated", [a, a, c, MARKER], "source_line_sequence_mismatch")
    one("source-lines-split-across-pages", [a.split("\n")[0]+"\n", MARKER+a.split("\n")[1]+"\n"+b[len(MARKER):],
                                            c, MARKER], "source_line_sequence_mismatch")
    one("source-line-missing", [a.split("\n")[0]+"\n", b, c, MARKER], "source_line_sequence_mismatch")
    one("source-line-duplicated", [a+a.split("\n")[1]+"\n", b, c, MARKER], "source_line_sequence_mismatch")
    one("ungrounded-prefix", [MARKER+"lost"+a[len(MARKER):], b, c, MARKER], "ungrounded_section_prefix")
    one("wrong-grounded-geometry", [a.replace("20, 50, 700, 190", "800, 800, 900, 900"), b, c, MARKER],
        "source_line_outside_grounded_box")
    one("empty-geometry", [a.replace("20, 50, 700, 190", "0, 0, 0, 0"), b, c, MARKER],
        "incomplete_grounded_projection")
    one("missing-eos", [*sections, MARKER], "missing_terminal_eos",
        change_native=lambda n:n.update(eos_observed=False))
    one("wrong-observed-step", [*sections, MARKER], "terminal_observation_mismatch",
        change_native=lambda n:n["terminal_observation"].update(step=1))
    one("wrong-guard-count", [*sections, MARKER], "native_guard_mismatch",
        change_native=lambda n:n["terminal_observation"]["guard"].update(marker_cum=3))
    one("wrong-input-bytes", [*sections, MARKER], "ordered_png_identity", raster=[images[1],images[0],images[2]])
    one("untrusted-binding", [*sections, MARKER], "untrusted_binding",
        change_binding=lambda raw:packed(dict(json.loads(raw), document_sha256="0"*64)))
    no_lines = deepcopy(pages)
    no_lines[1]["lines"] = []
    one("missing-proof-of-coverage", [*sections, MARKER], "missing_source_lines", source=no_lines)
    omitted_line = deepcopy(pages)
    omitted_line[0]["lines"].pop()
    one("omitted-from-witness-and-output", [a.split("\n")[0]+"\n", b, c, MARKER],
        "incomplete_source_pixel_coverage", source=omitted_line)
    blank = [SYNTHETIC[0], [], SYNTHETIC[2]]
    blank_pages, blank_pngs = printed_fixture(blank)
    one("true-blank-in-original-position", synthetic_sections(blank), "verified_blank_source_withheld",
        source=blank_pages, raster=blank_pngs)
    duplicate = [SYNTHETIC[0], SYNTHETIC[0], SYNTHETIC[2]]
    duplicate_pages, duplicate_pngs = printed_fixture(duplicate)
    one("indistinguishable-proof", [*synthetic_sections(duplicate), MARKER], "indistinguishable_source_text",
        source=duplicate_pages, raster=duplicate_pngs)
    native = packed(synthetic_native(cases.reader, sections, prompt))
    original_binding = bound("known-call", doc, digest(native), pages)
    altered = packed(synthetic_native(cases.reader, [b,a,c,MARKER], prompt))
    cases.run("native-from-other-call", altered, original_binding, images, "native_identity")
    missing_call = packed(dict(json.loads(original_binding), call=""))
    cases.run("missing-source-identity", native, missing_call, images, "incomplete_call_binding")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run", type=Path)
    p.add_argument("candidate")
    args = p.parse_args()
    run = args.run.resolve()
    env = observed_environment(run)
    git = r"C:/Program Files/Git/cmd/git.exe"
    head = subprocess.check_output([git, "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    require(re.fullmatch("[0-9a-f]{40}", args.candidate), "full_candidate_commit_required")
    code = [str(HERE / name) for name in ("reader.py", "replay.py", "fixtures.py", "run.ps1", "POLICY.md")]
    source_diff = subprocess.run([git, "-C", str(ROOT), "diff", "--quiet", args.candidate, "--",
                                  *code, str(ROOT/"docs/research/WP-0024/sensor/spans.py")]).returncode
    require(source_diff == 0, "candidate_source_changed")
    folder = run / "results"
    folder.mkdir(exist_ok=False)
    start = perf_counter_ns()
    begun = datetime.now(timezone.utc).isoformat()
    reader = Reader()
    cases = Cases(reader, folder)
    native, binding, images, old = witness(reader, folder)
    cases.run("k0014", native, binding, images, "one_empty_terminal_marker", evidence=old)
    prompt = development_cases(cases)
    synthetic_cases(cases, prompt)
    require("torch" not in sys.modules and "transformers" not in sys.modules, "unexpected_model_runtime")
    table = dict(schema="wp0027-terminal-reader-cases-v1", candidate=args.candidate, execution_head=head,
                 started_utc=begun, finished_utc=datetime.now(timezone.utc).isoformat(),
                 cpu_wall_ns=perf_counter_ns()-start, argv=sys.orig_argv, runtime=env,
                 model_runtime_imports=[], inference_calls=0, hidden_feature_files_read=0,
                 parser_sha256=SPAN_SHA, tokenizer_sha256=TOKENIZER_SHA, cases=cases.rows,
                 matched=sum(r["matched"] for r in cases.rows), total=len(cases.rows))
    (folder / "parser-cases.json").write_bytes(packed(table))
    print(json.dumps(dict(matched=table["matched"], total=table["total"],
                          mismatches=[r for r in table["cases"] if not r["matched"]]), indent=2))
    return 0 if table["matched"] == table["total"] else 1


if __name__ == "__main__":
    sys.exit(main())
