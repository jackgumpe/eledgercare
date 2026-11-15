"""Q0 execution session (runs inside the supervised child process).

Order is fixed and fail-closed: release -> lock -> storage/env -> platform/GPU -> installed
set -> fixtures+rasters -> model files + static safety -> cold load -> module-cache identity
-> observer -> one excluded warmup per fixture -> exactly two interleaved warm repeats per
fixture -> evaluation. Any classified failure stops further model calls; the outcome is
BLOCKED/NOT_QUALIFIED with the failure class and never an accuracy value.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import threading
import time
import traceback
from pathlib import Path

from . import HARNESS_ID
from .environment import audit_child_env, check_run_dir, check_storage_root, layout
from .fixtures import read_verified_fixture, verify_rendered_pages
from .hashing import is_hex, sha256_bytes
from .locks import validate_lock, verify_installed
from .modelfiles import load_manifest, verify_model_dir, verify_module_cache
from .outcome import BLOCKED, NOT_QUALIFIED, QUALIFIED, Q0Failure, make_outcome
from .procmem import PeakSampler
from .protocol import HARNESS_DIR, build_call_kwargs, call_timeout_s, check_context_budget, fixture_by_id, schedule
from .render import check_renderer, raster_tuples, render_pdf_bytes, renderer_identity
from .sourcecheck import MODEL_DIR_NAMES, analyze_model_sources
from .telemetry import NativeObserver, SafetyTripwire, resolve_targets
from .writer import BoundedJsonl, BoundedWriter


class Heartbeat:
    """Writes {phase, progress, t} atomically for the supervisor's timeout/stall guards."""

    def __init__(self, path: Path, interval_s: float, progress_fn):
        self.path = Path(path)
        self.interval = interval_s
        self.progress_fn = progress_fn
        self.phase = "starting"
        self.phase_timeout_s = None
        self._stop = threading.Event()
        self._t = threading.Thread(target=self._run, name="q0-heartbeat", daemon=True)

    def set_phase(self, phase: str, timeout_s: int | None, stall_monitored: bool):
        self.phase, self.phase_timeout_s, self.stall_monitored = phase, timeout_s, stall_monitored
        self.beat()

    def beat(self):
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"phase": self.phase, "phase_timeout_s": self.phase_timeout_s,
                                   "stall_monitored": getattr(self, "stall_monitored", False),
                                   "progress": int(self.progress_fn()), "t": time.time(), "pid": os.getpid()}),
                       encoding="utf-8")
        os.replace(tmp, self.path)

    def _run(self):
        while not self._stop.wait(self.interval):
            self.beat()

    def start(self):
        self._t.start()
        return self

    def stop(self):
        self._stop.set()
        self._t.join(timeout=5)


def validate_release(release: dict | None, *, protocol: dict, protocol_sha256: str, lock_sha256: str,
                     root: Path, owner: str) -> dict:
    if not release:
        raise Q0Failure("EXECUTION_NOT_RELEASED", "no coordinator release record supplied")
    want_seq = {"author": "004", "reviewer": "005"}[owner]
    problems = []
    if release.get("schema") != "eldq0-release/1": problems.append("schema")
    if release.get("packet") != "WP-0005" or release.get("sequence") != want_seq: problems.append("packet/sequence")
    if release.get("released_by") != "eld-coordinator": problems.append("released_by")
    if not is_hex(release.get("release_commit"), 40): problems.append("release_commit")
    if release.get("protocol_sha256") != protocol_sha256: problems.append("protocol_sha256")
    if release.get("lock_sha256") != lock_sha256: problems.append("lock_sha256")
    if release.get("gpu_uuid") != protocol["gpu"]["uuid"]: problems.append("gpu_uuid")
    if not release.get("lease_id"): problems.append("lease_id")
    if os.path.normcase(str(release.get("storage_root"))) != os.path.normcase(str(root)): problems.append("storage_root")
    if problems:
        raise Q0Failure("EXECUTION_NOT_RELEASED", "release record does not bind this exact execution", problems)
    return {k: release[k] for k in ("release_commit", "lease_id", "sequence", "gpu_uuid")}


class Session:
    def __init__(self, *, protocol: dict, protocol_sha256: str, lock: dict, lock_sha256: str, release: dict | None,
                 root: Path, owner: str, run_dir: Path, backend, repo_root: Path, expected_root: str,
                 forbidden_parents: list[str], manifest_path: Path | None = None, environ: dict | None = None,
                 heartbeat_path: Path | None = None):
        self.p, self.p_sha, self.lock, self.lock_sha = protocol, protocol_sha256, lock, lock_sha256
        self.release, self.root, self.owner, self.run_dir = release, Path(root), owner, Path(run_dir)
        self.backend, self.repo_root = backend, Path(repo_root)
        self.expected_root, self.forbidden_parents = expected_root, forbidden_parents
        self.manifest_path = manifest_path or (HARNESS_DIR / protocol["model"]["file_manifest"])
        self.environ = os.environ if environ is None else environ
        self.observer = None
        self.writer = BoundedWriter(self.run_dir / "evidence", total_cap_bytes=protocol["guards"]["max_log_bytes"])
        self.events = BoundedJsonl(self.run_dir / "evidence" / "events.jsonl",
                                   cap_bytes=protocol["guards"]["max_log_bytes"] // 8)
        self.heartbeat = Heartbeat(heartbeat_path or (self.run_dir / "heartbeat.json"),
                                   protocol["guards"]["heartbeat_interval_s"],
                                   lambda: self.observer.progress if self.observer else 0)
        self.checks: dict = {}
        self.context: dict = {"harness": HARNESS_ID, "protocol_sha256": protocol_sha256, "lock_sha256": lock_sha256,
                              "owner": owner, "python": sys.version}
        self.observations: list = []
        self.failures: list = []

    # -----------------------------------------------------------------
    def phase(self, name: str, timeout_s: int | None = None, stall: bool = False):
        self.heartbeat.set_phase(name, timeout_s, stall)
        self.events.append({"event": "phase", "phase": name, "t": time.time()})

    def fail(self, f: Q0Failure):
        self.failures.append(f.as_record())
        self.events.append({"event": "failure", **f.as_record()})

    def run(self) -> dict:
        self.heartbeat.start()
        try:
            self._run()
        except Q0Failure as f:
            self.fail(f)
        except BaseException as e:  # never hide: classify and keep traceback
            cls = "OOM" if self.backend.is_oom(e) else "RUNTIME_ERROR"
            self.fail(Q0Failure(cls, f"{type(e).__name__}: {e}", traceback.format_exc(limit=30)))
        finally:
            if self.observer is not None:
                self.observer.uninstall()
            self.heartbeat.set_phase("finished", None, False)
            self.heartbeat.stop()
        status = QUALIFIED if not self.failures else (NOT_QUALIFIED if self.observations else BLOCKED)
        self.context["events_log"] = self.events.close()
        self.context["evidence_index"] = list(self.writer.index)
        outcome = make_outcome(status, failures=self.failures, checks=self.checks,
                               observations=self.observations, context=self.context)
        self.writer.write_json("outcome.json", outcome, cap_bytes=8 << 20)
        return outcome

    # -----------------------------------------------------------------
    def _run(self):
        p, be = self.p, self.backend
        self.phase("preflight", p["guards"]["timeouts_s"]["preflight"])
        self.context["release"] = validate_release(self.release, protocol=p, protocol_sha256=self.p_sha,
                                                   lock_sha256=self.lock_sha, root=self.root, owner=self.owner)
        validate_lock(self.lock)

        # 1. storage & environment isolation
        check_storage_root(self.root, expected_root=self.expected_root, forbidden_parents=self.forbidden_parents)
        check_run_dir(self.run_dir, self.root, self.owner)
        audit_child_env(dict(self.environ), root=self.root, owner=self.owner, run_dir=self.run_dir)
        du = shutil.disk_usage(self.root)
        self.checks["1_storage_isolation"] = {"status": "pass", "provenance": "direct",
                                             "root": str(self.root), "free_bytes": du.free, "total_bytes": du.total,
                                             "hf_modules_cache": self.environ["HF_MODULES_CACHE"]}

        # 2. artifact & dependency lock
        plat = be.platform()
        self.context["platform"] = plat
        self._check_platform(plat)
        inst = verify_installed(self.lock, be.installed(), be.importable)
        pdfium = be.pdfium()
        ident = renderer_identity(pdfium, be.dist_version)
        check_renderer(ident, p)
        rendered = {}
        for fx in p["fixtures"]:
            data = read_verified_fixture(fx, self.repo_root)
            images = render_pdf_bytes(pdfium, data)
            pages = verify_rendered_pages(fx, raster_tuples(images))
            rendered[fx["fixture_id"]] = (images, pages)
        model_dir = layout(self.root, self.owner)["models"] / p["model"]["revision"]
        manifest = load_manifest(self.manifest_path)
        model_report = verify_model_dir(model_dir, manifest)
        facts = analyze_model_sources(model_dir, MODEL_DIR_NAMES)
        self.writer.write_json("model-files.json", model_report, cap_bytes=1 << 20)
        self.writer.write_json("static-safety.json", facts, cap_bytes=1 << 20)
        self.checks["2_artifact_dependency_lock"] = {
            "status": "pass", "provenance": "direct", "installed": inst, "renderer": ident,
            "rendered_pages": {k: v[1] for k, v in rendered.items()},
            "model_files_verified": len(model_report["files"])}

        # cold load
        self.phase("load", p["guards"]["timeouts_s"]["load"])
        with PeakSampler(0.25) as ps:
            tok, model, load_times = be.load(model_dir, p)
        mem_after_load = be.cuda_memory()
        pkg = type(model).__module__.rsplit(".", 1)[0]
        loaded = {n: getattr(m, "__file__", None) for n, m in list(sys.modules.items())
                  if n == "transformers_modules" or n.startswith("transformers_modules.")}
        cache_report = verify_module_cache(Path(self.environ["HF_MODULES_CACHE"]), model_dir, loaded)
        self.writer.write_json("module-cache.json", cache_report, cap_bytes=1 << 20)
        self.context["cold_load"] = {"provenance": "direct", "timings_s": load_times, "cuda_memory": mem_after_load,
                                     "host_memory": ps.result(), "package": pkg}

        # 3. save path invariant (static facts + frozen kwargs; runtime tripwire below)
        resolved, unresolved = resolve_targets(sys.modules, prefix=pkg + ".")
        self.observer = NativeObserver(resolved, unresolved).install()

        # 5. smoke execution
        for item in schedule(p):
            fx = fixture_by_id(p, item["fixture_id"])
            label = f"{fx['family_id']}.{item['kind']}{item['repeat'] or ''}"
            self.phase(f"call:{label}", call_timeout_s(p, fx["page_count"]), stall=True)
            self.observations.append(self._observe(fx, item, label, rendered[fx["fixture_id"]][0], tok, model))
        self.phase("evaluate")
        self._evaluate()

    def _check_platform(self, plat: dict):
        want, gpu = self.lock["platform"], self.p["gpu"]
        cuda = self.lock["cuda"]
        problems = []
        if plat.get("os") != want["os"] or plat.get("machine") != want["machine"]: problems.append("os/machine")
        if plat.get("python") != want["python"]: problems.append("python")
        if not plat.get("cuda_available"): problems.append("cuda_available")
        if plat.get("torch_cuda_version") != cuda["torch_cuda_version"]: problems.append("torch_cuda_version")
        if plat.get("device_count") != 1: problems.append("device_count (CUDA_VISIBLE_DEVICES must expose one GPU)")
        if gpu["name_contains"] not in str(plat.get("device_name")): problems.append("device_name")
        if list(plat.get("device_capability") or []) != cuda["device_capability"]: problems.append("capability")
        if cuda["required_arch"] not in (plat.get("arch_list") or []): problems.append("arch_list lacks sm_120")
        if plat.get("device_uuid") not in (gpu["uuid"], gpu["uuid"].removeprefix("GPU-")): problems.append("device_uuid")
        if problems:
            raise Q0Failure("UNSUPPORTED_PLATFORM", "platform/GPU differs from lock/protocol", {"problems": problems, "observed": plat})

    def _observe(self, fx, item, label, images, tok, model) -> dict:
        p, be, obs = self.p, self.backend, self.observer
        kwargs = build_call_kwargs(p, fx)
        mark = obs.begin_window()
        be.reset_peak()
        be.sync()
        error = None
        with PeakSampler(0.1) as ps:
            t0 = time.perf_counter_ns()
            try:
                text, ntok = be.invoke(model, tok, p["call"]["prompt"], images, kwargs)
            except SafetyTripwire as e:
                error = Q0Failure("SAFETY_VIOLATION", str(e))
            except BaseException as e:
                cls = "OOM" if be.is_oom(e) else "RUNTIME_ERROR"
                error = Q0Failure(cls, f"{type(e).__name__}: {e}", traceback.format_exc(limit=30))
            if error is None:
                be.sync()
            t1 = time.perf_counter_ns()
        win = obs.end_window(mark)
        rec = {"label": label, "fixture_id": fx["fixture_id"], "family_id": fx["family_id"], "kind": item["kind"],
               "repeat": item["repeat"], "excluded_from_warm_statistics": item["excluded"],
               "page_count_in": fx["page_count"], "call_kwargs": kwargs,
               "timing": {"external_synchronized_wall_s": {"provenance": "direct", "value": (t1 - t0) / 1e9}},
               "cuda_memory": be.cuda_memory(), "host_memory": ps.result(),
               "kernel_path": win["kernel_path"], "cache": win["cache"], "targets": win["targets"],
               "observer_overhead": win["observer_overhead"],
               "unresolved_optional_targets": win["unresolved_optional_targets"]}
        if win["violations"]:
            error = error or Q0Failure("SAFETY_VIOLATION", "forbidden save/eval path entered", win["violations"])
            rec["safety_violations"] = win["violations"]
        if error is not None:
            rec["error"] = error.as_record()
            self.writer.write_json(f"{label}.observation.json", rec, cap_bytes=4 << 20)
            self.observations.append(rec)  # the failed call stays visible in the outcome
            raise error
        if len(win["native_results"]) != 1:
            raise Q0Failure("TELEMETRY_UNSUPPORTED", f"expected one native result capture, got {len(win['native_results'])}")
        nat = win["native_results"][0]
        if nat["text"] != text or nat["output_tokens"] != ntok:
            raise Q0Failure("TELEMETRY_UNSUPPORTED", "captured native result disagrees with infer_multi return")
        raw_cap = p["guards"]["max_raw_output_bytes"]
        rec["raw_output"] = self.writer.write_text(f"{label}.raw.txt", text, cap_bytes=raw_cap)
        rec["token_ids_file"] = self.writer.write_json(f"{label}.token_ids.json", nat["token_ids"], cap_bytes=raw_cap)
        native = {k: v for k, v in nat.items() if k not in ("token_ids", "text")}
        native["token_ids_sha256"] = sha256_bytes(json.dumps(nat["token_ids"]).encode())
        native["text_sha256"] = sha256_bytes(text.encode("utf-8", "backslashreplace"))
        rec["native"] = native
        t = rec["timing"]
        if nat["prefill_time_s"] is not None and nat["time_s"] is not None:
            t["native_prefill_to_first_token_s"] = {"provenance": "native", "value": nat["prefill_time_s"],
                                                    "note": "t_first - t0 in _uocr_generate; host-synchronized by int(argmax)"}
            t["native_generate_total_s"] = {"provenance": "native", "value": nat["time_s"]}
            t["decode_s"] = {"provenance": "derived", "value": nat["time_s"] - nat["prefill_time_s"]}
            t["outside_generate_s"] = {"provenance": "derived",
                                       "value": t["external_synchronized_wall_s"]["value"] - nat["time_s"],
                                       "note": "prompt build, _uocr_build_inputs preprocessing, observer overhead, final sync"}
        rec["page_markers"] = {"provenance": "direct", "expected": nat["expected_pages"], "out": nat["num_pages_out"],
                               "marker_token_positions": _marker_positions(nat["token_ids"], p["call"]["page_token_id"])}
        rec["flags"] = []
        try:
            check_context_budget(nat["prompt_len"], kwargs["max_new_tokens"], kwargs["max_length"])
        except Q0Failure as f:
            rec["flags"].append(f.as_record())
        if nat["finish_reason"] != "stop":
            rec["flags"].append(Q0Failure("TRUNCATION", f"finish_reason={nat['finish_reason']!r}").as_record())
        if nat["expected_pages"] != fx["page_count"] or nat["num_pages_out"] != fx["page_count"]:
            rec["flags"].append(Q0Failure("PAGE_COUNT_MISMATCH",
                                          f"in={fx['page_count']} expected={nat['expected_pages']} out={nat['num_pages_out']}").as_record())
        self.writer.write_json(f"{label}.observation.json", rec, cap_bytes=4 << 20)
        return rec

    def _evaluate(self):
        obs = self.observations
        warm = [o for o in obs if o["kind"] == "warm"]
        per_fx = {}
        for o in warm:
            per_fx.setdefault(o["fixture_id"], []).append(o)
        repeat = {}
        for fid, runs in per_fx.items():
            if len(runs) != 2:
                self.fail(Q0Failure("TELEMETRY_UNSUPPORTED", f"{fid}: {len(runs)} warm observations, expected exactly 2"))
                continue
            a, b = runs
            same = a["native"]["token_ids_sha256"] == b["native"]["token_ids_sha256"]
            repeat[fid] = {"provenance": "direct", "warm_repeats_identical": same,
                           "warmup_identical_to_warm1": next(o for o in obs if o["fixture_id"] == fid and o["kind"] == "warmup")
                           ["native"]["token_ids_sha256"] == a["native"]["token_ids_sha256"]}
            if not same:
                self.fail(Q0Failure("NONDETERMINISTIC_OUTPUT", f"{fid}: warm repeats differ"))
        for o in obs:
            for flag in o["flags"]:
                self.fail(Q0Failure(flag["failure_class"], f"{o['label']}: {flag['detail']}"))
        labels = {o["kernel_path"]["label"] for o in obs}
        cache_ok = all(o["cache"].get("observed") and o["cache"]["grows_by_one_each_decode_step"]
                       and not o["cache"]["ring_buffer_marker_seen"] for o in obs)
        self.checks["3_save_results_invariant"] = {
            "status": "pass", "provenance": "direct+source",
            "frozen_kwargs": {"save_results": False, "output_path": ""},
            "tripwire_entries": sum(len(o.get("safety_violations", [])) for o in obs)}
        self.checks["4_kernel_cache_telemetry"] = {
            "status": "pass" if cache_ok and "mixed" not in labels else "fail", "provenance": "direct",
            "kernel_path_labels": sorted(labels), "dynamic_cache_growth_observed": cache_ok}
        if self.checks["4_kernel_cache_telemetry"]["status"] != "pass":
            self.fail(Q0Failure("TELEMETRY_UNSUPPORTED", "kernel/cache path not unambiguously observed"))
        self.checks["5_smoke_execution"] = {
            "status": "pass" if not self.failures else "fail", "provenance": "direct+native",
            "observations": len(obs), "warm_observations": len(warm), "repeatability": repeat}
        self.checks["6_honest_failure_accounting"] = {"status": "pass", "accuracy_score": None,
                                                      "failure_classes": sorted({f["failure_class"] for f in self.failures})}


def _marker_positions(token_ids: list[int], page_id: int) -> list[int]:
    return [i for i, t in enumerate(token_ids) if t == page_id]
