"""Request construction, fixed worker pins, and checks against independent fixture truth."""
import hashlib
import json
import re
import uuid
from pathlib import Path
from fixtures import HERE, ROOT, PAGES, TEXT, TRUTH

Q0 = Path("C:/Users/jackg/eLedgerCare-Q0/WP-0005")
PYTHON = Q0 / "venv/Scripts/python.exe"
GPU = "GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d"
WORKER = ROOT / "workers/local_ocr"
REFERENCE = ROOT / "docs/implementation/WP-0012/eld-f4-implementer/rehearsal-003/evidence/attempts/attempt-01a1ea6a-6642-7939-8407-e2aba617b795"
SHA = {
    "A": "25c14530845cad96329b528f860032c27a1259ed46de3ccb56f0e57730aa0858",
    "B": "ef5d8f09658355dae46d54724a8cbeb89bc625362e41e8c4e154461d81a604c8",
    "S": "47b2df6a33309bdc056c852f7f20c6c5824c4adb5a8b785fda05ed81e34489cd",
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def dump(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, allow_nan=False, indent=2) + "\n", encoding="utf-8")


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def materialize(path, key):
    request = read(REFERENCE / "request.json")
    data = PAGES[key].read_bytes()
    assert digest(data) == SHA[key]
    document = path / "input" / (key + ".pdf")
    document.parent.mkdir(exist_ok=True)
    if not document.exists():
        document.write_bytes(data)
    assert document.read_bytes() == data
    request.update(
        document_id=str(uuid.uuid4()), job_id=str(uuid.uuid4()), attempt_id=str(uuid.uuid4()),
        writable_runtime_root=str(path.parent.parent), input_pdf_path=str(document),
        expected_input_sha256=SHA[key], expected_input_byte_length=len(data),
    )
    dump(path / "request.json", request)


def assess(key, output):
    env = read(output / "envelope.json")
    assert env["status"] == "completed", env.get("failure")
    raw = (output / "raw_output.utf8.bin").read_bytes()
    text = raw.decode("utf-8", "strict")
    assert digest(raw) == env["output"]["sha256"] and env["input"]["sha256"] == SHA[key]
    score = {"fixture": key, "sha256": digest(raw), "bytes": len(raw), "output_tokens": env["output"]["output_token_count"],
             "raster": env["diagnostics"]["rendered_pages"], "timings": env["timings"]}
    if key in TEXT:
        # Only remove the native page token and bounded structural block/box tags. Preserve case and punctuation.
        content = text.replace("<PAGE>", " ")
        content = re.sub(r"<BLOCK>\w+\[\d+, ?\d+, ?\d+, ?\d+\]<FORK>", " ", content)
        normalized = " ".join(content.split())
        score.update(expected=TEXT[key], normalized=normalized, exact_ordered_text=normalized == TEXT[key])
    else:
        truth = read(TRUTH)
        fields = {}
        for field in truth["expected_fields"]:
            target = field["printed_text"]
            if field["value_type"] == "boolean_mark":
                target = field["label_printed"] + " " + target
            fields[field["field_id"]] = target in text
        cells = {}
        actual_tables = re.findall(r"<table>(.*?)</table>", text, re.S)
        for ti, table in enumerate(truth["expected_tables"]):
            body = actual_tables[ti] if ti < len(actual_tables) else ""
            rows = re.findall(r"<tr>(.*?)</tr>", body, re.S)[1:]
            for ri, expected_row in enumerate(table["rows"]):
                actual = re.findall(r"<td>(.*?)</td>", rows[ri], re.S) if ri < len(rows) else []
                for ci, column in enumerate(table["column_ids"]):
                    wanted = expected_row["cells"][column]["printed_text"]
                    observed = actual[ci] if ci < len(actual) else None
                    cells["/".join((table["table_id"], expected_row["row_id"], column))] = {
                        "expected": wanted, "observed": observed, "exact": wanted == observed}
        score.update(printed_fields_present=fields, table_cells=cells,
                     identical_to_accepted_raw=raw == (REFERENCE / "output/raw_output.utf8.bin").read_bytes())
    return score
