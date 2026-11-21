"""Quantify the physical directory/layout association with T3 status on public development PDFs."""
from collections import Counter
from contextlib import closing
import json
from pathlib import Path
import re
import sys

import pypdfium2 as pdfium

sys.path.insert(0,str(Path(__file__).resolve().parent))
from dev_layout_audit import CUSTODY, PIN, pinned, sha


def extract_page(doc,i):
    with closing(doc[i]) as page:
        with closing(page.get_textpage()) as layer:
            return layer.get_text_bounded().replace("\r","")


def axes(root, pairs, pdf_hashes):
    records = []
    for pair in pairs:
        for member in pair["members"]:
            ident = member["binder"]
            data = (root/"pdf"/(ident+".pdf")).read_bytes()
            assert sha(data) == pdf_hashes[ident]
            with pdfium.PdfDocument(data) as doc:
                last = re.search(r"MAINT-SUMMARY\s+(\d+)\s+(\d+)",extract_page(doc,len(doc)-2))
                if not last:
                    break
                assert last[1] == last[2]
                child = re.search(r"Schedule subtotal: (\d+)",extract_page(doc,len(doc)-5))
                p1 = extract_page(doc,0)
                directory = re.search(r"Owners: (\w+) / (\w+)",p1)
                owner = re.search(r"Ledger: (\w+)",p1)[1]
                # One observation per twin pair, indexed to a fixed lexical choice
                # to ensure that side order and repeated matched horizons are explicit.
                if owner != min(directory.groups()):
                    continue
                top = re.search(r"Directory card: (\w+) /",p1)[1]
                header = re.search(r"^Item (Amount Ref|Ref Amount)$",p1,re.M)[1]
                records.append({"horizon":len(doc),"balanced":child[1]==last[1],
                                "first_listed_owner_is_lexical_first":directory[1]==owner,
                                "top_card_is_lexical_first_owner":top==owner,
                                "lexical_first_owner_column_is_amount":header.startswith("Amount")})
                break
    cells = {}
    for h in (12,30):
        all_h = [r for r in records if r["horizon"]==h]
        assert all_h
        for f in records[0].keys()-{"horizon","balanced"}:
            pairs = Counter((r[f],r["balanced"]) for r in all_h)
            same = sum(n for (layout,status),n in pairs.items() if layout==status)
            cells[f"{h}/{f}"] = {"directory_bit_by_status":{f"{int(b)}/{int(s)}":pairs[b,s] for b in (0,1) for s in (0,1)},
                                 "accuracy_if_layout_bit_is_status":same/len(all_h),
                                 "best_orientation_agreement":max(same,len(all_h)-same)/len(all_h),
                                 "distinct_layout_cases":len(all_h)}
    return cells


if __name__ == "__main__":
    assert sys.flags.isolated and sys.dont_write_bytecode
    # Only public training and calibration material is read by this invocation.
    print(json.dumps({"custody_revision":PIN,"per_horizon":{s:axes(CUSTODY/s,pinned(s,"pairs")["pairs"],
             pinned(s,"receipt")["source_pdfs"]) for s in ("train","cal")}},sort_keys=True,indent=2))

