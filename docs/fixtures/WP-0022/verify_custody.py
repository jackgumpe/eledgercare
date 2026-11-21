"""Check WP-0022 files, literal/spatial truth, mask extents and independent regeneration."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

from PIL import Image


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inside(child, parent):
    return all(parent[i] <= child[i] for i in (0, 1)) and all(child[i] <= parent[i] for i in (2, 3))


def words_in(words, box):
    return [w["text"] for w in words if inside(w["bbox"], box)]


def union(boxes):
    return [min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes)]


def verify(root, generator, replay):
    sealed = read(root / "commitments.json")
    assert digest(generator) == sealed["generator_sha256"]
    assert digest(root / "truth.json") == sealed["truth_sha256"]
    assert digest(root / "public/manifest.json") == sealed["manifest_sha256"]
    assert digest(root / "precounts.json") == sealed["precounts_sha256"]
    public = root / "public"
    manifest = read(public / "manifest.json")
    docs = manifest["documents"]
    expected_files = {"manifest.json"}
    geometries = {}
    raster_digests = []
    refs = 0
    for doc in docs:
        name = doc["id"]
        render = "rendered/" + name + ".json"
        expected_files.add(render)
        assert digest(public / render) == sealed["rendered_sha256"][name]
        observation = read(public / render)
        for j, page in enumerate(doc["pages"], 1):
            expected_files.add(page["raster"])
            assert digest(public / page["raster"]) == page["sha256"]
            raster_digests.append(page["sha256"])
            frame = observation["pages"][j-1]
            assert frame["page"] == page["page"] == j
            assert set(frame) == {"page", "width_pt", "height_pt", "lines"}
            assert (frame["width_pt"], frame["height_pt"]) == (612, 792)
            words = []
            with Image.open(public / page["raster"]) as raster:
                assert raster.size == (2550, 3300) and raster.mode == "RGB"
                assert all(abs(v-300) < .02 for v in raster.info["dpi"])
                for li, line in enumerate(frame["lines"], 1):
                    assert set(line) == {"words"}
                    for wi, w in enumerate(line["words"], 1):
                        assert set(w) == {"text", "bbox", "ref"}
                        assert w["ref"] == f"p{j}:L{li}:W{wi}"
                        x0, y0, x1, y1 = (int(round(v*2550/612)) for v in w["bbox"])
                        assert 0 <= x0 < x1 <= 2550 and 0 <= y0 < y1 <= 3300
                        # Every edge of the word contains antialiased nonwhite ink.
                        for edge in [(x0, y0, x1, y0+1), (x0, y1-1, x1, y1),
                                     (x0, y0, x0+1, y1), (x1-1, y0, x1, y1)]:
                            assert raster.crop(edge).getextrema()[0][0] < 255
                        words.append(w)
            refs += len(words)
            geometries[name, j] = words
    assert {p.relative_to(public).as_posix() for p in public.rglob("*") if p.is_file()} == expected_files
    assert len(docs) == 8 and len(raster_digests) == 16 and len(set(raster_digests)) == 14
    assert digest(public / "rendered/N07.json") == digest(public / "rendered/N08.json")
    assert [p["sha256"] for p in docs[-2]["pages"]] == [p["sha256"] for p in docs[-1]["pages"]]

    targets = read(root / "truth.json")["targets"]
    assert len(targets) == len(set(t["id"] for t in targets)) == 42
    bounds = defaultdict(list)
    counts = Counter()
    tag_counts = Counter()
    note_pairs = defaultdict(list)
    sibling_headings = defaultdict(dict)
    for t in targets:
        doc, page, tags = t["doc"], t["page"], t["tags"]
        page_words = geometries[doc, page]
        assert (page == 1) == ("setup" in tags)
        assert inside(t["amount_box"], t["row_box"])
        assert words_in(page_words, t["amount_box"]) == ([t["literal"]] if t["literal"] else [])
        bounds[doc, page].append(t["row_box"])
        counts[page, t["scope"]] += 1
        tag_counts.update(tags)
        sources = {}
        for key in ("heading", "amount_header", "property_region", "unit_region"):
            source = t[key]
            candidates = [w for w in geometries[doc, source["page"]] if inside(w["bbox"], source["bbox"])]
            assert candidates and union([w["bbox"] for w in candidates]) == source["bbox"]
            sources[key] = [w["text"] for w in candidates]
        assert sources["amount_header"] == ["Amount"]
        assert sources["heading"] == (["Ledger"] if t["scope"] == "parent" else ["Contractor", "detail"])
        assert len(sources["property_region"]) == 2 and len(sources["unit_region"]) == 1
        if "child-a" in tags or "child-b" in tags:
            sibling_headings[doc]["a" if "child-a" in tags else "b"] = t["heading"]
        for note in t["note_boxes"]:
            assert inside(note, t["row_box"]) and t["amount_box"][2] < note[0]
            literal, = words_in(page_words, note)
            note_pairs[doc, t["scope"]].append((t["kind"], literal))
    assert all(v["a"] != v["b"] for v in sibling_headings.values()) and len(sibling_headings) == 2
    assert [v["scope"] for v in targets if v["kind"] == "ambiguous"] == ["parent", "child"]
    assert len(note_pairs) == 4
    for pair in note_pairs.values():
        assert pair[0][0] == "value" and pair[1][0] == "blank" and pair[0][1] == pair[1][1]
    for page_rows in bounds.values():
        for first, second in zip(page_rows, page_rows[1:]):
            assert first[3] < second[1]
    assert counts == {(1,"parent"):8, (1,"child"):8, (2,"parent"):13, (2,"child"):13}
    assert dict(tag_counts) == read(root / "precounts.json")["tags"]
    file_names = {"truth.json", "commitments.json", "precounts.json"} | {"public/"+n for n in expected_files}
    for name in file_names:
        assert digest(root/name) == digest(replay/name), name
    return dict(verified=True, compared_generated_files=len(file_names), renderer_word_instances=refs,
                raster_appearances=len(raster_digests), distinct_rasters=len(set(raster_digests)),
                targets=len(targets), note_pairs=len(note_pairs), siblings_checked=len(sibling_headings))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("root", "generator", "replay"):
        parser.add_argument(arg, type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.root, args.generator, args.replay), indent=2))
