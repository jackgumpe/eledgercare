"""Verify accepted application and immutable review objects in a merge, without executing them."""
import argparse
import json
import subprocess

p = argparse.ArgumentParser()
p.add_argument("--design", required=True)
p.add_argument("--candidate", required=True)
p.add_argument("--review", required=True)
p.add_argument("--merged", required=True)
a = p.parse_args()

def git(*args):
    return subprocess.check_output(["git", *args], stderr=subprocess.DEVNULL).decode("utf-8").strip()

def entry(revision, path):
    return git("ls-tree", revision, "--", path)

changed = git("diff", "--name-only", a.design, a.candidate).splitlines()
candidate_differences = [path for path in changed if entry(a.candidate, path) != entry(a.merged, path)]
tree = git("ls-tree", "-r", "--name-only", a.candidate).splitlines()
prefixes = ("src/", "tests/", "web/", "deploy/", "evaluation/product-smoke/", "workers/", ".config/")
roots = {"global.json", "Directory.Build.props", "Directory.Packages.props", "NuGet.Config", "ELedgerCare.slnx"}
inputs = [path for path in tree if path.startswith(prefixes) or path in roots]
input_differences = [path for path in inputs if entry(a.candidate, path) != entry(a.merged, path)]
extra_inputs = [path for path in git("ls-tree", "-r", "--name-only", a.merged).splitlines()
                if (path.startswith(prefixes) or path in roots) and path not in tree]
review_paths = git("diff", "--name-only", a.candidate, a.review).splitlines()
review_differences = [path for path in review_paths if entry(a.review, path) != entry(a.merged, path)]
all_equal = not (candidate_differences or input_differences or extra_inputs or review_differences)
print(json.dumps({"design": a.design, "candidate": a.candidate, "review": a.review, "merged": a.merged,
                  "candidate_changed_paths": len(changed), "application_inputs": len(inputs),
                  "author_and_reviewer_evidence_paths": len(review_paths),
                  "candidate_changed_path_differences": candidate_differences,
                  "application_input_differences": input_differences, "extra_application_inputs": extra_inputs,
                  "author_and_reviewer_evidence_differences": review_differences,
                  "all_compared_git_objects_identical": all_equal,
                  "limits": "Git modes/blobs only; unchanged runtime suites are attributed to their actual author/reviewer executions."}, indent=2))
raise SystemExit(0 if all_equal else 1)
