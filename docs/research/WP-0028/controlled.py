"""Admit only exact manifest-routed inputs. Operate on both members together."""
import io
import json
import re
from pathlib import Path
from zipfile import ZipFile

import online
from inputs import check, sha
from measurement import comparable, measure, query_context
from score_math import NAMES, TIMES, trajectory


FROZEN = {
    12: ("7682788164e1efa4ce425424", "c68d80f8a27dd80a95e5aea0",
         (("097e2bb5c201709ec32fbb54", "a3043c8819fd5b7a19f5a713"),
          ("b1319c493624d146b9905f68", "64096a9ae03655cf255b4b33"))),
    30: ("05c474726fa62f8cf7cafa17", "3d942ef5cf4ec8f1ce6b503f",
         (("eed9f381739ceff89219e5ef", "722b1395e7a05852683c965a"),
          ("64ca02ee321c80c200e01a1a", "a97ca2a8aa299398728312fb"))),
}


def empty(t, reason):
    return {"pointer": None, "source_checkpoint": None,
            "role": "normal_target_before_write" if t == "t3" else "retrospective",
            "target_available": None, "candidate_order": None, "controller": None,
            "query_sha256": None, "matrix_sha256": None, "read_sha256": None,
            "owner_columns_sha256": None, "scores": dict.fromkeys(NAMES),
            "score_bytes_f32le_sha256": None, "exact_top_tie": None, "zero_read": None,
            "top_score_pass": None, "top_gap_pass": None,
            "unit_column_controls": {"unit":None, "column":None}, "typed": None, "reason": reason}


def check_pair(pair):
    n = pair["horizon"]
    pid, target, ids = FROZEN[n]
    check((pair["template"],pair["pair"],pair["base_target"]) == (f"T1-{n}",pid,target),
          "fixture identity drift")
    members = sorted(pair["members"], key=lambda m:m["owner"])
    check(tuple((m["binder"],m["target"]) for m in members) == ids and
          tuple(m["owner"] for m in members) == NAMES, "frozen member identity drift")
    missing = []
    for member in members:
        windows = member["windows"]
        check([w["window"] for w in windows] == list(range(1, n//3+1)), "incomplete ordered window list")
        for win in windows:
            rgbs = [p["rgb_sha256"] for p in win["pages"]]
            key = sha((json.dumps(rgbs, indent=2) + "\n").encode("ascii"))
            check(len(rgbs) == 3 and key == win["rgb_key"], "source whole-window identity drift")
            if win["feature"] is None:
                missing.append({"binder": member["binder"], "window": win["window"], "rgb_key": key,
                                "ordered_rgb_sha256": rgbs})
    check(pair["admitted"] == (not missing), "fixture admission contradicts missing windows")
    return members, missing


def route(w, work, blob, cache):
    f = w["feature"]
    archive = f["archive"]
    check(re.fullmatch(r"docs/reviews/WP-0026/(?:cal-features|train-features|train-c1|h0)-primary/primary-001\.zip",
                       archive), "unreleased feature archive")
    check(re.fullmatch(r"[0-9a-f]{40}",f["archive_revision"]), "archive requires immutable revision")
    if archive not in cache:
        cache[archive] = (f["archive_revision"], ZipFile(io.BytesIO(blob(f["archive_revision"],archive))))
    rev, z = cache[archive]
    check(rev == f["archive_revision"], "mixed revisions for archive")
    prefix = f["prefix"]
    check(re.fullmatch(r"runs/[A-Za-z0-9-]+/sensor/[A-Za-z0-9]+/",prefix), "unexpected feature prefix")
    receipt = json.loads(z.read(prefix+"receipt.json"))
    check(receipt["split"] in ("cal","train") and receipt["verified"] and receipt["tag"] == f["tag"],
          "feature receipt identity")
    check([p["rgb_sha256"] for p in w["pages"]] == [p["rgb_sha256"] for p in receipt["pages"]],
          "ordered RGB binding failed")
    dest = work / "controlled-inputs" / w["rgb_key"]
    dest.mkdir(parents=True, exist_ok=True)
    for name, hkey in (("metadata.json","metadata_sha256"), ("pooled.f32","pooled_sha256"),
                       ("through-eos.u32le","through_eos_sha256")):
        data = z.read(prefix + name)
        check(sha(data) == f[hkey] == receipt["artifacts"][name], "feature digest mismatch")
        if name != "through-eos.u32le":
            path = dest / name
            if path.exists():
                check(path.read_bytes() == data, "unstable same-source feature identity")
            else:
                with path.open("xb") as out:
                    out.write(data)
    return dest


def controlled(model, cuts, manifest, work, blob):
    pairs = manifest["pairs"]
    check(len(pairs) == 2 and {p["horizon"] for p in pairs} == set(FROZEN), "wrong controlled denominator")
    output, cache = [], {}
    try:
        for p in pairs:
            members, missing = check_pair(p)
            reason, measures = None, []
            if missing:
                reason = "missing_exact_whole_window_features"
            else:
                final = [m["windows"][-1] for m in members]
                keys = ("metadata_sha256","pooled_sha256","through_eos_sha256")
                if final[0]["rgb_key"] != final[1]["rgb_key"] or any(
                        final[0]["feature"][k] != final[1]["feature"][k] for k in keys):
                    reason = "different_final_window_source_or_features"
                else:
                    paths = [[route(w,work,blob,cache) for w in m["windows"]] for m in members]
                    contexts = [query_context(model, [online.load_window(w) for w in seq]) for seq in paths]
                    reason = comparable(contexts)
                    if reason is None:
                        measures = [measure(model, seq, cuts)[:2] for seq in paths]
            result = []
            for i,m in enumerate(members):
                checkpoints, parity = (measures[i] if measures else ({t:empty(t,reason) for t in TIMES}, None))
                result.append({"binder":m["binder"], "target":m["target"], "owner":m["owner"],
                               "pdf":m["source_pdf"], "source_pdf_sha256":m["source_pdf_sha256"],
                               "rgb_keys_by_window":[w["rgb_key"] for w in m["windows"]],
                               "parity":parity, "checkpoints":checkpoints})
            note = ("Both members are unmeasured at t1, t2 and t3. " + reason.replace("_"," ") + "."
                    if reason else "See the signed trajectory for each checkpoint.")
            output.append({"template":p["template"], "horizon":p["horizon"], "pair":p["pair"],
                           "source_target":p["base_target"], "fixture_admitted":p["admitted"],
                           "counts":{"planned":1, "admitted":int(reason is None), "completed":int(bool(measures))},
                           "reason":reason, "trajectory":note, "missing":missing,
                           "members":result, "metrics":trajectory(result)})
    finally:
        for _, z in cache.values():
            z.close()
    return output
