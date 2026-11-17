"""Build independent /007 source, input and output audit without model access."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[6]
OWNED = "docs/reviews/WP-0012/eld-f4-reviewer/correction-006-review"
AUTHOR = "docs/implementation/WP-0012/eld-f4-implementer/correction-006"
BASE = "379d8c5d607fd248d7f272e412b4ed4a97bc64f6"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def tree(commit, prefix=None):
    args = ["ls-tree", "-rz", commit]
    if prefix:
        args += ["--", prefix]
    return {record.split(b"\t", 1)[1].decode(): record.split(b"\t", 1)[0].decode()
            for record in git(*args).split(b"\0") if record}


def file_record(path):
    raw = (ROOT / path).read_bytes()
    blob = git("show", f"HEAD:{path}")
    if raw.replace(b"\r\n", b"\n") != blob.replace(b"\r\n", b"\n"):
        raise AssertionError(f"Uncommitted byte drift: {path}")
    return {"path": path, "bytes": len(raw), "sha256_raw": hashlib.sha256(raw).hexdigest(),
            "sha256_lf": hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest(),
            "git_blob_sha256": hashlib.sha256(blob).hexdigest()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--author-publication", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    assert not git("status", "--porcelain", "--untracked-files=all").strip()
    output = (ROOT / args.output).resolve()
    assert output.is_relative_to(ROOT / OWNED) and not output.exists()
    baseline, head = tree(BASE), tree("HEAD")
    assert all(head.get(p) == oid for p, oid in baseline.items()), "Historical paths changed"
    allowed = (OWNED + "/", AUTHOR + "/", "docs/agent-reports/eld-f4-implementer/WP-0012/006_",
               "docs/agent-reports/eld-f4-reviewer/WP-0012/007_")
    added = sorted(set(head) - set(baseline))
    assert all(p.startswith(allowed) for p in added), "Unexpected added path"
    source_tree = tree(args.source_commit, AUTHOR)
    publication_tree = tree(args.author_publication, AUTHOR)
    assert all(head.get(p) == oid and publication_tree.get(p) == oid for p, oid in source_tree.items()), "Bound source changed"
    assert all(head.get(p) == oid for p, oid in publication_tree.items()), "Author publication not merged exactly"
    author_report = [p for p in tree(args.author_publication, "docs/agent-reports/eld-f4-implementer/WP-0012")
                     if Path(p).name.startswith("006_")]
    assert len(author_report) == 1 and author_report[0] in head
    own_paths = sorted(p for p in head if p.startswith(OWNED + "/"))
    author_paths = sorted(publication_tree) + author_report
    inputs = ["docs/implementation/WP-0012/eld-f4-implementer/helpers/run_wp0012_rehearsal.py",
              "docs/implementation/WP-0012/eld-f4-implementer/helpers/drive_rehearsal_edge.mjs",
              "docs/reviews/WP-0012/eld-f4-reviewer/author-001-review/helpers/run_wp0012_reviewer_rehearsal_v3.py",
              "docs/reviews/WP-0012/eld-f4-reviewer/preparation/helpers/drive_wp0012_edge_workflow.mjs",
              "docs/agent-reports/eld-f4-reviewer/WP-0012/002_2026-11-17_review_eld-f4-reviewer.md"]
    input_manifest = ROOT / OWNED / "preliminary/native-input-inventory.json"
    inputs += [item["path"] for item in json.loads(input_manifest.read_text())["files"]]
    files = [file_record(p) for p in sorted(set(own_paths + author_paths + inputs))]
    secret_settings = json.loads((ROOT / ".local/secrets/pg-local.json").read_text(encoding="utf-8"))
    secrets = [secret_settings[k].encode() for k in ("adminPassword", "migratorPassword", "appPassword") if secret_settings.get(k)]
    checked_links = []
    for path in own_paths + author_paths:
        raw = (ROOT / path).read_bytes()
        assert not any(secret in raw for secret in secrets), f"Local credential present in {path}"
        if path.endswith(".md"):
            for link in re.findall(r"\[[^\]]+\]\(([^)#?\s]+)(?:#[^)\s]*)?\)", raw.decode("utf-8")):
                if "://" in link or link.startswith("mailto:"):
                    continue
                assert (ROOT / path).parent.joinpath(link).resolve().exists(), f"Broken link {path}: {link}"
                checked_links.append({"source": path, "target": link})
    # Pure CPU observations; these do not inspect the GPU/model or claim a lease.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import run_wp0012_reviewer_rehearsal_v5 as reviewer
    ports = reviewer.observe_ports(reviewer.REVIEWER_PORTS, ROOT)
    pg = reviewer.run_cmd([str(ROOT / ".local/tools/pgsql-18.7-1/bin/pg_ctl.exe"), "status", "-D", str(ROOT / ".local/postgres-data")], cwd=ROOT)
    runs = reviewer.WRITABLE_DEMO_ROOT / "runs"
    entries = sorted(p.name for p in runs.iterdir()) if runs.exists() else []
    assert all(ports.get(str(p)) == [] for p in reviewer.REVIEWER_PORTS) and pg.returncode == 3 and entries == []
    runtime_identity = {"owner": reviewer.EXPECTED_OWNER, "conversation_id": reviewer.EXPECTED_CONVERSATION_ID,
                        "model": reviewer.EXPECTED_MODEL, "effort": reviewer.EXPECTED_EFFORT}
    product_trees = {p: git("rev-parse", f"HEAD:{p}").decode().strip()
                     for p in ("src", "web", "tests", "deploy", "workers/local_ocr", "ELedgerCare.slnx")}
    doc = {"schema": "eledgercare.wp0012.independent007-inventory/1", "utc": datetime.now(timezone.utc).isoformat(),
           "executing_head": git("rev-parse", "HEAD").decode().strip(), "source_candidate": args.source_commit,
           "author_publication": args.author_publication, "historical_base": BASE, "historical_paths_preserved": len(baseline),
           "bound_source_paths_verified": len(source_tree), "product_tree_objects": product_trees,
           "added_paths": added, "reviewer_owned_paths": own_paths, "author_input_paths": author_paths,
           "runtime_identity": runtime_identity, "files": files, "checked_markdown_links": checked_links,
           "reviewer_resources": {"ports": ports, "pg_status_exit": pg.returncode, "run_entries": entries},
           "checks_not_run": ["live OCR", "GPU query", "renderer import", "real PostgreSQL/API/browser startup", "broad unchanged product suite"],
           "inventory_excludes_itself": True}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"passed": True, "files": len(files), "preserved": len(baseline), "links": len(checked_links)}))


if __name__ == "__main__":
    main()
