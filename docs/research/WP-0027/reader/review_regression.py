"""Replay the published reviewer's exact ordinary counterexample under the caller's CPU isolation."""
import ast
import io
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

from PIL import Image, ImageDraw
from reader import ROOT, digest, require

SOURCE = "2b4ee8f00bb9e72d6ea9596b4f40d3d6ecec26c8"
RESULT = "309b9cd834a2f91728cbb88f974f589fedb0ff58"
NAME = "source raster contains untranscribed text/ordinary"


def published(revision, file):
    return subprocess.check_output(["git", "-C", str(ROOT), "show", f"{revision}:docs/reviews/WP-0027/{file}"])


def replay(reader, target, prompt):
    # The module initializer configures the reviewer's scratch. Execute only the exact pure
    # fixture functions from its pinned source so the author keeps the assigned environment.
    src = published(SOURCE, "reader_challenge.py")
    tree = ast.parse(src)
    definitions = [node for node in tree.body if
                   (isinstance(node, ast.FunctionDef) and node.name in ("encode", "pages", "body", "test"))
                   or (isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
                       and node.targets[0].id == "AUTHORITY")]
    require(len(definitions) == 5, "review_fixture_definition_set")
    scope = dict(io=io, json=json, Image=Image, ImageDraw=ImageDraw, sha=digest)
    exec(compile(ast.Module(body=definitions, type_ignores=[]), "pinned-review-fixture", "exec"), scope)
    case = SimpleNamespace(name=NAME, sections=("p", "q", "r"), source=("p", "q", "r"), eos=True,
                           binding="hidden_ink", allowed="U")
    result = scope["test"](target, reader.tokenizer, reader.vocabulary, reader.added, reader.original, case, prompt)
    evidence = json.loads(published(RESULT, "reader-challenge-r1.json"))
    old, = [row for row in evidence["cases"] if row["case"] == NAME]
    keys = ("case", "native_sha256", "binding_sha256", "trusted_binding_sha256", "ordered_images", "expected")
    require(all(old[k] == result[k] for k in keys), "review_fixture_bytes_changed")
    return dict(reviewer_source=SOURCE, original_evidence=RESULT, historical=old, replay=result)
