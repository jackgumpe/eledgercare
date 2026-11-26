"""PDF, policy, native-source and field checks; PDF parsing is separate from the CPU suite."""
from hashlib import sha1, sha256
import json
from pathlib import Path
import subprocess

from pypdf import PdfReader, __version__ as pdf_version

BASE = "f5e68668a5999a12ba399eb0f5103ffa835e4b30"
RESERVATION = "a947ddbab8f71df64b5c6640ef94923c32e29cd5"
SCRATCH = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0042/review")
CACHE = Path("C:/Users/jackg/eLedgerCare-Q0/WP-0005")


def git(rev, path):
    return subprocess.check_output(["git", "show", rev + ":" + path])


def digest(data):
    return sha256(data).hexdigest()


def blob(data):
    return sha1(b"blob %d\0" % len(data) + data).hexdigest()


def main():
    prefix = "docs/coordination/WP-0042/"
    manifest = json.loads(git(RESERVATION, prefix+"inputs.json"))
    pdf = Path("C:/Users/jackg/Downloads") / manifest["pdf"]
    data = pdf.read_bytes()
    assert (len(data), digest(data)) == (manifest["bytes"], manifest["sha256"])
    outer = PdfReader(pdf)
    assert len(outer.pages) == 21
    assert set(outer.attachments) == set(manifest["attachments"]) and len(outer.attachments) == 14
    historical = 0
    staged = 0
    attachments = {}
    for name, expected in manifest["attachments"].items():
        entries = outer.attachments[name]
        assert len(entries) == 1 and Path(name).name == name
        asset = entries[0]
        assert (len(asset),digest(asset)) == (expected["bytes"],expected["sha256"])
        (SCRATCH / name).write_bytes(asset)
        target = None
        if "path" in expected:
            assert asset == git(BASE, expected["path"]) and blob(asset) == expected["git_blob"]
            target = BASE + ":" + expected["path"]
            historical += 1
        elif name in ["AGENTS-research-handoffs.patch","Research-handoff-authoring-policy.md","six_controls.py","six-results.txt"]:
            assert asset == git(RESERVATION, prefix + name)
            target = RESERVATION + ":" + prefix + name
            staged += 1
        attachments[name] = {"bytes":len(asset), "sha256":digest(asset),"verified_git_source":target}
    assert (historical,staged) == (7,4)
    gem = PdfReader(SCRATCH / "Gemini-original-review.pdf")
    assert len(gem.pages) == 10
    assert all(a.extract_text() == b.extract_text() and a.get_contents().get_data() == b.get_contents().get_data()
               for a,b in zip(gem.pages, outer.pages[11:]))
    draft = PdfReader(SCRATCH / "Draft-2-mathematical-handoff.pdf")
    assert len(draft.pages) == 15 and "(14)" in draft.pages[4].extract_text()
    agents = git(BASE, "AGENTS.md")
    assert agents == git(RESERVATION, "AGENTS.md")
    marker = b"## Mathematics in architecture handoffs"
    assert agents.count(marker) == 1
    split = agents.index(marker)
    policy = outer.attachments["Research-handoff-authoring-policy.md"][0]
    expected = agents[:split] + policy + b"\n" + agents[split:]
    patch = SCRATCH/"AGENTS-research-handoffs.patch"
    # An external scratch path prevents discovery of the reviewer's working index.
    dest = SCRATCH/"patch"
    dest.mkdir(exist_ok=True)
    (dest/"AGENTS.md").write_bytes(agents)
    for args in [["--check"],[]]:
        subprocess.run(["git","-c","core.autocrlf=false","apply","--no-index",*args,str(patch)],cwd=dest,check=True)
    actual = (dest/"AGENTS.md").read_bytes()
    assert actual == expected
    source = json.loads(outer.attachments["WP0041-model-source.json"][0])
    native = {}
    for name in ["modeling_unlimitedocr.py","modeling_deepseekv2.py","_sparse_base_impl.py","config.json","dash_attention.py"]:
        raw = (CACHE/"models/Unlimited_OCR_2_04809669"/name).read_bytes()
        assert digest(raw) == source["files"][name]["sha256"] and blob(raw)==source["files"][name]["git_blob"]
        native[name] = digest(raw)
    for name in ["transformers/cache_utils.py","torch/_torch_docs.py"]:
        raw = (CACHE/"venv/Lib/site-packages"/name).read_bytes()
        assert digest(raw) == source["versions"]["runtime_source_sha256"][name]
        native[name] = digest(raw)
    field = json.loads(outer.attachments["WP0041-field.json"][0])
    ids = text = None
    for path in field["source_blobs"]:
        if path.endswith(("F07.warm1.token_ids.json","F07.warm1.raw.txt","F07.warm1.observation.json")):
            raw = git(field["base"],path)
            assert digest(raw) == field["source_blobs"][path]["sha256"]
            if path.endswith("token_ids.json"):
                ids = json.loads(raw)
            if path.endswith(".txt"):
                text = raw
    assert len(ids) == 2558 and ids[618:624] == [128821,6,1449,16,1328,128822]
    assert text[1823:1838] == b"<td>$28.50</td>" and text.count(b"$28.50") >= 2
    assert [827+row["consume_index"] for row in field["prediction_alignment"]] == list(range(1445,1450))
    assert field["historical_call_kwargs"]["ngram_window"] == 1024
    result = {"pdf":[len(data),digest(data)],"pypdf":pdf_version,"attachments":attachments,
              "draft_pages":15,"gemini_matching_content_streams_and_text":10,"native":native,
              "policy":{"base_length":len(agents),"base_git":blob(agents),"base_sha256":digest(agents),
                        "prior_math_offset":split,"target_length":len(expected),"target_git":blob(actual),
                        "target_sha256":digest(actual),"math_through_eof_sha256":digest(agents[split:]),
                        "prefix_through_insertion_sha256":digest(agents[:split]),"policy_bytes":len(policy)},
              "historical_target":{"price_occurrences":text.count(b"$28.50"),"generated_count":len(ids),
                    "prefix_index":618,"input_start":1445,"context_ids":ids[618:624],"ngram_window":1024}}
    print(json.dumps(result,indent=2))


if __name__ == "__main__":
    main()
