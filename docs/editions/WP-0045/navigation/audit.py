"""Compare each live page, annotation and destination against the independently read bound predecessor."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from pypdf import PdfReader
from pypdf.generic import ArrayObject, BooleanObject, NullObject


def digest(data):
    return sha256(data).hexdigest()


def jsonable(value):
    value = value.get_object() if hasattr(value,"get_object") else value
    if isinstance(value, NullObject):
        return None
    if isinstance(value, BooleanObject):
        return value.value
    if isinstance(value,dict):
        return {k:jsonable(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):
        return list(map(jsonable,value))
    return value


def destination(doc, item, offset):
    return [doc.get_destination_page_number(item) - offset, *jsonable(item.dest_array[1:])]


def outline(doc, items, offset):
    tree = []
    for item in items:
        if isinstance(item,list):
            tree.append(outline(doc,item,offset))
        else:
            tree.append({"title":item.title,"dest":destination(doc,item,offset),
                         "format":{k:jsonable(item[k]) for k in ("/C","/F","/%is_open%") if k in item}})
    return tree


def outline_count(items):
    return sum(outline_count(item) if isinstance(item,list) else 1 for item in items)


def streams(page):
    content = page["/Contents"]
    entries = content if isinstance(content,ArrayObject) else [content]
    return [{"encoded":digest(e.get_object()._data),"decoded":digest(e.get_object().get_data())} for e in entries]


def registry(doc):
    return {k:list(map(digest, v)) for k,v in doc.attachments.items()}


def main():
    parser = argparse.ArgumentParser()
    for field in ("inputs","supplements","assembly","out"):
        parser.add_argument(field, type=Path)
    args = parser.parse_args()
    report = {}
    all_checks = []
    for label in ("I","II","III"):
        old_path = next(args.inputs.glob(f"Targeted-Depth-{label}-*.pdf"))
        old, new = PdfReader(old_path), PdfReader(args.assembly/f"Targeted-Depth-{label}-Complete-02.1.pdf")
        note_path = args.supplements/f"Amendment-{label}-02.1.pdf"
        note = PdfReader(note_path)
        delta = len(note.pages)
        old_named = {k:destination(old,v,0) for k,v in old.named_destinations.items()}
        new_named = {k:destination(new,v,delta) for k,v in new.named_destinations.items()}
        named_ok = old_named == new_named
        prior_tree = outline(old,old.outline,0)
        new_tree = outline(new,new.outline[2:],delta)
        pages = []
        types = Counter()
        for j,old_page in enumerate(old.pages):
            new_page = new.pages[j+delta]
            prior_annotations = [jsonable(a) for a in old_page.get("/Annots",[])]
            annotations = [jsonable(a) for a in new_page.get("/Annots",[])]
            types.update([a["/Subtype"] for a in annotations])
            actions = [{"type":a.get("/A",{}).get("/S",a["/Subtype"]),
                        "target":a.get("/A",{}).get("/D",a.get("/A",{}).get("/URI",a.get("/Dest")))}
                       for a in annotations]
            streams_old = streams(old_page)
            pages.append({"old_page":j+1,"complete_page":j+1+delta,
                          "streams":streams_old,"streams_equal":streams_old == streams(new_page),
                          "annotation_count":len(annotations),"annotations_equal":prior_annotations == annotations,
                          "actions":actions,"label_equal":old.page_labels[j] == new.page_labels[j+delta],
                          "text_equal":old_page.extract_text() == new_page.extract_text()})
        old_attachments = registry(old)
        attachments = registry(new)
        extra = {old_path.name:[digest(old_path.read_bytes())],
                 note_path.name:[digest(note_path.read_bytes())],
                 "Edition02.1-navigation.zip":[digest((args.assembly/"Edition02.1-navigation.zip").read_bytes())]
                 } if (args.assembly/"Edition02.1-navigation.zip").exists() else {
                     old_path.name:[digest(old_path.read_bytes())],note_path.name:[digest(note_path.read_bytes())]}
        advisory = next(args.inputs.glob("PGDA*.pdf"))
        extra[advisory.name] = [digest(advisory.read_bytes())]
        extra["Edition02.1-source.zip"] = ["18ac0a336b04bf46aaec670fc2a37c53f358823c3a733634ddf7a211336148d8"]
        if label == "III":
            companions = {f"Targeted-Depth-{n}-Complete-02.1.pdf":digest(
                (args.assembly/f"Targeted-Depth-{n}-Complete-02.1.pdf").read_bytes()) for n in ("I","II")}
            extra.update({k:[v] for k,v in companions.items()})
            encoded = (json.dumps(companions,sort_keys=True,indent=2)+"\n").encode()
            extra["companions-02.1.json"] = [digest(encoded)]
        introduction = [(e.title,new.get_destination_page_number(e)) for e in new.outline[:2] if not isinstance(e,list)]
        valid = {"introductory_bookmarks":introduction == [("Edition 02.1 - operative amendment",0),
                                                            ("Edition 02 - historical text",delta)],
                 "same_named_destinations":named_ok,"original_bookmark_tree_equal":prior_tree == new_tree,
                 "total_pages":len(new.pages) == len(old.pages)+delta,
                 "complete_registry_equal":{**old_attachments,**extra} == attachments,
                 "public_pages_equal":all(streams(p) == streams(new.pages[k]) for k,p in enumerate(note.pages)),
                 "pages_equal":all(p["streams_equal"] and p["annotations_equal"] and
                                   p["label_equal"] and p["text_equal"] for p in pages)}
        report[label] = {"checks":valid,"old_bookmarks":outline_count(prior_tree),
                         "carried_bookmarks":outline_count(new_tree), "annotations_by_type":dict(types),
                         "pages":pages,"old_registry":old_attachments,"new_registry":attachments,
                         "old_bookmark_tree":prior_tree,"carried_tree":new_tree,
                         "destinations":old_named,"missing_destinations":sorted(set(old_named)-set(new_named)),
                         "changed_destinations":[k for k in old_named if k in new_named and old_named[k]!=new_named[k]]}
        all_checks.extend(valid.values())
    args.out.write_bytes((json.dumps(report,indent=2,sort_keys=True)+"\n").encode())
    print({k:v["checks"] for k,v in report.items()})
    if not all(all_checks):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
