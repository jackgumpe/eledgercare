"""Verify every WP-0031 packet file from its public, immutable integration URL."""
import argparse
import hashlib
import json
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


REPO = "jackgumpe/eledgercare"
BASE = "40fa358cd3c94efbf8fe9df93f188e7c02e1c6e4"
BRANCHES = ("coordination/bootstrap", "research/wp-0031-write8", "review/wp-0031-write8")
ROLES = ("eld-owner-probe", "eld-rd-reviewer", "eld-coordinator")


def git(*args):
    return subprocess.check_output(["git", *args])


def download(url):
    request = Request(url, headers={"User-Agent": "eLedgerCare-WP-0031", "Cache-Control": "no-cache"})
    for attempt in range(4):
        try:
            with urlopen(request, timeout=35) as reply:
                return reply.read()
        except HTTPError as exc:
            if exc.code not in (404, 429, 500, 502, 503, 504) or attempt == 3:
                raise
        except (TimeoutError, URLError):
            if attempt == 3:
                raise
        time.sleep(2 ** attempt)


def remote_heads():
    refs = ["refs/heads/" + branch for branch in BRANCHES]
    lines = git("ls-remote", "--exit-code", "origin", *refs).decode().splitlines()
    heads = {ref.removeprefix("refs/heads/"): sha for sha, ref in map(str.split, lines)}
    if set(heads) != set(BRANCHES):
        raise ValueError(f"Missing remote branch in {heads}")
    return heads


def verify(head):
    if not re.fullmatch("[0-9a-f]{40}", head):
        raise ValueError("Use the full published revision.")
    heads = remote_heads()
    if heads[BRANCHES[0]] != head:
        raise ValueError(f"Integration moved to {heads[BRANCHES[0]]}.")
    for ancestor in (BASE, *heads.values()):
        git("merge-base", "--is-ancestor", ancestor, head)

    changed = git("diff", "--name-only", "--no-renames", BASE, head).decode().splitlines()
    areas = tuple(f"docs/{area}/WP-0031/" for area in ("coordination", "research", "reviews"))
    report_dirs = tuple(f"docs/agent-reports/{role}/WP-0031/" for role in ROLES)
    unrelated = [p for p in changed if p not in ("INDEX.md", "CURRENT.md") and not p.startswith(areas + report_dirs)]
    if unrelated:
        raise ValueError(f"Unexpected paths since acceptance: {unrelated}")
    reports = [p for p in changed if p.startswith(report_dirs)]
    for sequence, folder in enumerate(report_dirs, 1):
        if len([p for p in reports if p.startswith(folder + f"{sequence:03}_")]) != 1:
            raise ValueError(f"Missing or duplicate canonical report in {folder}")

    def verify_path(path):
        expected = git("show", f"{head}:{path}")
        fetched = download(f"https://raw.githubusercontent.com/{REPO}/{head}/{quote(path)}")
        if fetched != expected:
            raise ValueError(f"Downloaded bytes differ: {path}")
        return path, {
            "bytes": len(fetched),
            "sha256": hashlib.sha256(fetched).hexdigest(),
            "git_blob": git("rev-parse", f"{head}:{path}").decode().strip(),
        }

    with ThreadPoolExecutor(max_workers=5) as pool:
        files = dict(pool.map(verify_path, changed))
    publications = {}
    for path in sorted(reports):
        commits = git("log", "--format=%H", "--diff-filter=A", f"{BASE}..{head}", "--", path).decode().splitlines()
        if len(commits) != 1:
            raise ValueError(f"Check publication lineage for {path}: {commits}")
        if git("rev-parse", f"{commits[0]}:{path}").decode().strip() != files[path]["git_blob"]:
            raise ValueError(f"Report changed since publication: {path}")
        publications[path] = commits[0]
    if heads != remote_heads():
        raise ValueError("Branch heads moved during the checks.")
    return {
        "verified_utc": datetime.now(timezone.utc).isoformat(),
        "repository": REPO,
        "accepted_base": BASE,
        "verified_integration": head,
        "live_branches": heads,
        "immutable_report_publications": publications,
        "downloaded_files": files,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("head")
    parser.add_argument("output", type=Path, help="New receipt file, or a fresh path in coordinator scratch")
    args = parser.parse_args()
    receipt = verify(args.head)
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(receipt, stream, indent=2)
        stream.write("\n")
    print(args.head, len(receipt["downloaded_files"]), "byte-for-byte public downloads")
