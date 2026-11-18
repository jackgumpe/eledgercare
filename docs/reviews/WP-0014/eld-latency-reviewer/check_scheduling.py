"""Check seven published browser waits against raw events and matching saved identities."""

import io
import json
import re
import subprocess
import sys
import zipfile

from check_repeat import FIXTURES, SHORT_TRUTH, read, sha


def records(path):
    return [json.loads(line) for line in path.read_text(encoding="utf8").splitlines()]


def check(revision):
    prefix = "docs/research/WP-0014/scheduling/evidence"
    archive = subprocess.check_output(["git", "archive", "--format=zip", revision, prefix])
    root = zipfile.Path(zipfile.ZipFile(io.BytesIO(archive)), prefix + "/")
    database = read(root / "database.json")
    attempts = read(root / "attempts.json")
    summary = read(root / "summary.json")
    rows, lifetimes = [], []
    assert len(attempts) == 7 and len(database) == 21
    for phase in ("stock", "demandfirst", "demand", "immediate", "ready"):
        f = root / phase
        browser, manager = records(f / "browser.jsonl"), records(f / "manager.jsonl")
        engine = [] if phase == "stock" else records(f / "engine.jsonl")
        expected = {"stock": [], "demandfirst": ["A"], "demand": ["W", "A"], "ready": ["W", "A", "B"],
                    "immediate": ["W", "A", "B"]}[phase]
        assert [e["item"] for e in engine if e["event"] == "infer_start"] == expected
        assert [e["item"] for e in engine if e["event"] == "infer_end"] == expected
        if engine:
            assert len({e["pid"] for e in engine}) == 1 and sum(e["event"] == "model_load_start" for e in engine) == 1
            assert sum(e["event"] == "spawned" for e in manager) == 1
        if len(expected) == 3:
            assert sum(e["event"] == "prepare_signal" for e in manager) == 2
        lifetimes.append({"phase": phase, "call_order": expected or ["A"]})
        for key in ("AB" if phase in ("immediate", "ready") else "A"):
            saved = read(f / f"{key}-saved-identities.json")
            env = read(f / f"{key}-envelope.json")
            ev = {e["name"]: e for e in browser if e.get("key") == key}
            raw = (f / f"{key}-raw.txt").read_bytes()
            digest = sha(raw)
            assert saved["status"] == env["status"] == "completed" and env["output"]["finish_reason"] == "stop"
            assert ev["result_viewport_frame"]["inViewport"] and digest == env["output"]["sha256"] == ev["reopened"]["raw"]
            assert sha((FIXTURES / f"{key}.pdf").read_bytes()) == saved["originalSha256"] == ev["reopened"]["original"]
            assert ev["reopened"]["doc"] == env["document_id"] == saved["documentId"] and env["job_id"] == saved["jobId"]
            assert ev["reopened"]["attempt"] == env["attempt_id"] == saved["currentAttempt"]["attemptId"]
            assert sum(a["attempt_id"] == env["attempt_id"] and a["status"] == "completed" for a in attempts) == 1
            db = {e["status"]: e["commit_ms"] for e in database if e["document_id"] == env["document_id"]}
            assert db.keys() == {"queued", "running", "completed"} and db["queued"] <= db["running"] <= db["completed"]
            text = re.sub(r"<BLOCK>\w+\[[\d, ]+\]<FORK>", " ", raw.decode().removeprefix("<PAGE>"))
            assert " ".join(text.split()) == SHORT_TRUTH[key]
            click, opened, visible = (ev[n]["browser_ms"] for n in ("request-extraction", "intake_open", "result_viewport_frame"))
            row = dict(phase=phase, key=key, document_id=env["document_id"], raw_sha256=digest, exact_text=True,
                       click_ms=click, intake_ms=opened, visible_ms=visible,
                       intake_to_click_s=(click-opened)/1000, click_to_visible_s=(visible-click)/1000,
                       intake_to_visible_s=(visible-opened)/1000, queue_to_claim_s=(db["running"]-db["queued"])/1000,
                       commit_to_visible_s=(visible-db["completed"])/1000)
            supplied = next(x for x in summary["rows"] if (x["phase"], x["key"]) == (phase, key))
            assert abs(supplied["clock_ms"]["visible"]-visible) < 0.001
            rows.append(row)
    assert len({r["document_id"] for r in rows}) == 7
    return dict(revision=revision, rows=rows, lifetimes=lifetimes,
                peak_concurrent_running_in_queue_trace=max(e["active"] for e in database))


if __name__ == "__main__":
    print(json.dumps(check(sys.argv[1]), indent=2))
