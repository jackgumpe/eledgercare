"""Verify all 42 pages and original attachments of the three locally assembled editions."""
import hashlib
import json
import subprocess
import sys
from io import BytesIO
from pathlib import Path
from pypdf import PdfReader

EDITION = "6fd7c96db7071c565c742fb27263e7c1b031f81c"
HIST = {"I":"Targeted-Depth-I-Mathematical-Specification.pdf",
        "II":"Targeted-Depth-II-Integrated-Concepts.pdf",
        "III":"Targeted-Depth-III-Coordinator-Handoff.pdf"}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def compare(inputs, folder):
    summaries = {}
    for roman,old_name in HIST.items():
        base = (inputs/old_name).read_bytes()
        note_name = f"Amendment-{roman}-02.1.pdf"
        note = subprocess.check_output(["git","show",EDITION+":docs/editions/WP-0045/papers/"+note_name])
        full = (folder/f"Targeted-Depth-{roman}-Complete-02.1.pdf").read_bytes()
        archive = PdfReader(BytesIO(base))
        amended = PdfReader(BytesIO(full))
        supplements = PdfReader(BytesIO(note))
        assert amended.attachments[old_name] == [base] and amended.attachments[note_name] == [note]
        for name,raw in archive.attachments.items():
            assert amended.attachments[name] == raw
        for name in ["Edition02-source.zip","Edition02.1-source.zip","Edition02.1-navigation.zip"]:
            assert len(amended.attachments[name]) == 1
        ordered = [*supplements.pages,*archive.pages]
        assert len(ordered)==len(amended.pages)
        for original,page in zip(ordered,amended.pages,strict=True):
            assert original.get_contents().get_data() == page.get_contents().get_data()
            assert original.extract_text() == page.extract_text()
            assert len(original.get("/Annots",[])) == len(page.get("/Annots",[]))
        summaries[roman] = {"original_pages":len(archive.pages),"amendment_pages":len(supplements.pages),
                            "complete_pages":len(amended.pages),"complete_sha256":sha(full),"amendment_sha256":sha(note),
                            "exact_predecessor_embedded":True,"inherited_attachments_compared":len(archive.attachments),
                            "shared_source_zip":sha(amended.attachments["Edition02.1-source.zip"][0])}
    handoff = PdfReader(folder/"Targeted-Depth-III-Complete-02.1.pdf")
    for roman in ["I","II"]:
        name=f"Targeted-Depth-{roman}-Complete-02.1.pdf"
        assert len(handoff.attachments[name])==1 and sha(handoff.attachments[name][0])==summaries[roman]["complete_sha256"]
    return summaries


if __name__=="__main__":
    result=compare(Path(sys.argv[1]),Path(sys.argv[2]))
    with Path(sys.argv[3]).open("x",encoding="utf8",newline="\n") as stream:
        json.dump(result,stream,indent=2)
        stream.write("\n")
