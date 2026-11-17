"""Offline independent disposition checks on actual preserved /004 evidence."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[7]
AREA = Path(__file__).resolve().parent.parent
E = AREA / "evidence"
BASE = "bf2172c9ecaab63de038300960082f3b521f8074"
AUTH = "2d19a46b0d5e31995c5a00720faa285a61ab4fa8"


def read(path): return json.loads(path.read_text(encoding="utf-8"))
def sha(data): return hashlib.sha256(data).hexdigest()
def git(*args): return subprocess.check_output(["git", *args], cwd=ROOT)
def bytea(value):
    assert value.startswith("\\x")
    return bytes.fromhex(value[2:])
def tree(commit):
    out = {}
    for row in git("ls-tree", "-rz", "--full-tree", commit).split(b"\0"):
        if row:
            metadata, path = row.split(b"\t", 1)
            out[path.decode()] = metadata.decode()
    return out


def main():
    collection = read(E / "collection-inventory.json")
    for row in collection["copied_files"]:
        data = (ROOT / row["path"]).read_bytes()
        assert len(data) == row["bytes"] and sha(data) == row["sha256"]
    for row in collection["originals"]:
        data = (Path(row["source_root"]) / row["source_path"]).read_bytes()
        assert len(data) == row["bytes"] and sha(data) == row["sha256"]
        if "copy" in row: assert data == (ROOT / row["copy"]["path"]).read_bytes()
    for row in collection["git_inputs"]:
        assert sha(git("show", f"{row['commit']}:{row['path']}")) == row["sha256"]
    d = read(E / "database/post-restart-tables.json")
    p1, p2 = read(E / "browser/edge-live-phase1.json"), read(E / "browser/edge-live-phase2-post-restart.json")
    returned, summary = read(E / "browser/resource-return.json"), read(E / "browser/summary.json")
    release = json.loads(git("show", f"{AUTH}:docs/coordination/WP-0012/releases/reviewer-004-r3.json"))
    checks = []
    def check(name, condition, detail=None):
        assert condition, name
        checks.append(dict(name=name, passed=True, detail=detail))
    check("exact_two_fresh_no_retry_attempts", len(d["execution_attempts"]) == 2 and all(a["attempt_number"] == 1 and a["retried_from_attempt_id"] is None and a["status"] == "completed" and a["exit_code"] == 0 for a in d["execution_attempts"]))
    results = []
    for row in d["extraction_results"]:
        run = E / "attempts" / ("attempt-" + row["attempt_id"])
        request, envelope = read(run / "request.json"), read(run / "output/envelope.json")
        raw = (run / "output/raw_output.utf8.bin").read_bytes()
        pdf = (run / "input/document.pdf").read_bytes()
        original = next(x for x in d["original_artifacts"] if x["document_id"] == row["document_id"])
        check("original_pdf_exact_" + str(row["page_count"]), pdf == bytea(original["bytes"]) and sha(pdf) == bytea(original["sha256"]).hex() == bytea(row["input_sha256"]).hex() == request["expected_input_sha256"] == envelope["input"]["sha256"])
        check("raw_output_exact_" + str(row["page_count"]), raw == bytea(row["raw_output_bytes"]) and sha(raw) == bytea(row["raw_output_sha256"]).hex() == envelope["output"]["sha256"] and len(raw) == row["raw_output_byte_length"] == envelope["output"]["byte_length"])
        check("provenance_exact_" + str(row["page_count"]), bytea(row["model_manifest_sha256"]).hex() == release["pinned_digests"]["model_manifest_sha256"] and bytea(row["dependency_lock_sha256"]).hex() == release["pinned_digests"]["dependency_lock_sha256"] and bytea(row["worker_source_digest"]).hex() == release["pinned_digests"]["worker_source_sha256"] and bytea(row["worker_config_digest"]).hex() == release["pinned_digests"][f"worker_config_{row['page_count']}p_sha256"])
        check("successful_fresh_envelope_" + str(row["page_count"]), envelope["status"] == "completed" and envelope["failure"] is None and envelope["output"]["finish_reason"] == "stop" and row["page_count"] == row["output_page_count"] == envelope["output"]["output_page_count"] and datetime.fromisoformat(envelope["timings"]["started_at_utc"]) > datetime.fromisoformat(release["released_utc"]))
        results.append(dict(document_id=row["document_id"], attempt_id=row["attempt_id"], page_count=row["page_count"], raw_sha256=sha(raw), raw_bytes=len(raw), output_tokens=envelope["output"]["output_token_count"], timings=envelope["timings"], machine_date_error_preserved=b"2025-10-01" in raw))
    wo, mp = p1["woDocument"]["documentId"], p1["mpDocument"]["documentId"]
    wo_revs = sorted((r for r in d["work_order_review_revisions"] if r["document_id"] == wo), key=lambda r:r["revision_number"])
    mp_rev = next(r for r in d["work_order_review_revisions"] if r["document_id"] == mp)
    check("reviewed_one_then_newer_draft_two", [(r["revision_number"], r["status"]) for r in wo_revs] == [(1,"reviewed"),(2,"draft")] and next(r for r in d["work_order_review_heads"] if r["document_id"] == wo)["current_status"] == "draft")
    def fields(revision): return {r["field_key"]:r for r in d["work_order_review_fields"] if r["revision_id"] == revision["revision_id"]}
    w1, w2, m = fields(wo_revs[0]), fields(wo_revs[1]), fields(mp_rev)
    check("four_source_values_preserved", all(w1[k]["decision"] == "accepted" and w1[k]["human_value"] == value for k,value in {"work_order_id":"WO-004192", "property_name":"Cedar Hollow Apartments", "building_unit":"Bldg B - Unit 204", "requested_date":"2026-10-16"}.items()))
    check("draft_not_promoted_into_reviewed", "Callahan" not in w1["issue_and_resolution"]["human_value"] and "Callahan" in w2["issue_and_resolution"]["human_value"] and p1["archiveChecks"]["qDraftNonLeak"]["count"] == 0)
    check("three_explicit_unknowns", mp_rev["status"] == "reviewed" and mp_rev["unknown_field_count"] == 3 and mp_rev["edited_field_count"] == 2 and all(m[k]["decision"] == "unknown" and m[k]["human_value"] is None and bool(m[k]["unknown_reason"]) for k in ("work_order_id", "building_unit", "requested_date")))
    check("human_billing_date_distinct_from_machine_error", "2026-10-01" in m["issue_and_resolution"]["human_value"] and any(r["page_count"] == 3 and r["machine_date_error_preserved"] for r in results))
    check("archive_machine_reviewed_semantics", p1["archiveChecks"]["qMachineMp"]["documentIds"] == [mp] and p1["archiveChecks"]["qReviewedMpUnknownAbsent"]["count"] == 0 and p1["archiveChecks"]["qReviewedSku"]["documentIds"] == [wo] and p1["archiveChecks"]["qReviewedMpDate"]["documentIds"] == [mp])
    check("restart_disabled_with_no_new_attempts", p2["extChecks"] == {"woWorkerEnabled":False, "woAttempts":1, "mpWorkerEnabled":False, "mpAttempts":1} and p2["extractionPostCountDuringPhase2"] == 0 and p2["storageCounts"] == {"localKeys":[], "sessionKeys":[]} and p1["extractionRequestsIssued"] == p1["extractionPostCountObserved"] == 2)
    check("actual_clean_return", returned["status"] == "completed" and returned["clean_return_verified"] is True and returned["lease_returned"] is True and returned["cleanup_errors"] == [] and returned["pg_ctl_status_exit_code"] == 3 and all(v == [] for v in returned["ports_after"].values()) and returned["q0_model_immutability_verified"] is True)
    check("durable_counts_match_runtime", returned["persisted_counts"] == summary["persisted_counts"] and all(len(d[k]) == count for k,count in returned["persisted_counts"].items()) and len(d["archive_result_projections"]) == 2 and len(d["archive_projection_units"]) == 4)
    before, after = tree(BASE), tree("HEAD")
    check("inherited_tree_unchanged", all(after.get(k) == v for k,v in before.items()), len(before))
    check("accepted_product_trees_unchanged", all(git("rev-parse", f"HEAD:{p}").decode().strip() == oid for p,oid in release["product_tree_objects"].items()))
    source_paths = ["docs/reviews/WP-0012/eld-f4-reviewer/live-004/integration-correction/helpers/run_wp0012_reviewer_rehearsal_v7.py", "docs/reviews/WP-0012/eld-f4-reviewer/live-004/integration-correction/helpers/ownership_v6.py", "docs/reviews/WP-0012/eld-f4-reviewer/preparation/helpers/run_wp0012_reviewer_rehearsal.py", "docs/reviews/WP-0012/eld-f4-reviewer/preparation/helpers/drive_wp0012_edge_workflow.mjs"]
    sources = []
    for path in source_paths:
        data = git("show", f"{BASE}:{path}")
        assert data == (ROOT/path).read_bytes()
        sources.append(dict(commit=BASE, path=path, sha256=sha(data)))
    limitations = ["Screenshot06 contains Searching/Loading archive results; it does not prove painted result cards. Subsequent witness click/history assertions and query receipts are the actual evidence.", "Postrestart screenshots08/09 show unpainted dark native PDF panes. URL#page2, range reads, DOM page indicator and extracted-page highlight passed; these are not pixel proof of painted native target page.", "Phase1 MP review screenshot04 labels Page3 while the native pane still shows Page1 at capture. No settled native PDF paint claim or product defect inference follows.", "No visual-capture-only rerun, extra extraction or accuracy benchmark was performed."]
    audit = dict(checked_utc=datetime.now(timezone.utc).isoformat(), source=BASE, checks=checks, actual_results=results, inherited_paths_preserved=len(before), original_files_verified=len(collection["originals"]), copied_files_verified=len(collection["copied_files"]), git_bindings_verified=len(collection["git_inputs"]), runtime_source_bindings=sources, screenshot_limitations=limitations, disposition="accepted for bounded actual workflow; native PDF paint not visually established")
    target = AREA / "semantic-audit.json"
    assert not target.exists()
    target.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    artifact_rows = []
    for path in sorted(AREA.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            data = path.read_bytes()
            artifact_rows.append(dict(path=path.relative_to(ROOT).as_posix(), bytes=len(data), sha256=sha(data)))
    inv = AREA / "final-inventory.json"
    assert not inv.exists()
    inv.write_text(json.dumps(dict(base=BASE, audit_executing_head=git("rev-parse","HEAD").decode().strip(), artifacts=artifact_rows, inherited_paths_preserved=len(before), metadata_after_inventory=[inv.relative_to(ROOT).as_posix(), "docs/agent-reports/eld-f4-reviewer/WP-0012/004_2026-11-17_review_eld-f4-reviewer.md"]), indent=2) + "\n", encoding="utf-8")
    print(json.dumps(dict(checks=len(checks), artifacts=len(artifact_rows), copied_files=len(collection["copied_files"]), original_files=len(collection["originals"]), inherited=len(before))))


if __name__ == "__main__": main()
