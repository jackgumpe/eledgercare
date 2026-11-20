"""WP-0019 reviewer control checks (eld-rd-reviewer, independent non-author).

Subcommands: env, inputs, geometry, identity, timing, static, decision. None of them calls WinRT,
OCR, a GPU or the network. Inputs are canonical run bundles (wp0019-review-run/1) and the read-only
manifests; author formats are bound by a separate committed adapter (PREREGISTRATION section 4).
"""
import argparse
import json
import os
import platform
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from review_common import (FAMILY_PINS, HISTORICAL_ASSETS, HISTORICAL_ENGINE_VERSION, Checks, bgra_to_rgb, canon,
                           file_version, finite_box, load_pins, page_count, pairs, project_float, project_pinned, read_bmp,
                           read_json, render_rgb_pages, sha256_bytes, sha256_file, slice_bgra, write_new)

ARMS = ("baseline", "treatment")
MANIFEST_PAGE_KEYS = {"page", "bmp", "width", "height", "points", "rgb_sha256", "bgra_sha256"}


def load_runs(specs):
    runs = {}
    for spec in specs or []:
        name, path = spec.split("=", 1)
        runs[name] = dict(path=str(Path(path).resolve()), sha256=sha256_file(path), bundle=read_json(path))
    return runs


def arms_of(bundle):
    return {a["arm"]: a for a in bundle["arms"]}


def fam_of(arm, family):
    for f in arm["families"]:
        if f["family"] == family:
            return f
    return None


def finish(out, kind, checks, extra):
    doc = dict(kind=kind, checks=checks.rows, check_summary=checks.summary(), failed_checks=checks.failed(),
               failed_observations=[i for i in checks.failed(gating_only=False) if i not in checks.failed()], **extra)
    sha = write_new(out, doc)
    print(json.dumps(dict(out=str(out), sha256=sha, check_summary=doc["check_summary"],
                          failed=doc["failed_checks"], failed_observations=doc["failed_observations"]), indent=1))
    return doc


# ---------------------------------------------------------------- env
def cmd_env(args):
    import winreg
    checks = Checks()
    win = Path(os.environ["SystemRoot"])
    assets = {}
    for rel, want in HISTORICAL_ASSETS.items():
        path = win / rel
        got = sha256_file(path) if path.exists() else None
        assets[rel] = dict(sha256=got, bytes=path.stat().st_size if path.exists() else None, version=file_version(path) if path.exists() else None)
        checks.add(f"E1.asset.{rel}", got == want, "OCR asset equals historical WP-0015 pin", got, gating=False)
    extra = {}
    for rel in ["System32/WindowsCodecs.dll", "System32/windows.storage.dll", "System32/combase.dll",
                "System32/Windows.Graphics.dll", "System32/Windows.Globalization.dll",
                "System32/WindowsPowerShell/v1.0/powershell.exe"] + list(args.extra or []):
        path = Path(rel) if Path(rel).is_absolute() else win / rel
        extra[rel] = dict(sha256=sha256_file(path), version=file_version(path)) if path.exists() else None
    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion")
    osinfo = {}
    for name in ("ProductName", "DisplayVersion", "CurrentBuild", "UBR", "EditionID"):
        try:
            osinfo[name] = winreg.QueryValueEx(key, name)[0]
        except OSError:
            osinfo[name] = None
    checks.add("E2.ocr_version", assets["System32/Windows.Media.Ocr.dll"]["version"] == HISTORICAL_ENGINE_VERSION,
               "Windows.Media.Ocr.dll file version equals historical engine_version", assets["System32/Windows.Media.Ocr.dll"]["version"], gating=False)
    langs = sorted(p.name for p in (win / "OCR").iterdir() if p.is_dir()) if (win / "OCR").exists() else []
    checks.add("E3.en_us", "en-us" in [l.lower() for l in langs], "en-US OCR resources present", langs)
    pyinfo = dict(version=sys.version, executable=sys.executable, executable_sha256=sha256_file(sys.executable), flags=str(sys.flags))
    try:
        import numpy, PIL, pypdfium2
        pyinfo.update(numpy=numpy.__version__, pillow=PIL.__version__, pypdfium2=str(pypdfium2.version.PYPDFIUM_INFO),
                      pdfium=str(pypdfium2.version.PDFIUM_INFO))
    except Exception as exc:  # recorded, not hidden
        pyinfo["import_error"] = repr(exc)
    checks.add("E4.renderer", pyinfo.get("pypdfium2") == "5.15.2" and pyinfo.get("pillow") == "13.0.0" and
               str(pyinfo.get("pdfium", "")).startswith("159.0.8149.0"), "renderer stack equals historical rasters.json renderer", pyinfo)
    power = subprocess.run(["powercfg", "/getactivescheme"], capture_output=True, text=True).stdout.strip()
    procs = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True).stdout
    names = Counter(line.split('","')[0].strip('"').lower() for line in procs.splitlines() if line.strip())
    watch = {n: names.get(n, 0) for n in ("powershell.exe", "pwsh.exe", "python.exe", "dotnet.exe", "nvidia-smi.exe")}
    for n in args.watch or []:
        watch[n.lower()] = names.get(n.lower(), 0)
    expect = read_json(args.expect) if args.expect else None
    if expect:
        same = {rel: expect["assets"].get(rel, {}).get("sha256") == v["sha256"] for rel, v in assets.items()}
        checks.add("E5.same_as_reference_snapshot", all(same.values()) and expect["os"] == osinfo,
                   "assets and OS build equal the reference snapshot", dict(same_assets=same, os_equal=expect["os"] == osinfo))
    finish(Path(args.out), "wp0019-review-env", checks,
           dict(os=osinfo, platform=platform.platform(), cpu=platform.processor(), logical_cpus=os.cpu_count(),
                assets=assets, historical_assets=HISTORICAL_ASSETS, historical_engine_version=HISTORICAL_ENGINE_VERSION,
                other_binaries=extra, ocr_languages=langs, python=pyinfo, power_scheme=power, watched_process_counts=watch,
                note="process counts are observations only; no process is touched"))


# ---------------------------------------------------------------- inputs
def cmd_inputs(args):
    checks = Checks()
    record = {}
    checks.add("N0.families", sorted(args.families) == ["A", "H"], "both H and A admitted in this check", args.families,
               gating=sorted(args.families) == ["A", "H"])
    for fam in args.families:
        pins = FAMILY_PINS[fam]
        mpath = getattr(args, f"manifest_{fam}")
        manifest = read_json(mpath)
        pdf = Path(getattr(args, f"pdf_{fam}")).read_bytes()
        rasters = read_json(getattr(args, f"rasters_{fam}"))
        checks.add(f"N1.rasters_pin.{fam}", sha256_file(getattr(args, f"rasters_{fam}")) == pins["rasters_sha256"], "rasters.json equals commitment")
        checks.add(f"N1.manifest_keys.{fam}", set(manifest) >= {"family", "source_sha256", "pages"}, "manifest top-level keys", sorted(manifest))
        checks.add(f"N1.family.{fam}", manifest.get("family") == fam, "manifest family", manifest.get("family"))
        checks.add(f"N1.source.{fam}", sha256_bytes(pdf) == pins["source_sha256"] == manifest.get("source_sha256"),
                   "source PDF digest equals pin and manifest", sha256_bytes(pdf))
        pages = manifest.get("pages", [])
        nums = [p.get("page") for p in pages]
        checks.add(f"N1.pages.{fam}", nums == list(range(1, pins["pages"] + 1)) and page_count(pdf) == pins["pages"],
                   "one-based contiguous pages equal PDF page count", nums)
        rp = {p["page_number"]: p for p in rasters["pages"]}
        rows = []
        copy_pages = []
        by_num = {p.get("page"): p for p in pages}
        for render in render_rgb_pages(pdf):
            num = render["page"]
            mp = by_num.get(num, {})
            row = dict(page=num, extra_keys=sorted(set(mp) - MANIFEST_PAGE_KEYS), missing_keys=sorted(MANIFEST_PAGE_KEYS - set(mp)))
            rgb_sha = sha256_bytes(render["rgb"])
            row.update(render_rgb_sha256=rgb_sha, render_size=[render["width"], render["height"]], render_points=render["points"])
            ok_render = rgb_sha == rp[num]["rgb_sha256"] == mp.get("rgb_sha256") and [render["width"], render["height"]] == [rp[num]["width_px"], rp[num]["height_px"]]
            try:
                bmp = read_bmp(mp["bmp"])
                bgra_sha = sha256_bytes(bmp["bgra"])
                rgb_from_bmp = bgra_to_rgb(bmp["bgra"])
                row.update(bmp=str(mp["bmp"]), bmp_file_sha256=sha256_file(mp["bmp"]), bmp_meta=bmp["meta"],
                           bmp_size=[bmp["width"], bmp["height"]], bmp_bgra_sha256=bgra_sha,
                           bmp_rgb_equals_render=rgb_from_bmp == render["rgb"])
                ok_bmp = (bgra_sha == mp.get("bgra_sha256") and [bmp["width"], bmp["height"]] == [mp.get("width"), mp.get("height")] ==
                          [render["width"], render["height"]] and rgb_from_bmp == render["rgb"])
                del rgb_from_bmp
            except Exception as exc:
                row["bmp_error"] = repr(exc)
                ok_bmp = False
                bmp = None
            ok_points = (isinstance(mp.get("points"), list) and len(mp["points"]) == 2 and
                         all(abs(a - b) < 1e-9 for a, b in zip(mp["points"], render["points"])))
            row.update(render_ok=ok_render, bmp_ok=ok_bmp, points_ok=ok_points)
            if args.expected:
                exp = {p["page"]: p for p in read_json(args.expected)["families"][fam]}.get(num, {})
                checks.add(f"N2.expected.{fam}.{num}", exp.get("bgra_sha256") == mp.get("bgra_sha256"),
                           "manifest BGRA digest equals the reviewer's preregistered expectation", mp.get("bgra_sha256"))
            checks.add(f"N2.page.{fam}.{num}", ok_render and ok_bmp and ok_points and not row["missing_keys"],
                       "independent render RGB == pins == manifest; BMP BGRA (own parser) == manifest; BMP RGB == render; points", row)
            if args.copy_to and ok_bmp:
                dest = Path(args.copy_to) / fam / f"page-{num:03d}.bmp"
                dest.parent.mkdir(parents=True, exist_ok=True)
                data = Path(mp["bmp"]).read_bytes()
                with open(dest, "xb") as f:
                    f.write(data)
                    f.flush()
                    os.fsync(f.fileno())
                same = sha256_file(dest) == row["bmp_file_sha256"]
                checks.add(f"N3.copy.{fam}.{num}", same, "reviewer BMP copy byte-identical", str(dest))
                copy_pages.append(dict({k: mp[k] for k in mp if k != "bmp"}, bmp=str(dest.resolve())))
            rows.append(row)
            del render, bmp
        record[fam] = dict(manifest=str(Path(mpath).resolve()), manifest_sha256=sha256_file(mpath), pages=rows)
        if args.copy_to:
            mout = Path(args.copy_to) / fam / "manifest.json"
            sha = write_new(mout, dict({k: v for k, v in manifest.items() if k != "pages"}, pages=copy_pages))
            record[fam]["reviewer_manifest"] = dict(path=str(mout.resolve()), sha256=sha)
    finish(Path(args.out), "wp0019-review-inputs", checks, dict(families=record))


def cmd_inputs_fresh(args):
    """Stage 2: admitted fresh rasters against the coordinator's pre-execution raster commitment. Keys are never read."""
    checks = Checks()
    pins = load_pins(args.pins)
    commitments = read_json(args.commitments)
    pdfs = pairs(args.pdf)
    record = {}
    for fam, mpath in pairs(args.manifest).items():
        manifest = read_json(mpath)
        com = commitments.get(fam, {})
        cpages = {p["page"]: p for p in com.get("pages", [])}
        checks.add(f"F1.family.{fam}", manifest.get("family") == fam and fam in pins and
                   manifest.get("source_sha256") == pins[fam]["source_sha256"] == com.get("source_sha256"),
                   "family/source digest agree across manifest, pins and raster commitment", manifest.get("source_sha256"))
        nums = [p["page"] for p in manifest["pages"]]
        checks.add(f"F1.pages.{fam}", fam in pins and nums == list(range(1, pins[fam]["pages"] + 1)) == sorted(cpages),
                   "contiguous committed page set", nums)
        renders = {}
        if fam in pdfs:
            pdf = Path(pdfs[fam]).read_bytes()
            checks.add(f"F2.pdf.{fam}", sha256_bytes(pdf) == manifest.get("source_sha256"), "PDF digest equals source", sha256_bytes(pdf))
            renders = {r["page"]: sha256_bytes(r["rgb"]) for r in render_rgb_pages(pdf)}
        rows = []
        for mp in manifest["pages"]:
            bmp = read_bmp(mp["bmp"])
            bgra = sha256_bytes(bmp["bgra"])
            rgb = sha256_bytes(bgra_to_rgb(bmp["bgra"]))
            c = cpages.get(mp["page"], {})
            row = dict(page=mp["page"], bmp_file_sha256=sha256_file(mp["bmp"]), bgra_sha256=bgra, rgb_sha256=rgb,
                       size=[bmp["width"], bmp["height"]], render_rgb_sha256=renders.get(mp["page"]))
            ok = (bgra == mp["bgra_sha256"] == c.get("bgra_sha256") and [bmp["width"], bmp["height"]] == [mp["width"], mp["height"]] and
                  rgb == mp["rgb_sha256"] and c.get("rgb_sha256") in (None, rgb) and (not renders or renders.get(mp["page"]) == rgb))
            checks.add(f"F3.page.{fam}.{mp['page']}", ok, "own-parser BGRA/RGB equal manifest and commitment (and render when supplied)", row)
            rows.append(row)
            del bmp
        record[fam] = dict(manifest=str(Path(mpath).resolve()), manifest_sha256=sha256_file(mpath), pages=rows)
    finish(Path(args.out), "wp0019-review-inputs-fresh", checks,
           dict(commitments=dict(path=str(Path(args.commitments).resolve()), sha256=sha256_file(args.commitments)), families=record))


def rgb_to_opaque_bgra(rgb):
    out = bytearray(len(rgb) // 3 * 4)
    out[0::4] = rgb[2::3]
    out[1::4] = rgb[1::3]
    out[2::4] = rgb[0::3]
    out[3::4] = b"\xff" * (len(rgb) // 3)
    return bytes(out)


def cmd_expect_bgra(args):
    """Preregistered expectation: opaque top-to-bottom BGRA digests derived from an independent render."""
    checks = Checks()
    fams = {}
    for fam in ("H", "A"):
        pdf = Path(getattr(args, f"pdf_{fam}")).read_bytes()
        rasters = read_json(getattr(args, f"rasters_{fam}"))
        rp = {p["page_number"]: p for p in rasters["pages"]}
        checks.add(f"B0.source.{fam}", sha256_bytes(pdf) == FAMILY_PINS[fam]["source_sha256"], "source digest", sha256_bytes(pdf))
        rows = []
        for r in render_rgb_pages(pdf):
            rgb_sha = sha256_bytes(r["rgb"])
            rows.append(dict(page=r["page"], width=r["width"], height=r["height"], points=r["points"], rgb_sha256=rgb_sha,
                             bgra_sha256=sha256_bytes(rgb_to_opaque_bgra(r["rgb"]))))
            checks.add(f"B1.rgb.{fam}.{r['page']}", rgb_sha == rp[r["page"]]["rgb_sha256"] and
                       [r["width"], r["height"]] == [rp[r["page"]]["width_px"], rp[r["page"]]["height_px"]], "render equals rasters.json pin")
        checks.add(f"B2.count.{fam}", len(rows) == FAMILY_PINS[fam]["pages"], "page count", len(rows))
        fams[fam] = rows
    finish(Path(args.out), "wp0019-review-expected-bgra", checks, dict(families=fams))


# ---------------------------------------------------------------- geometry / hashes / projections
def flatten_words(record):
    return [w for ln in record.get("lines") or [] for w in ln["words"]]


def cmd_geometry(args):
    checks = Checks()
    runs = load_runs(args.run)
    per_crop = []
    projection_modes = Counter()
    formats = Counter()
    consistency = []
    for fam, mpath in pairs(args.manifest).items():
        manifest = read_json(mpath)
        for mp in manifest["pages"]:
            num = mp["page"]
            bmp = None
            for name, run in runs.items():
                arms = arms_of(run["bundle"])
                for arm_name in ARMS:
                    fam_rec = fam_of(arms.get(arm_name, {"families": []}), fam)
                    if fam_rec is None:
                        continue
                    page = {p["page"]: p for p in fam_rec["pages"]}.get(num)
                    if page is None:
                        checks.add(f"G0.page_present.{name}.{arm_name}.{fam}.{num}", False, "page record present")
                        continue
                    full = page["full"]
                    formats[str(full.get("pixel_format"))] += 1
                    checks.add(f"G1.full_input.{name}.{arm_name}.{fam}.{num}",
                               (full.get("bgra_sha256"), full.get("width"), full.get("height")) == (mp["bgra_sha256"], mp["width"], mp["height"]),
                               "full-pass input hash/dimensions equal admitted page", [full.get("bgra_sha256"), full.get("width"), full.get("height")])
                    crops = page.get("crops") or []
                    if arm_name == "baseline":
                        checks.add(f"G2.baseline_no_crops.{name}.{fam}.{num}", len(crops) == 0, "baseline arm attempts no crop", len(crops))
                        continue
                    if crops and bmp is None:
                        bmp = read_bmp(mp["bmp"])
                        if sha256_bytes(bmp["bgra"]) != mp["bgra_sha256"]:
                            raise ValueError("admitted BMP no longer matches manifest")
                    for ix, crop in enumerate(crops):
                        rect = crop.get("rect")
                        row = dict(run=name, family=fam, page=num, index=ix, id=crop.get("id", ix), rect=rect, kind=crop.get("kind"))
                        ok_rect = (isinstance(rect, list) and len(rect) == 4 and all(type(v) is int for v in rect) and
                                   0 <= rect[0] < rect[2] <= mp["width"] and 0 <= rect[1] < rect[3] <= mp["height"])
                        row["rect_ok"] = ok_rect
                        if ok_rect:
                            sl = slice_bgra(bmp["bgra"], mp["width"], mp["height"], rect)
                            mine = sha256_bytes(sl)
                            del sl
                            row["reviewer_slice_sha256"] = mine
                            row["dims_ok"] = (crop.get("width"), crop.get("height")) == (rect[2] - rect[0], rect[3] - rect[1])
                            row["source_rect_ok"] = crop.get("source_rect_sha256") == mine
                            row["crop_bytes_ok"] = crop.get("bgra_sha256") in (None, mine)
                            row["attached_ok"] = crop.get("full_sha256") == mp["bgra_sha256"] == full.get("bgra_sha256")
                            row["format_same"] = crop.get("pixel_format") == full.get("pixel_format")
                            words = flatten_words(crop)
                            w, h = rect[2] - rect[0], rect[3] - rect[1]
                            row["words"] = len(words)
                            row["words_outside_crop"] = sum(1 for x in words if not (finite_box(list(x["bbox"])) and
                                                            0 <= x["bbox"][0] <= x["bbox"][2] <= w and 0 <= x["bbox"][1] <= x["bbox"][3] <= h))
                            proj = crop.get("projected_words")
                            if proj is not None:
                                pts = mp["points"]
                                mode = set()
                                maxdiff = 0.0
                                text_ok = len(proj) == len(words)
                                for pw, cw in zip(proj, words):
                                    text_ok &= pw["text"] == cw["text"]
                                    px = [cw["bbox"][0] + rect[0], cw["bbox"][1] + rect[1], cw["bbox"][2] + rect[0], cw["bbox"][3] + rect[1]]
                                    pin = project_pinned(px, mp["width"], mp["height"], pts)
                                    flt = project_float(px, mp["width"], mp["height"], pts)
                                    if list(pw["bbox"]) == pin:
                                        mode.add("pinned")
                                    elif max(abs(a - b) for a, b in zip(pw["bbox"], flt)) <= 1e-6:
                                        mode.add("float")
                                    else:
                                        mode.add("mismatch")
                                        maxdiff = max(maxdiff, max(abs(a - b) for a, b in zip(pw["bbox"], pin)))
                                row["projection"] = dict(modes=sorted(mode), text_order_ok=text_ok, max_mismatch_pt=maxdiff)
                                for m in mode:
                                    projection_modes[m] += 1
                            if args.inset is not None or args.padding is not None:
                                consistency.append(consistency_row(crop, page, mp, args.inset, args.padding, row))
                        checks.add(f"G3.crop.{name}.{fam}.{num}.{ix}",
                                   ok_rect and row["dims_ok"] and row["source_rect_ok"] and row["crop_bytes_ok"] and row["attached_ok"],
                                   "integer half-open in-page rect; dims; reviewer slice hash == source-rect hash; attached to admitted full page",
                                   {k: row.get(k) for k in ("rect", "rect_ok", "dims_ok", "source_rect_ok", "crop_bytes_ok", "attached_ok")})
                        per_crop.append(row)
            bmp = None
    checks.add("G4.projection_rule", (set(projection_modes) in ({"pinned"}, {"float"})) if projection_modes else None,
               "every projected word box follows one projection rule (pinned round-3 or float within 1e-6)", dict(projection_modes))
    checks.add("G5.pixel_format", len(formats) <= 1, "one pixel format across all full passes", dict(formats))
    if consistency:
        dev = [c for c in consistency if c.get("max_dev_px") is not None and c["max_dev_px"] > 1.0]
        checks.add("G6.inset_padding_consistency", not dev, "cell crops at declared inset, prose crops at declared padding, within 1 px",
                   dict(rows=len(consistency), deviating=len(dev), examples=dev[:10]), gating=False)
    crops_per_page = Counter((r["run"], r["family"]) for r in per_crop)
    out = Path(args.out)
    sha = write_new(out.with_name(out.stem + "-crops.json"), per_crop)
    finish(out, "wp0019-review-geometry", checks, dict(per_crop_sha256=sha, crops=dict((f"{k[0]}/{k[1]}", v) for k, v in crops_per_page.items()),
                                                      projection_modes=dict(projection_modes), pixel_formats=dict(formats),
                                                      consistency=consistency[:2000]))


def consistency_row(crop, page, mp, inset, padding, row):
    rect = crop["rect"]
    W, H, pts = mp["width"], mp["height"], mp["points"]
    out = dict(id=row["id"], page=row["page"], family=row["family"], run=row["run"], kind=crop.get("kind"), rect=rect)
    cx, cy = (rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2
    grids = page.get("grids") or []
    if crop.get("kind") == "cell" and inset is not None:
        for g in grids:
            xs = [x * W / pts[0] for x in g["xs"]]
            ys = [y * H / pts[1] for y in g["ys"]]
            if xs[0] <= cx < xs[-1] and ys[0] <= cy < ys[-1]:
                c = max(i for i in range(len(xs) - 1) if xs[i] <= cx)
                r = max(i for i in range(len(ys) - 1) if ys[i] <= cy)
                d = [rect[0] - xs[c], rect[1] - ys[r], xs[c + 1] - rect[2], ys[r + 1] - rect[3]]
                out.update(grid_cell=[r, c], inset_observed=d, max_dev_px=max(abs(v - inset) for v in d))
                break
        else:
            out.update(max_dev_px=None, note="no detected grid cell contains crop centre")
    elif crop.get("kind") == "line" and padding is not None:
        best = None
        for li, ln in enumerate(page["full"]["lines"]):
            boxes = [w["bbox"] for w in ln["words"]]
            if not boxes:
                continue
            u = [min(b[0] for b in boxes) - padding, min(b[1] for b in boxes) - padding,
                 max(b[2] for b in boxes) + padding, max(b[3] for b in boxes) + padding]
            u = [max(0, u[0]), max(0, u[1]), min(W, u[2]), min(H, u[3])]
            dist = max(abs(a - b) for a, b in zip(rect, u))
            if best is None or dist < best[0]:
                best = (dist, li)
        out.update(max_dev_px=None if best is None else best[0], nearest_full_line=None if best is None else best[1])
    else:
        out.update(max_dev_px=None, note="kind/constant not declared")
    return out


# ---------------------------------------------------------------- full-pass identity
def canonical_full(full):
    return dict(width=full["width"], height=full["height"], bgra_sha256=full.get("bgra_sha256"),
                pixel_format=full.get("pixel_format"), text=full["text"],
                lines=[dict(text=ln["text"], words=[dict(text=w["text"], bbox=[float(v) for v in w["bbox"]]) for w in ln["words"]])
                       for ln in full["lines"]])


def archive_compare(cur, raw):
    rr = raw.get("reader_result", raw)
    a_lines = [dict(text=ln["text"], words=[dict(text=w["text"], bbox=[float(v) for v in w["bbox"]]) for w in ln["words"]]) for ln in rr["lines"]]
    if (rr["width"], rr["height"]) != (cur["width"], cur["height"]):
        return "size_differs", None
    if rr["text"] == cur["text"] and a_lines == cur["lines"]:
        return "identical", None
    if [[w["text"] for w in l["words"]] for l in a_lines] == [[w["text"] for w in l["words"]] for l in cur["lines"]]:
        return "boxes_differ", None
    cur_words = [w["text"] for l in cur["lines"] for w in l["words"]]
    arch_words = [w["text"] for l in a_lines for w in l["words"]]
    if sorted(cur_words) == sorted(arch_words):
        return "order_or_grouping_differs", None
    diff = dict(only_current=sorted((Counter(cur_words) - Counter(arch_words)).elements()),
                only_archive=sorted((Counter(arch_words) - Counter(cur_words)).elements()))
    return "text_differs", diff


def cmd_identity(args):
    checks = Checks()
    runs = load_runs(args.run)
    reference = {}
    archive_classes = {}
    archive_detail = {}
    grid_archive = {}
    for name, run in runs.items():
        b = run["bundle"]
        info = (b.get("worker") or {}).get("info") or {}
        checks.add(f"I0.language.{name}", str(info.get("language", "")).lower() == "en-us", "worker language en-US", info.get("language"))
        checks.add(f"I0.info.{name}", bool(info), "worker.info recorded (build, assets, max input size)",
                   {k: info.get(k) for k in sorted(info)[:40]})
        arms = arms_of(b)
        for fam, mpath in pairs(args.manifest).items():
            manifest = read_json(mpath)
            mpages = {p["page"]: p for p in manifest["pages"]}
            if not mpages:
                continue
            per_arm = {}
            for arm_name in ARMS:
                f = fam_of(arms.get(arm_name, {"families": []}), fam)
                if f is None:
                    checks.add(f"I1.present.{name}.{arm_name}.{fam}", False, "family present in arm")
                    continue
                per_arm[arm_name] = {p["page"]: p for p in f["pages"]}
            if set(per_arm) != set(ARMS):
                continue
            for num, mp in mpages.items():
                cb = canonical_full(per_arm["baseline"][num]["full"])
                ct = canonical_full(per_arm["treatment"][num]["full"])
                checks.add(f"I1.arms_equal.{name}.{fam}.{num}", cb == ct,
                           "baseline and treatment full passes equal (raw text/words/boxes/input hash/format; clocks excluded)",
                           None if cb == ct else dict(baseline_sha=sha256_bytes(canon(cb).encode()), treatment_sha=sha256_bytes(canon(ct).encode())))
                checks.add(f"I2.input.{name}.{fam}.{num}", (cb["bgra_sha256"], cb["width"], cb["height"]) == (mp["bgra_sha256"], mp["width"], mp["height"]),
                           "full-pass input equals admitted page")
                key = (fam, num)
                digest = sha256_bytes(canon(cb).encode())
                if key not in reference:
                    reference[key] = (name, digest, cb)
                else:
                    checks.add(f"I3.runs_equal.{name}.{fam}.{num}", digest == reference[key][1],
                               f"full pass equals run {reference[key][0]}", digest)
                gb, gt = per_arm["baseline"][num].get("grids"), per_arm["treatment"][num].get("grids")
                if gb is not None or gt is not None:
                    checks.add(f"I4.grids_equal.{name}.{fam}.{num}", gb == gt, "detected grid identical in both arms")
                if args.archive_root and fam in ("H", "A") and key not in archive_classes:
                    raw_path = Path(args.archive_root) / fam / "windows" / f"raw-{num:03d}.json"
                    win_path = Path(args.archive_root) / fam / "windows" / f"window-{num:03d}.json"
                    raw = read_json(raw_path)
                    cls, diff = archive_compare(cb, raw)
                    archive_classes[key] = cls
                    if diff:
                        archive_detail[f"{fam}/{num}"] = diff
                    checks.add(f"X1.archive.{fam}.{num}", cls == "identical", "current full pass equals WP-0015 archive raw (disclosure only)",
                               cls, gating=False)
                    checks.add(f"X1.archive_input.{fam}.{num}", raw.get("rgb_sha256") == mp["rgb_sha256"],
                               "archive raster digest equals admitted page RGB", raw.get("rgb_sha256"), gating=False)
                    if gb is not None and win_path.exists():
                        arch_grids = read_json(win_path).get("rule_tables")
                        same = arch_grids == gb
                        grid_archive[f"{fam}/{num}"] = same
                        checks.add(f"X2.archive_grid.{fam}.{num}", same, "detected grid equals archive window rule_tables (disclosure)", gating=False)
    finish(Path(args.out), "wp0019-review-identity", checks,
           dict(runs={n: dict(path=r["path"], sha256=r["sha256"]) for n, r in runs.items()},
                full_pass_digests={f"{k[0]}/{k[1]}": v[1] for k, v in sorted(reference.items())},
                archive_classes={f"{k[0]}/{k[1]}": v for k, v in sorted(archive_classes.items())},
                archive_class_counts=dict(Counter(archive_classes.values())), archive_text_differences=archive_detail,
                archive_grid_equal=grid_archive))


# ---------------------------------------------------------------- timing
def cmd_timing(args):
    checks = Checks()
    pins = load_pins(args.pins)
    runs = load_runs(args.run)
    metrics = {}
    intervals = []
    for name, run in runs.items():
        b = run["bundle"]
        order = b.get("order")
        seq = [a["arm"] for a in b["arms"]]
        checks.add(f"T1.order.{name}", (order, seq) in (("AB", ["baseline", "treatment"]), ("BA", ["treatment", "baseline"])),
                   "AB = full-only then full-plus-crops; BA reverse", [order, seq])
        wpid = (b.get("worker") or {}).get("pid")
        pids = [a.get("pid") for a in b["arms"]] + [((b.get("warmup") or {}).get("pid"))]
        checks.add(f"T2.same_worker.{name}", wpid is not None and all(p == wpid for p in pids),
                   "warm-up and both arms in the same warm worker process", [wpid] + pids)
        wu = b.get("warmup")
        first = min(a["start_ns"] for a in b["arms"])
        checks.add(f"T3.warmup.{name}", bool(wu) and wu.get("excluded") is True and wu["end_ns"] <= first,
                   "excluded warm-up precedes both arms", wu and {k: wu.get(k) for k in ("input", "excluded", "start_ns", "end_ns")})
        a1, a2 = b["arms"][0], b["arms"][1]
        checks.add(f"T4.serial.{name}", a1["end_ns"] <= a2["start_ns"], "arms do not overlap", [a1["start_ns"], a1["end_ns"], a2["start_ns"], a2["end_ns"]])
        arms = arms_of(b)
        page_sets = {}
        rm = dict(order=order, arms={})
        for arm_name in ARMS:
            arm = arms[arm_name]
            pages, crops, fam_rows = 0, 0, {}
            inside = True
            for f in arm["families"]:
                fp = f["pages"]
                page_sets.setdefault(f["family"], {})[arm_name] = [p["page"] for p in fp]
                nc = sum(len(p.get("crops") or []) for p in fp)
                for p in fp:
                    inside &= (p.get("start_ns") is not None and p.get("durable_ns") is not None and
                               arm["start_ns"] <= p["start_ns"] <= p["durable_ns"] <= arm["end_ns"])
                    full = p["full"]
                    if full.get("start_ns") is not None:
                        inside &= arm["start_ns"] <= full["start_ns"] <= full.get("end_ns", full["start_ns"]) <= arm["end_ns"]
                fdur = (f["end_ns"] - f["start_ns"]) / 1e9 if f.get("end_ns") is not None else None
                fam_rows[f["family"]] = dict(pages=len(fp), crops=nc, seconds=fdur,
                                             pages_per_min=None if not fdur else 60 * len(fp) / fdur,
                                             ms_per_page=None if not fdur else 1000 * fdur / len(fp),
                                             crops_per_page=nc / len(fp) if fp else None)
                pages += len(fp)
                crops += nc
            checks.add(f"T5.own_full_pass_inside_arm.{name}.{arm_name}", inside,
                       "every page (and its own full pass) starts and becomes durable inside this arm's interval")
            total = (arm["end_ns"] - arm["start_ns"]) / 1e9
            rm["arms"][arm_name] = dict(startup_s=None if arm.get("setup_ns") is None else arm["setup_ns"] / 1e9,
                                        ready_to_durable_s=total, pages=pages, pages_per_min=60 * pages / total if total > 0 else None,
                                        ms_per_page=1000 * total / pages if pages else None, attempted_crops=crops,
                                        crops_per_page=crops / pages if pages else None, families=fam_rows)
            intervals.append((name, arm_name, arm["start_ns"], arm["end_ns"], b.get("clock", "qpc")))
        for fam, sets in page_sets.items():
            checks.add(f"T6.same_pages.{name}.{fam}", sets.get("baseline") == sets.get("treatment") and
                       fam in pins and sets.get("baseline") == list(range(1, pins[fam]["pages"] + 1)),
                       "identical complete page sequence in both arms", sets)
        base, treat = rm["arms"]["baseline"], rm["arms"]["treatment"]
        rm["added_ms_per_page"] = 1000 * (treat["ready_to_durable_s"] - base["ready_to_durable_s"]) / base["pages"] if base["pages"] else None
        rm["worker_startup_s"] = None if (b.get("worker") or {}).get("startup_ns") is None else b["worker"]["startup_ns"] / 1e9
        metrics[name] = rm
        checks.add(f"T7.baseline_no_crops.{name}", base["attempted_crops"] == 0, "baseline attempts no crop", base["attempted_crops"])
    overlaps = []
    for i, x in enumerate(intervals):
        for y in intervals[i + 1:]:
            if x[0] != y[0] and x[4] == y[4] and x[2] < y[3] and y[2] < x[3]:
                overlaps.append([x[:2], y[:2]])
    checks.add("T8.runs_serial", not overlaps, "timed runs did not overlap one another (same clock domain)", overlaps)
    by_order = {}
    for name, rm in metrics.items():
        by_order.setdefault(rm["order"], []).append(name)
    summary = dict(by_order=by_order)
    for group in sorted({n.rsplit("-", 1)[0] for n in metrics}):
        pair = {metrics[n]["order"]: metrics[n] for n in metrics if n.rsplit("-", 1)[0] == group}
        if {"AB", "BA"} <= set(pair):
            added = [pair[o]["added_ms_per_page"] for o in ("AB", "BA")]
            tppm = [pair[o]["arms"]["treatment"]["pages_per_min"] for o in ("AB", "BA")]
            summary[group] = dict(added_ms_per_page_AB_BA=added, added_ms_per_page_mean=sum(added) / 2,
                                  treatment_pages_per_min_AB_BA=tppm, treatment_pages_per_min_min=min(tppm),
                                  stage2_speed_rule_met=min(tppm) >= args.ppm_threshold)
    finish(Path(args.out), "wp0019-review-timing", checks, dict(metrics=metrics, summary=summary, ppm_threshold=args.ppm_threshold,
                                                               note="Stage 1 timing is form-specific and non-gating; the 30 pages/min rule applies to fresh Stage 2"))


# ---------------------------------------------------------------- static scan (truth/key-derived selection)
TEXT_SUFFIX = {".py", ".ps1", ".psm1", ".cs", ".csproj", ".json", ".md", ".txt", ".toml", ".cfg", ".ini", ".yaml", ".yml"}
CODE_SUFFIX = {".py", ".ps1", ".psm1", ".cs"}
KEYWORDS = ["truth", "historical-score", "wp0018-data", "eLedgerCare-Speed", "score.py", "critical", "expected",
            "answer", "ground", "reference_bbox", "label"]


def iter_sources(args):
    for d in args.source or []:
        for p in sorted(Path(d).rglob("*")):
            if p.is_file() and p.suffix.lower() in TEXT_SUFFIX:
                yield str(p), p.read_bytes()
    for spec in args.git or []:
        rev, path = spec.split(":", 1)
        names = subprocess.run(["git", "ls-tree", "-r", "--name-only", rev, "--", path], capture_output=True, text=True, check=True).stdout.split()
        for n in names:
            if Path(n).suffix.lower() in TEXT_SUFFIX:
                yield f"{rev[:12]}:{n}", subprocess.run(["git", "show", f"{rev}:{n}"], capture_output=True, check=True).stdout


def cmd_static(args):
    checks = Checks()
    tokens = set()
    for t in (args.truth_H, args.truth_A):
        truth = read_json(t)
        for p in truth["pages"]:
            for ln in p["lines"]:
                if ln["critical"]:
                    tokens.add(ln["critical"])
            for tb in p["tables"]:
                for row in tb["rows"]:
                    for c in row:
                        if c["critical"] and c["text"]:
                            tokens.add(" ".join(c["text"].split()))
    strong = sorted(t for t in tokens if len(t) >= 6 and any(ch.isdigit() for ch in t) and any(ch.isalpha() or ch == "-" for ch in t))
    hits, keyword_hits, files = [], [], []
    for label, data in iter_sources(args):
        text = data.decode("utf-8", errors="replace")
        files.append(dict(file=label, sha256=sha256_bytes(data), bytes=len(data)))
        is_code = Path(label.split(":", 1)[-1]).suffix.lower() in CODE_SUFFIX
        for t in strong:
            for m in re.finditer(re.escape(t), text):
                line = text.count("\n", 0, m.start()) + 1
                hits.append(dict(file=label, line=line, token=t, code=is_code))
        if is_code:
            for i, ln in enumerate(text.splitlines(), 1):
                for k in KEYWORDS:
                    if k.lower() in ln.lower():
                        keyword_hits.append(dict(file=label, line=i, keyword=k, text=ln.strip()[:200]))
    code_hits = [h for h in hits if h["code"]]
    checks.add("K1.no_reference_tokens_in_code", not code_hits, "no critical reference token (>=6 chars, digit) appears in author code", code_hits[:50])
    checks.add("K2.files_scanned", bool(files), "source files scanned", len(files))
    finish(Path(args.out), "wp0019-review-static", checks,
           dict(files=files, strong_tokens=len(strong), token_hits_all=hits[:500], keyword_hits=keyword_hits[:2000],
                note="keyword hits require manual inspection and are not themselves failures"))


# ---------------------------------------------------------------- audit logs of reviewer replays
IMAGE_SUFFIX = (".bmp", ".png", ".tif", ".tiff", ".jpg", ".jpeg", ".gif")
TRUTH_NAMES = ("truth.json", "historical-score.json", "answer", "key.json", "labels")


def cmd_audit(args):
    checks = Checks()
    allow = {a.lower() for a in (args.allow_exe or [])}
    summary = {}
    for spec in args.log:
        name, path = spec.split("=", 1)
        log = read_json(path)
        ev = log["events"]
        procs = [e for e in ev if e["event"] == "subprocess.Popen"]
        others = [e for e in ev if e["event"] in ("os.system", "os.exec", "os.spawn", "os.posix_spawn")]

        def exe_name(e):
            x = e.get("executable")
            if not x:
                argv = e.get("argv")
                x = argv[0] if isinstance(argv, list) and argv else str(argv or "").split(" ")[0]
            return Path(str(x).strip('"')).name.lower()

        exes = sorted({exe_name(e) for e in procs})
        checks.add(f"A0.no_shell_spawn.{name}", not others, "no os.system/exec/spawn process launch", others[:10])
        img_writes = [e for e in ev if e["event"] == "open" and (e.get("path") or "").lower().endswith(IMAGE_SUFFIX) and
                      any(m in str(e.get("mode", "")) for m in ("w", "a", "x", "+"))]
        truthy = [e for e in ev if e["event"] == "open" and any(t in Path(e.get("path") or "").name.lower() for t in TRUTH_NAMES)]
        net = [v for v in log["violations"] if v.get("note") == "network event"]
        denied = [v for v in log["violations"] if v.get("note") != "network event"]
        checks.add(f"A1.no_denied_reads.{name}", not denied, "no open/list below a denied prefix (truth, scores, keys, archive, author scratch)", denied[:20])
        checks.add(f"A2.no_network.{name}", not net, "no socket/urllib event in the Python process", net[:20])
        checks.add(f"A3.processes.{name}", bool(exes) and (not allow or set(exes) <= allow), "only the declared worker executable is launched", exes)
        checks.add(f"A4.crops_in_memory.{name}", not img_writes, "no image file is written during the run (crops stay in memory)", img_writes[:20])
        checks.add(f"A5.no_truth_names.{name}", not truthy, "no file named like ground truth/score/keys is opened", truthy[:20])
        checks.add(f"A6.complete_log.{name}", not log.get("truncated"), "audit log not truncated")
        summary[name] = dict(path=str(Path(path).resolve()), sha256=sha256_file(path), counts=log["counts"], executables=exes,
                             subprocesses=[dict(executable=e.get("executable"), argv=e.get("argv"), cwd=e.get("cwd")) for e in procs][:20])
    finish(Path(args.out), "wp0019-review-audit-summary", checks, dict(logs=summary))


# ---------------------------------------------------------------- combined decision
def cmd_decision(args):
    parts = {}
    for k in ("env", "inputs", "geometry", "identity", "timing", "static", "score", "audit"):
        v = getattr(args, k)
        parts[k] = dict(path=v, sha256=sha256_file(v), doc=read_json(v)) if v else None
    control_fail = {}
    for k in ("env", "inputs", "geometry", "identity", "static", "audit"):
        if parts[k] is None:
            control_fail[k] = ["NOT_SUPPLIED"]
        else:
            f = parts[k]["doc"].get("failed_checks", [])
            if f:
                control_fail[k] = f
    timing_fail = parts["timing"]["doc"].get("failed_checks", []) if parts["timing"] else ["NOT_SUPPLIED"]
    score = parts["score"]["doc"] if parts["score"] else None
    score_fail = score.get("failed_checks", []) if score else ["NOT_SUPPLIED"]
    verdict_score = score["gate"]["score_component"] if score else "INCONCLUSIVE"
    if control_fail or score_fail or (timing_fail and args.timing_gating):
        verdict = "INCONCLUSIVE_CONTROL"
    elif verdict_score == "PASS":
        verdict = "STAGE2_RELEASE_SUPPORTED"
    elif verdict_score in ("FAIL_QUALITY", "FAIL_NOT_REPRODUCIBLE"):
        verdict = "CLOSE_AT_STAGE1"
    else:
        verdict = "INCONCLUSIVE_CONTROL"
    doc = dict(kind="wp0019-review-decision", stage=args.stage, verdict=verdict, score_component=verdict_score,
               control_failures=control_fail, score_failures=score_fail, timing_failures=timing_fail,
               timing_gating=args.timing_gating, inputs={k: (None if v is None else dict(path=v["path"], sha256=v["sha256"])) for k, v in parts.items()},
               gate=score["gate"] if score else None,
               rule="STAGE2 only if every control passes, every run is evaluable, pooled H+A net critical WR-RW >= 1 and RW=0 per family "
                    "in every run, and per-position outputs are identical across all runs; Stage 2 additionally gates timing")
    sha = write_new(Path(args.out), doc)
    print(json.dumps(dict(out=args.out, sha256=sha, verdict=verdict, control_failures=control_fail, score_failures=score_fail), indent=1))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("env")
    e.add_argument("--out", required=True)
    e.add_argument("--extra", nargs="*")
    e.add_argument("--watch", nargs="*")
    e.add_argument("--expect")
    i = sub.add_parser("inputs")
    for fam in ("H", "A"):
        i.add_argument(f"--manifest-{fam}")
        i.add_argument(f"--pdf-{fam}")
        i.add_argument(f"--rasters-{fam}")
    i.add_argument("--families", nargs="+", default=["H", "A"], choices=["H", "A"])
    i.add_argument("--expected", help="preregistered expected-bgra.json")
    i.add_argument("--copy-to")
    i.add_argument("--out", required=True)
    fr = sub.add_parser("inputs-fresh")
    fr.add_argument("--manifest", action="append", required=True, help="FAMILY=manifest.json")
    fr.add_argument("--pdf", action="append", default=[], help="FAMILY=source.pdf (optional render check)")
    fr.add_argument("--commitments", required=True, help="coordinator raster commitment JSON (no keys)")
    fr.add_argument("--pins", required=True)
    fr.add_argument("--out", required=True)
    xb = sub.add_parser("expect-bgra")
    for fam in ("H", "A"):
        xb.add_argument(f"--pdf-{fam}", required=True)
        xb.add_argument(f"--rasters-{fam}", required=True)
    xb.add_argument("--out", required=True)
    g = sub.add_parser("geometry")
    g.add_argument("--manifest", action="append", required=True, help="FAMILY=manifest.json")
    g.add_argument("--run", action="append", required=True)
    g.add_argument("--inset", type=float)
    g.add_argument("--padding", type=float)
    g.add_argument("--out", required=True)
    d = sub.add_parser("identity")
    d.add_argument("--manifest", action="append", required=True, help="FAMILY=manifest.json")
    d.add_argument("--run", action="append", required=True)
    d.add_argument("--archive-root")
    d.add_argument("--out", required=True)
    t = sub.add_parser("timing")
    t.add_argument("--run", action="append", required=True)
    t.add_argument("--ppm-threshold", type=float, default=30.0)
    t.add_argument("--pins")
    t.add_argument("--out", required=True)
    s = sub.add_parser("static")
    s.add_argument("--source", action="append")
    s.add_argument("--git", action="append", help="REV:PATH")
    s.add_argument("--truth-H", required=True)
    s.add_argument("--truth-A", required=True)
    s.add_argument("--out", required=True)
    au = sub.add_parser("audit")
    au.add_argument("--log", action="append", required=True, help="NAME=audit log path")
    au.add_argument("--allow-exe", nargs="*")
    au.add_argument("--out", required=True)
    c = sub.add_parser("decision")
    for k in ("env", "inputs", "geometry", "identity", "timing", "static", "score", "audit"):
        c.add_argument(f"--{k}")
    c.add_argument("--stage", default="1")
    c.add_argument("--timing-gating", action="store_true")
    c.add_argument("--out", required=True)
    args = p.parse_args()
    dict(env=cmd_env, inputs=cmd_inputs, geometry=cmd_geometry, **{"expect-bgra": cmd_expect_bgra, "inputs-fresh": cmd_inputs_fresh}, identity=cmd_identity, timing=cmd_timing,
         static=cmd_static, audit=cmd_audit, decision=cmd_decision)[args.cmd](args)


if __name__ == "__main__":
    main()
