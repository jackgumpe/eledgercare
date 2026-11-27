"""Verify supplied archive identities and checks under Python 3.12 with pypdf."""
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import zipfile

import pypdf


def git(rev, path):
    return subprocess.check_output(["git", "show", rev + ":" + path])


def verify(data, pin):
    assert len(data) == pin["bytes"] and hashlib.sha256(data).hexdigest() == pin["sha256"]


def main(downloads, scratch):
    reservation = "d497bae7db42589bd2ede512f932b0488f6309cd"
    manifest = json.loads(git(reservation, "docs/coordination/WP-0043/inputs.json"))
    results = {"python": sys.version, "pypdf": pypdf.__version__, "packages": {}}
    for name, pin in manifest.items():
        raw = (downloads / name).read_bytes()
        verify(raw, pin)
        doc = pypdf.PdfReader(io.BytesIO(raw))
        assert len(doc.pages) == pin["pages"] and set(doc.attachments) == set(pin["attachments"])
        for member, apin in pin["attachments"].items():
            payload, = doc.attachments[member]
            verify(payload, apin)
            if "members" not in apin:
                continue
            root = scratch / Path(member).stem
            with zipfile.ZipFile(io.BytesIO(payload)) as z:
                assert sorted(z.namelist()) == sorted(apin["members"])
                for filename, zpin in apin["members"].items():
                    path = PurePosixPath(filename)
                    assert not path.is_absolute() and ".." not in path.parts and "\\" not in filename
                    data = z.read(filename)
                    verify(data, zpin)
                    target = root / path
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)
            script = next(k for k in apin["members"] if k.endswith(".py"))
            cmd = [sys.executable, "-I", "-B", str(root / script)]
            proc = subprocess.run(cmd, cwd=root, capture_output=True, timeout=60)
            proc.check_returncode()
            assert not proc.stderr
            results["packages"][member] = {"sha256": apin["sha256"], "script": script,
                "script_sha256": apin["members"][script]["sha256"], "exit": proc.returncode,
                "members_verified": len(apin["members"]), "stdout": proc.stdout.decode().splitlines()}

    field = json.loads(git(reservation, "docs/coordination/WP-0042/field-baseline.json"))
    evidence = {}
    for path, pin in field["historical_objects"].items():
        data = git(field["base"], path)
        verify(data, pin)
        assert data == (scratch / "f07-math-check" / "evidence" / Path(path).name).read_bytes()
        evidence[path.split(".")[-2]] = data
    ids = json.loads(evidence["token_ids"])
    text = evidence["raw"]
    obs = json.loads(evidence["observation"])
    assert [i for i, token in enumerate(ids) if token == 128827] == [0, 1145, 1896]
    assert text[1823:1838] == b"<td>$28.50</td>" and text[1880:1886] == b"$28.50"
    assert 1 not in ids and len(ids) == 2558 and len(text) == 7617
    assert obs["cache"]["final_seq_len"] == 3385 and obs["native"]["finish_reason"] == "stop"
    stats = []
    for g in range(618, 623):
        h = ids[:g+1]
        # For each proper suffix length, search all completed prefixes for the same tuple.
        hits = [j for j in range(1, 35) if any(h[i:i+j] == h[-j:]
                for i in range(max(0, len(h)-1024), len(h)-j))]
        stats.append([len(h), len(h)-34, max(hits, default=0), ids[g+1]])
        assert h.count(128827) == 1 and h[0] == 128827 and 34 not in hits
    assert [x[2] for x in stats] == [2,0,0,1,2] and sum(x[1] for x in stats) == 2935
    assert [x[3] for x in stats] == [6,1449,16,1328,128822]
    results["independent_rows_n_starts_max_suffix_y"] = stats
    results["historical_document"] = [len(ids), len(text), obs["cache"]["final_seq_len"]]
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
