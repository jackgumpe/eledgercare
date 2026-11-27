"""Rebind the unchanged scientific PDFs with original navigation from the predecessor catalog."""
import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import sys
from zipfile import ZipFile

import pypdf
from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, DictionaryObject, NameObject, NumberObject, TextStringObject

HERE = Path(__file__).resolve().parent
# Beside the repository source or within the extracted frozen source tree.
sys.path.insert(0, str(HERE.parent))
import build

FROZEN = "18ac0a336b04bf46aaec670fc2a37c53f358823c3a733634ddf7a211336148d8"
PATCH = "Edition02.1-navigation.zip"
NAMES = {r:f"Targeted-Depth-{r}-Complete-02.1.pdf" for r in build.PAPERS}
SUPPLEMENTS = {"I":"6ee4b47dde4f2ff4147551f1b4e2e54d919a9faf868b2099b3005224db7e0866",
               "II":"6e42583def967803bc72df6ffdc3f7660a4bbb430a04d3a86ec23c7fd50c6eac",
               "III":"ddcffc7bd4e059590c842540dda851e943334de7473993d0f0b0e56a57aa9576"}


def set_labels(writer, supplement, old):
    numbers = ArrayObject()
    for i,label in enumerate([f"02.1-{j+1}" for j in range(supplement)] + old.page_labels):
        numbers.extend([NumberObject(i),DictionaryObject({NameObject("/P"): TextStringObject(label)})])
    writer.root_object[NameObject("/PageLabels")] = DictionaryObject({NameObject("/Nums"):numbers})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", type=Path)
    parser.add_argument("frozen_source", type=Path)
    parser.add_argument("supplements", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    assert sys.version_info[:3] == (3,12,10) and pypdf.__version__ == "6.16.2"
    args.out.mkdir(parents=True, exist_ok=False)
    original, _, _ = build.verify(args.inputs)
    frozen = args.frozen_source.read_bytes()
    assert build.digest(frozen) == FROZEN
    patch = build.archive({k:(HERE/k).read_bytes() for k in
                           ("package.py","audit.py","render.ps1","README.md")})
    (args.out/PATCH).write_bytes(patch)
    companions = {}
    result = {"unchanged_public_notes":SUPPLEMENTS, "unchanged_source_zip":FROZEN,
              "navigation_zip":build.digest(patch), "complete":{}}
    for key,name in build.PAPERS.items():
        old = PdfReader(BytesIO(original[name]))
        note_name = "Amendment-" + key + "-02.1.pdf"
        note = (args.supplements/note_name).read_bytes()
        assert build.digest(note) == SUPPLEMENTS[key]
        document = PdfReader(BytesIO(note))
        writer = PdfWriter(clone_from=old)
        for i,page in enumerate(document.pages):
            writer.insert_page(page,i)
        bookmarks = writer.get_outline_root()
        first, last = bookmarks.raw_get("/First"), bookmarks.raw_get("/Last")
        operative = writer.add_outline_item("Edition 02.1 - operative amendment", 0)
        historical = writer.add_outline_item("Edition 02 - historical text", len(document.pages))
        # Move the two newly appended siblings as one list prefix. Original
        # siblings, descendants, destination objects and open counts stay intact.
        bookmarks[NameObject("/First")] = operative
        bookmarks[NameObject("/Last")] = last
        operative.get_object().pop("/Prev")
        historical.get_object()[NameObject("/Next")] = first
        first.get_object()[NameObject("/Prev")] = historical
        last.get_object().pop("/Next")
        writer.open_destination = writer.pages[0]
        writer.add_metadata({"/Title":f"Targeted recurrent depth {key} - complete research Edition 02.1",
                             "/Author":"Original team (Edition 02); eld-depth-author (02.1 amendment)"})
        set_labels(writer, len(document.pages), old)
        extra = {name:original[name], note_name:note, build.GEMINI:original[build.GEMINI],
                 build.ZIP_NAME:frozen, PATCH:patch}
        if key == "III":
            extra.update(companions)
            extra["companions-02.1.json"] = build.json_bytes({k:build.digest(v) for k,v in companions.items()})
        assert not set(extra).intersection(old.attachments)
        for filename, data in sorted(extra.items()):
            writer.add_attachment(filename, data)
        stream = BytesIO()
        writer.write(stream)
        data = stream.getvalue()
        (args.out / NAMES[key]).write_bytes(data)
        result["complete"][NAMES[key]] = {"sha256":sha256(data).hexdigest(),"bytes":len(data)}
        companions[NAMES[key]] = data
    (args.out/"navigation.json").write_bytes(build.json_bytes(result))


if __name__ == "__main__":
    main()
