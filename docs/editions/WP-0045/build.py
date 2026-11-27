"""Rebuild signed-off inputs, independent operative PDFs and complete private editions."""
import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import sys
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import pypdf
from pypdf import PdfReader, PdfWriter

from typeset import pdf, sections

HERE = Path(__file__).resolve().parent
PIN_FILE = HERE.parent / "source-pins.json"
if not PIN_FILE.exists():
    PIN_FILE = HERE.parents[1] / "coordination" / "WP-0045" / "source-pins.json"
PINS = json.loads(PIN_FILE.read_bytes())
PAPERS = dict(zip(("I","II","III"), [p for p in PINS if p.startswith("Targeted-Depth-")]))
GEMINI = next(p for p in PINS if p.startswith("PGDA"))
TEXTS = ["shared.md","model-02.1.tex","profile-02.1.json","fixtures.json","clauses.py",
         "typeset.py","build.py","trial.py","historical.py","paper-I.md","paper-II.md","paper-III.md"]
ZIP_NAME = "Edition02.1-source.zip"


def digest(data):
    return sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def archive(files):
    output = BytesIO()
    with ZipFile(output, "w") as z:
        for path, data in sorted(files.items()):
            member = ZipInfo(path, (2026, 11, 27, 0, 0, 0))
            member.create_system = 3
            member.external_attr = 0o100644 << 16
            z.writestr(member, data, compress_type=ZIP_DEFLATED, compresslevel=9)
    return output.getvalue()


def verify(inputs):
    actual = {}
    for name, expected in PINS.items():
        if isinstance(expected, str):
            data = (inputs / name).read_bytes()
            if digest(data) != expected:
                raise ValueError(f"wrong bound precursor {name}")
            actual[name] = data
    members = {}
    for name in [*PAPERS.values(), GEMINI]:
        reader = PdfReader(BytesIO(actual[name]))
        rebuilt = "\n\n".join(p.extract_text() for p in reader.pages)
        text_path = inputs / (name + ".txt")
        if text_path.exists() and text_path.read_text(encoding="utf-8-sig") != rebuilt:
            raise ValueError(f"transcript differs from PDF {name}")
        attached = {k: v for k,v in reader.attachments.items()}
        if name != GEMINI and attached["Edition02-source.zip"] != [actual["Edition02-source.zip"]]:
            raise ValueError(f"embedded source differs {name}")
        if name == PAPERS["III"]:
            for k in [PAPERS["I"], PAPERS["II"], "companions.json"]:
                if attached[k] != [actual[k]]:
                    raise ValueError(f"embedded companion differs {k}")
        members[name] = {"pages": len(reader.pages), "sha256":digest(actual[name]),
                         "attachments":{k:list(map(digest, v)) for k,v in attached.items()}}
    with ZipFile(BytesIO(actual["Edition02-source.zip"])) as z:
        original = {k:z.read(k) for k in z.namelist() if not k.endswith("/")}
    for name, data in original.items():
        staged = inputs / "edition02" / name
        if staged.exists() and staged.read_bytes() != data:
            raise ValueError(f"staged member differs {name}")
    for line in original["SHA256SUMS.txt"].decode().splitlines():
        expected, name = line.split("  ", 1)
        if digest(original[name]) != expected:
            raise ValueError(f"member inventory mismatch {name}")
    return actual, original, members


def operative(roman, source):
    paper = source[f"paper-{roman}.md"].decode()
    title = paper.splitlines()[0][2:]
    text = sections(paper) + sections(source["shared.md"].decode())
    provenance = ["Local amendment and derivations by eld-depth-author for eLedgerCare. "
                  "Predecessor: the supplied team's Targeted recurrent depth, Research Edition 02, "
                  "prepared for Jack Gumpel. Independent prior advisory: Gemini, Co-Cloud Coordinator "
                  "Review Return, 27 November 2026 (seven pages). The private full edition carries "
                  "the actual predecessor, all inherited attachments and that advisory, with original attribution.",
                  "Use the three operative shared sections above wherever an earlier statement, equation, "
                  "TOKEN or RECONCILE conflicts. Other clauses and proofs remain in the exact predecessor. "
                  "The following pins identify the reviewed objects in their entirety, including embedded files.",
                  "Repository revision of supplied sources: " + PINS["originals"]["source_revision"]]
    for label, value in [("This paper's Edition 02 PDF", PINS[PAPERS[roman]]),
                         ("Edition 02 common source ZIP", PINS["Edition02-source.zip"]),
                         ("Gemini advisory PDF", PINS[GEMINI]),
                         ("New shared normative TeX overlay", digest(source["model-02.1.tex"])),
                         ("New profile overlay", digest(source["profile-02.1.json"])),
                         ("New shared definitions and proofs", digest(source["shared.md"])),
                         ("New public finite examples and predicted rows", digest(source["fixtures.json"]))]:
        provenance.append(label + "\n" + value)
    provenance.append("Reproduction: apply build.py to the pinned PDFs and source, then run historical.py "
                      "on the unaltered reference and trial.py public on the new cases. The source, shared "
                      "equations and examples are embedded alongside each new public paper. Paper III binds "
                      "both complete companion editions. Independent results and release decisions have separate receipts.")
    text.append(("Source bindings and reproduction", provenance))
    extras = {k:v for k,v in source.items() if k in {"shared.md","model-02.1.tex","profile-02.1.json",
                                                     "fixtures.json",f"paper-{roman}.md","clauses.py"}}
    return pdf(roman, title, text, extras)


def assemble(roman, note, actual, bundle, companions):
    filename = PAPERS[roman]
    old_data = actual[filename]
    prior = PdfReader(BytesIO(old_data))
    writer = PdfWriter()
    writer.add_metadata({"/Title": "Targeted recurrent depth " + roman + " - complete Edition 02.1",
                         "/Author": "Original team (Edition 02); eld-depth-author (02.1 amendment)"})
    writer.append(PdfReader(BytesIO(note)), import_outline=False)
    writer.append(prior, import_outline=False)
    writer.add_outline_item("Edition 02.1 - operative amendment", 0)
    writer.add_outline_item("Edition 02 - preserved historical text", len(PdfReader(BytesIO(note)).pages))
    files = {filename: old_data, GEMINI:actual[GEMINI], ZIP_NAME:bundle,
             f"Amendment-{roman}-02.1.pdf": note, **companions}
    for name, values in prior.attachments.items():
        if len(values) != 1 or name in files:
            raise ValueError(f"ambiguous inherited attachment {name}")
        files[name] = values[0]
    for name,data in sorted(files.items()):
        writer.add_attachment(name, data)
    output = BytesIO()
    writer.write(output)
    result = output.getvalue()
    readback = PdfReader(BytesIO(result))
    if {k:v for k,v in readback.attachments.items()} != {k:[v] for k,v in files.items()}:
        raise ValueError("attachment metadirectory differs after complete assembly")
    historical = list(readback.pages)[-len(prior.pages):]
    if any(a.extract_text() != b.extract_text() for a,b in zip(historical, prior.pages, strict=True)):
        raise ValueError("historical page text differs")
    return result, {"sha256":digest(result),"bytes":len(result),"pages":len(readback.pages),
                    "attachments":{k:digest(v) for k,v in files.items()}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("out", type=Path)
    parser.add_argument("--inputs", type=Path)
    args = parser.parse_args()
    if pypdf.__version__ != "6.16.2" or sys.version_info[:3] != (3,12,10):
        raise ValueError("pin CPython 3.12.10 and pypdf 6.16.2 for deterministic PDF writing")
    args.out.mkdir(parents=True, exist_ok=False)
    source = {k:(HERE / k).read_bytes() for k in TEXTS}
    notes = {k:operative(k,source) for k in PAPERS}
    for k,note in notes.items():
        (args.out / f"Amendment-{k}-02.1.pdf").write_bytes(note)
    if not args.inputs:
        return
    actual, original, inventory = verify(args.inputs)
    material = {"edition02/" + k:v for k,v in original.items()}
    material["Edition02-source.zip"] = actual["Edition02-source.zip"]
    material.update({"edition021/" + k:v for k,v in source.items()})
    material["edition021/tex/model.tex"] = original["tex/model.tex"] + b"\n" + source["model-02.1.tex"]
    profile = json.loads(original["profile.json"])
    profile.update(json.loads(source["profile-02.1.json"]))
    material["edition021/profile.json"] = json_bytes(profile)
    material["source-pins.json"] = PIN_FILE.read_bytes()
    schedule = HERE.parent / "schedule.json"
    if not schedule.exists():
        schedule = HERE.parents[1] / "coordination" / "WP-0045" / "schedule.json"
    material["schedule.json"] = schedule.read_bytes()
    material["README.txt"] = (b"The original Edition 02 tree and source ZIP are immutable.\n"
                              b"edition021/ contains the operative source including the resolved shared TeX and profile.\n"
                              b"Rebuild from this extracted zip: python -B edition021/build.py OUT --inputs INPUTS\n"
                              b"INPUTS holds the four original PDFs, Edition02-source.zip and companions.json.\n")
    material["SHA256SUMS.txt"] = "".join(f"{digest(v)}  {k}\n" for k,v in sorted(material.items())).encode()
    bundle = archive(material)
    (args.out / ZIP_NAME).write_bytes(bundle)
    result = {"predecessors":inventory, "source_zip_sha256":digest(bundle),
              "resolved_model_sha256":digest(material["edition021/tex/model.tex"]),
              "resolved_profile_sha256":digest(material["edition021/profile.json"]),
              "public_pdfs":{k:digest(v) for k,v in notes.items()}, "complete_pdfs":{}}
    companions = {}
    for roman, note in notes.items():
        extra = {} if roman != "III" else {**companions,"companions-02.1.json":json_bytes(
            {k:digest(v) for k,v in companions.items()})}
        data, receipt = assemble(roman, note, actual, bundle, extra)
        name = f"Targeted-Depth-{roman}-Complete-02.1.pdf"
        (args.out / name).write_bytes(data)
        result["complete_pdfs"][name] = receipt
        companions[name] = data
    (args.out / "assembly.json").write_bytes(json_bytes(result))


if __name__ == "__main__":
    main()
