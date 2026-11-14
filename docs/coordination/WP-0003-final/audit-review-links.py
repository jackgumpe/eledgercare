"""Read-only audit of Markdown file links and line bounds in exact Git objects.

This verifies locations, not whether the cited source supports the prose.
"""
import argparse
import json
import posixpath
import re
import subprocess
from urllib.parse import unquote, urlsplit

parser = argparse.ArgumentParser()
parser.add_argument("revision")
parser.add_argument("paths", nargs="+")
args = parser.parse_args()

def git(*parts):
    return subprocess.check_output(["git", *parts], stderr=subprocess.DEVNULL)

findings = []
checked = 0
for path in args.paths:
    text = git("show", f"{args.revision}:{path}").decode("utf-8")
    for match in re.finditer(r"\[[^\]\n]+\]\(([^)\n]+)\)", text):
        target = match.group(1).strip("<>")
        parts = urlsplit(target)
        revision = args.revision
        if parts.scheme:
            pinned = re.fullmatch(r"/jackgumpe/eledgercare/blob/([0-9a-f]{40})/(.+)", parts.path)
            if parts.netloc != "github.com" or not pinned:
                continue
            revision, resolved = pinned.groups()
        elif not parts.path:
            continue
        else:
            resolved = posixpath.normpath(posixpath.join(posixpath.dirname(path), unquote(parts.path)))
        checked += 1
        issue = {"document": path, "document_line": text.count("\n", 0, match.start()) + 1,
                 "target": target, "revision": revision, "resolved_path": resolved}
        try:
            content = git("show", f"{revision}:{resolved}")
        except subprocess.CalledProcessError:
            issue["error"] = "missing target Git object"
            findings.append(issue)
            continue
        bounds = re.fullmatch(r"L(\d+)(?:-L?(\d+))?", parts.fragment)
        if bounds:
            first = int(bounds[1])
            last = int(bounds[2] or bounds[1])
            length = len(content.splitlines())
            if not 1 <= first <= last <= length:
                issue.update(error="line bounds outside file", target_lines=length)
                findings.append(issue)

print(json.dumps({"revision": args.revision, "documents": args.paths,
                  "checked_links": checked, "findings": findings,
                  "limits": "Markdown file links and Git line bounds only; no semantic claim validation."}, indent=2))
