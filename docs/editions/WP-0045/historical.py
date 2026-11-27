"""Re-run the actual unmodified Edition 02 small, stdlib-only reference on the pinned archive."""
import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile

ARCHIVE = "c351e8213018238b2d43f1979db7cfe771c49f0a8baab1054f092b544d3569f9"
EXPECTED = "d7e26e8d4e2f4932d4a54667c9461f912d8109cd5779b5e76da93f678e13fa66"
VECTORS = "51792f1d7af0bafe26dc450f4c37afd85dcc9a1b5aa9bc4e055f0a84e3dcf67f"


def sha(data):
    return sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    data = args.archive.read_bytes()
    assert sha(data) == ARCHIVE and sys.version_info[:3] == (3,12,10)
    with ZipFile(BytesIO(data)) as z:
        for name in ("reference.py","profile.json","vectors.json","expected.txt"):
            (args.out / name).write_bytes(z.read(name))
    expected = (args.out / "expected.txt").read_bytes()
    vectors = (args.out / "vectors.json").read_bytes()
    assert sha(expected) == EXPECTED and sha(vectors) == VECTORS
    child = subprocess.run([sys.executable, "-I", "-B", "reference.py"], cwd=args.out,
                           capture_output=True, timeout=30, check=False)
    (args.out / "raw.stdout").write_bytes(child.stdout)
    (args.out / "stderr.txt").write_bytes(child.stderr)
    canonical = child.stdout.replace(b"\r\n",b"\n")
    (args.out / "canonical.stdout").write_bytes(canonical)
    receipt = {"archive_sha256":ARCHIVE, "vectors_sha256":sha(vectors), "vectors_bytes":len(vectors),
               "reference_sha256":sha((args.out / "reference.py").read_bytes()),
               "expected_lf_sha256":sha(expected), "expected_bytes":len(expected),
               "exit":child.returncode,"stderr_sha256":sha(child.stderr),
               "raw_sha256":sha(child.stdout), "raw_bytes":len(child.stdout),
               "crlf_count":child.stdout.count(b"\r\n"), "canonical_sha256":sha(canonical),
               "canonical_bytes":len(canonical), "canonical_equal":canonical == expected,
               "raw_equal": child.stdout == expected, "printed_vector_passes":canonical.count(b" PASS "),
               "printed_final_line":canonical.splitlines()[-1].decode() if canonical else None}
    (args.out / "historical.json").write_bytes((json.dumps(receipt,sort_keys=True,indent=2)+"\n").encode())
    print(json.dumps(receipt))
    if child.returncode != 0 or child.stderr or canonical != expected:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
