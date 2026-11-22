"""Prospective CPU interpretation of an immutable three-input native emission."""
from hashlib import sha256
from io import BytesIO
import json
import math
from pathlib import Path
import re
import sys

from PIL import Image, ImageChops
from tokenizers import Tokenizer

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
HISTORIC = ROOT / "docs/research/WP-0024/sensor"
SPAN_SHA = "29817b77589e88ef6b741dc1c36e9da3d07bcf641887109f3a77d4b7a39aeece"
TOKENIZER = Path("C:/Users/jackg/eLedgerCare-Q0/WP-0005/models/Unlimited_OCR_2_04809669/tokenizer.json")
TOKENIZER_SHA = "c55c165e32c5a67830362a53e1f548c8930dcc8469efa30ff3252a982799c589"
EOS = 1
PAGE = 128827
PROMPT_SHA = "b03d548d131b2651d56c3457e4b60144ab128b21444f87e4c9138dce1e809f57"
MARKER = "<PAGE>"
# The admitted table syntax preserves every row and cell without HTML repair or ignored content.
CELL = r"<td>[^<>\r\n]+</td>"
ROW = rf"<tr>(?:{CELL})+</tr>"
TABLE = re.compile(rf"<table>(?:{ROW})+</table>")
TEXT = re.compile(r"[^<>\r\n]+")
HASH = re.compile(r"[0-9a-f]{64}")


def digest(data):
    return sha256(data).hexdigest()


def packed(value):
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, allow_nan=False,
                       separators=(",", ":")) + "\n").encode()


def uint32_bytes(ids):
    return b"".join(i.to_bytes(4, "little") for i in ids)


class Unresolved(ValueError):
    """A condition prevents an authenticated mapping of the full input."""


def require(ok, reason):
    if not ok:
        raise Unresolved(reason)


def parse_json(data):
    def unique(pairs):
        obj = dict(pairs)
        require(len(obj) == len(pairs), "duplicate_json_key")
        return obj
    return json.loads(data, object_pairs_hook=unique)


def check_hash(data, identity, reason):
    require(isinstance(identity, str) and HASH.fullmatch(identity)
            and digest(data) == identity, reason)


class Reader:
    def __init__(self):
        check_hash((HISTORIC / "spans.py").read_bytes(), SPAN_SHA, "original_parser_pin")
        sys.path.insert(0, str(HISTORIC))
        import spans
        spans.verify_parsers()
        self.original = spans
        token_data = TOKENIZER.read_bytes()
        check_hash(token_data, TOKENIZER_SHA, "tokenizer_pin")
        self.tokenizer = Tokenizer.from_str(token_data.decode("utf-8"))
        self.added = {r["id"]: r["content"] for r in json.loads(token_data)["added_tokens"]}
        require(self.added.get(PAGE) == MARKER and self.added.get(EOS) == "<｜end▁of▁sentence｜>", "special_token_pin")

    def vocabulary(self, ids):
        return [self.tokenizer.id_to_token(i) for i in ids]

    def original_map(self, native):
        return self.original.map_window(native["text"], native["token_ids"], self.vocabulary, self.added)

    def observe(self, native):
        ids, text = native["token_ids"], native["text"]
        require(digest(packed(native["prompt_token_ids"])) == PROMPT_SHA, "unbound_three_page_prompt")
        require(isinstance(ids, list) and isinstance(text, str) and
                all(type(i) is int and 0 <= i < 2**32 for i in ids), "invalid_native_stream")
        require(EOS not in ids and native["eos_observed"] is True and native["stop_cause"] == "eos"
                and native["finish_reason"] == "stop", "missing_terminal_eos")
        event = native["terminal_observation"]
        require(all(type(i) is int for i in (event["nxt"], event["step"], native["eos_id"],
                                              event["prompt_length"], native["expected_pages"],
                                              native["num_pages_out"])), "invalid_terminal_metadata")
        require(event["nxt"] == native["eos_id"] == EOS and event["step"] == len(ids)
                and event["prompt_length"] == len(native["prompt_token_ids"])
                and native["expected_pages"] == 3, "terminal_observation_mismatch")
        edges = self.original.token_bytes(text, ids, self.vocabulary, self.added)
        starts = [i for i, token in enumerate(ids) if token == PAGE]
        markers = list(re.finditer(re.escape(MARKER), text))
        byte_starts = [len(text[:m.start()].encode()) for m in markers]
        require(starts and starts[0] == 0 and byte_starts == [edges[i] for i in starts]
                and all(edges[i+1] - edges[i] == len(MARKER) for i in starts),
                "marker_token_byte_disagreement")
        guard = event["guard"]
        require(all(type(guard[k]) is int for k in ("marker_cum", "page_len", "scanned"))
                and guard["marker_cum"] == native["num_pages_out"] == len(starts)
                and guard["scanned"] == len(ids) and guard["page_len"] == len(ids)-starts[-1]-1,
                "native_guard_mismatch")
        sections = []
        for index, start in enumerate(starts):
            end = starts[index+1] if index+1 < len(starts) else len(ids)
            char_end = markers[index+1].start() if index+1 < len(starts) else len(text)
            sections.append(dict(marker_token=start, token_range=[start, end],
                                 char_range=[markers[index].start(), char_end],
                                 byte_range=[edges[start], edges[end]],
                                 payload_byte_range=[edges[start+1], edges[end]]))
        return dict(raw_utf8_sha256=digest(text.encode()), token_byte_edges=edges, sections=sections,
                    ids_through_eos=[*ids, EOS], ids_through_eos_u32le_sha256=digest(uint32_bytes([*ids, EOS])),
                    observed_eos=dict(id=EOS, token_index=len(ids), byte_range=[edges[-1], edges[-1]],
                                      terminal_observation=event))

    def section_lines(self, text, rows):
        """Walk every source-bearing byte. LF is an explicit native block separator."""
        projected, _ = self.original.title_projection(text)
        heads = list(self.original.BLOCK.finditer(projected))
        require(heads and heads[0].start() == len(MARKER), "ungrounded_section_prefix")
        selected = []
        for index, head in enumerate(heads):
            stop = heads[index+1].start() if index+1 < len(heads) else len(projected)
            body = projected[head.end():stop]
            body = body.removesuffix("\n")
            if head[1] == "table":
                require(TABLE.fullmatch(body), "unsupported_or_incomplete_table")
                for row in re.finditer(ROW, body):
                    cells = re.findall(r"<td>([^<>\r\n]+)</td>", row.group())
                    selected.append(("row", " ".join(cells)))
            else:
                require(head[1] in ("text", "title") and TEXT.fullmatch(body), "unsupported_or_incomplete_block")
                selected.append(("block", body))
        grounded = [(r["kind"], r["text"]) for r in rows if r["kind"] == "row" or r["block_kind"] != "table"]
        require(grounded == selected and sum(r["kind"] == "block" for r in rows) == len(heads),
                "incomplete_grounded_projection")
        return [r for r in rows if r["kind"] == "row" or r["block_kind"] != "table"]

    def map(self, native_bytes, binding_bytes, binding_pin, raster_bytes):
        """binding_pin must come from the independent caller's authority, outside the case."""
        try:
            check_hash(binding_bytes, binding_pin, "untrusted_binding")
            binding = parse_json(binding_bytes)
            check_hash(native_bytes, binding["native_sha256"], "native_identity")
            native = parse_json(native_bytes)
            observation = self.observe(native)
            sections = observation["sections"]
            require(len(sections) in (3, 4), "section_count")
            unused = None
            if len(sections) == 4:
                unused = sections[-1]
                lo, hi = unused["payload_byte_range"]
                require(lo == hi and unused["marker_token"] + 1 == observation["observed_eos"]["token_index"],
                        "extra_section_has_payload")

            evidence = authenticate_pages(binding, binding_pin, raster_bytes)
            for section in sections[:3]:
                lo, hi = section["payload_byte_range"]
                if lo == hi:
                    index = sections.index(section)
                    reason = "verified_blank_source_withheld" if evidence[index]["white"] else "empty_input_section"
                    raise Unresolved(reason)
            require(not any(page["white"] for page in evidence), "verified_blank_source_withheld")
            keys = [tuple(line["text"] for line in page["lines"]) for page in evidence]
            require(all(keys), "missing_source_lines")
            require(len(set(keys)) == len(keys), "indistinguishable_source_text")
            require(len({p["rgb_sha256"] for p in evidence}) == 3, "indistinguishable_source_pixels")

            # Only after verifying the complete stream, expose the grounded window to the pinned
            # three-page parser. Raw offsets still begin at zero; the full token ledger is separate.
            char_end = sections[2]["char_range"][1]
            token_end = sections[2]["token_range"][1]
            parsed = self.original.map_window(native["text"][:char_end], native["token_ids"][:token_end],
                                              self.vocabulary, self.added)
            mapped = []
            for index, (section, source) in enumerate(zip(sections[:3], evidence, strict=True), 1):
                rows = [r for r in parsed["spans"] if r["page"] == index]
                lo, hi = section["char_range"]
                selected = self.section_lines(native["text"][lo:hi], rows)
                require([r["text"] for r in selected] == list(keys[index-1]), "source_line_sequence_mismatch")
                require((source["ink_outside_source_lines"] == 0 or source["verified_pdf_ruling"] is not None)
                        and all(source["source_line_contains_ink"]), "incomplete_source_pixel_coverage")
                correspondences = []
                for line, span in zip(source["lines"], selected, strict=True):
                    a, b, c, d = line["bbox999"]
                    x, y = (a+c)/2, (b+d)/2
                    left, top, right, bottom = span["bbox999"]
                    require(left <= x <= right and top <= y <= bottom, "source_line_outside_grounded_box")
                    correspondences.append(dict(text=span["text"], source_center999=[x, y],
                                                span=span["index"], grounded_bbox999=span["bbox999"]))
                require(all(section["marker_token"] < r["token_indices"][0] <= r["token_indices"][-1]
                            < section["token_range"][1] for r in rows), "span_crosses_section")
                mapped.append(dict(source=source, section=section, line_correspondences=correspondences,
                                   span_indices=[r["index"] for r in rows]))
            return dict(decision="accepted", reason="one_empty_terminal_marker" if unused else "ordinary",
                        binding_sha256=binding_pin, native_sha256=digest(native_bytes),
                        source_to_section=mapped, observation=observation, projection=parsed,
                        unused_delimiter=dict(disposition="retained_unassigned", **unused) if unused else None)
        except (ValueError, KeyError, TypeError, AttributeError, IndexError, OSError, OverflowError) as exc:
            return dict(decision="unresolved", reason=str(exc) if isinstance(exc, Unresolved)
                        else f"invalid_record:{type(exc).__name__}:{exc}")


def authenticate_pages(binding, binding_pin, images):
    require(binding["schema"] == "wp0027-reader-binding-v1" and isinstance(binding["call"], str)
            and binding["call"] and HASH.fullmatch(binding["document_sha256"]),
            "incomplete_call_binding")
    pages = binding["pages"]
    require(len(pages) == len(images) == 3, "ordered_three_sources_required")
    numbers = [p["page"] for p in pages]
    require(all(type(n) is int and n >= 1 for n in numbers)
            and numbers == list(range(numbers[0], numbers[0]+3)), "source_page_order")
    verified = []
    for p, encoded in zip(pages, images, strict=True):
        check_hash(encoded, p["png_sha256"], "ordered_png_identity")
        with Image.open(BytesIO(encoded)) as image:
            require(image.format == "PNG" and image.mode == "RGB" and list(image.size) == p["size"], "source_raster_shape")
            check_hash(image.tobytes(), p["rgb_sha256"], "ordered_pixel_identity")
            r, g, b = image.split()
            ink = ImageChops.invert(ImageChops.darker(r, ImageChops.darker(g, b)))
            white = ink.getbbox() is None
            remainder = ink.copy()
            contains_ink = []
            clips = []
            w, h = image.size
            require(isinstance(p["lines"], list), "invalid_source_lines")
            for line in p["lines"]:
                s, box = line["text"], line["bbox999"]
                require(isinstance(s, str) and s and s == s.strip() and "\n" not in s and "\r" not in s,
                        "invalid_source_lines")
                require(len(box) == 4 and all(type(v) in (float, int) and math.isfinite(v) for v in box)
                        and 0 <= box[0] < box[2] <= 999 and 0 <= box[1] < box[3] <= 999, "invalid_source_box")
                # One normalized coordinate unit covers glyph-box rounding and antialiasing.
                left, top, right, bottom = box
                clip = (max(0, math.floor((left-1)*w/999)), max(0, math.floor((top-1)*h/999)),
                        min(w, math.ceil((right+1)*w/999)), min(h, math.ceil((bottom+1)*h/999)))
                contains_ink.append(ink.crop(clip).getbbox() is not None)
                remainder.paste(0, clip)
                clips.append(clip)
            outside = sum(remainder.histogram()[1:])
            ruling = None
            if outside:
                from source_ruling import verify_h0_ruling
                ruling = verify_h0_ruling(binding, binding_pin, p, image, clips)
        require(not (white and p["lines"]), "blank_source_line_conflict")
        verified.append(dict(p, white=white, source_line_contains_ink=contains_ink,
                             ink_outside_source_lines=outside, verified_pdf_ruling=ruling))
    return verified
