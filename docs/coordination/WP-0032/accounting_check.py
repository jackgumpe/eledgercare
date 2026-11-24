"""Reconcile the six archived owner readouts in scalar binary64 without executing a probe."""
import hashlib
import json
import math
import struct
import subprocess
import sys
from pathlib import Path

ARCHIVE = "8f31cc66c4878ca086fa5da1498c4a73ed6a6306"
DIRECTORY = "docs/research/WP-0031/evidence"
OWNERS = ("Alder", "Cedar")
EPS = 1e-8
TOL = 2e-5


def blob(name):
    return subprocess.check_output(["git", "cat-file", "blob", f"{ARCHIVE}:{DIRECTORY}/{name}"])


def decode(data):
    return struct.unpack(f"<{len(data) // 4}f", data)


def vec(hex_text):
    return decode(bytes.fromhex(hex_text))


def dot(x, y):
    return math.fsum(a*b for a, b in zip(x, y, strict=True))


def norm(x):
    return math.sqrt(dot(x, x))


def archive_inputs(arm, receipt):
    name = arm + ".json"
    data = blob(name)
    assert hashlib.sha256(data).hexdigest() == receipt[name]
    case = json.loads(data)
    assert case["owner_order"] == list(OWNERS) and case["thresholds"] == [1.0, 0.1]
    return case


def accounting(arm, row, donor, data):
    src = data["sources"][donor]
    query = vec(src["frozen_query_f32le"])[:32]
    u = [x / (norm(query) + EPS) for x in query]
    anchors = vec(src["ordered_anchors_f32le"])
    aa, ac = anchors[:128], anchors[128:]
    axis = [a-c for a, c in zip(aa, ac, strict=True)]
    bundle = src["donor"]["projected_f32le"]
    k, v, (a,), (b,) = [vec(bundle[key]) for key in ("key", "value", "alpha", "beta")]
    z = dot(k[:32], u)
    direct = [b*z*x for x in v]
    if arm == "M1":
        snap = data["sources"][row]["snapshot"]
        raw = blob(snap["matrices_file"])
        assert hashlib.sha256(raw).hexdigest() == snap["matrix_sha256"] and snap["shape"] == [1, 128, 128]
        old = decode(raw)
        rows = [old[t:t+128] for t in range(0, len(old), 128)]
        retained = [a * dot(r[:32], u) for r in rows]
        subtraction = [-a*b*z * dot(r, k) for r in rows]
        saved = data["cells"][row[0]+donor[0]]["read"]
    else:
        retained = subtraction = [0.] * 128
        saved = data["empty_cells"]["0"+donor[0]]["read"]
    assert saved["controller"]["depth"] == 0 and saved["owner_eligible"]
    assert saved["ordered_anchor_sha256"] == hashlib.sha256(bytes.fromhex(src["ordered_anchors_f32le"])).hexdigest()
    assert saved["query_sha256"] == hashlib.sha256(bytes.fromhex(src["frozen_query_f32le"])).hexdigest()
    native = vec(saved["read_f32le"])
    raw_scores = dict(zip(OWNERS, vec(saved["score_f32le"]), strict=True))
    native_margin = raw_scores["Alder"] - raw_scores["Cedar"]
    assert raw_scores == saved["scores"] and native_margin == saved["margin"]
    native_den = norm(native) + EPS
    omission = [r+d for r, d in zip(retained, direct, strict=True)]
    total = [o+e for o, e in zip(omission, subtraction, strict=True)]
    num = dot(axis, total)
    den = norm(total) + EPS
    raw_terms = [dot(axis, term) for term in (retained, direct, subtraction)]
    scores = [dot(anchor, total)/den for anchor in (aa, ac)]
    residuals = {}
    def check(key, lhs, rhs):
        errors = [abs(x-y) for x,y in zip(lhs,rhs,strict=True)]
        ratios = [e / (TOL*(1+max(abs(x),abs(y)))) for e,x,y in zip(errors,lhs,rhs,strict=True)]
        assert max(ratios) <= 1, (arm,row,donor,key, max(ratios))
        residuals[key] = {"max_abs":max(errors), "max_fraction_of_limit":max(ratios)}
    check("owner_vector",total,native)
    check("candidate_scores",scores,[raw_scores[name] for name in OWNERS])
    check("restored_numerator",[num],[dot(axis,native)])
    check("restored_margin",[num/den],[native_margin])
    check("common_denominator_sum",[math.fsum(raw_terms)/native_den],[native_margin])
    result = {"native_score_f32le": saved["score_f32le"], "native_margin":native_margin,
              "native_numerator":dot(axis,native), "native_denominator":native_den,
              "restored_numerator":num, "restored_denominator":den, "restored_margin":num/den,
              "reconstructed_scores":dict(zip(OWNERS,scores,strict=True)), "residuals":residuals}
    if arm == "M1":
        result.update(term_numerators=raw_terms, term_margin_contributions=[n/native_den for n in raw_terms],
                      omitted_numerator=dot(axis,omission), omitted_denominator=norm(omission)+EPS,
                      omitted_margin=dot(axis,omission)/(norm(omission)+EPS))
    else:
        vn = norm(v)
        result.update(z=z, beta=b, gain=b*z, value_norm=vn,
                      anchor_dot_v=[dot(anc,v) for anc in (aa,ac)],
                      anchor_dot_direction_v=[dot(anc,v)/(vn+EPS) for anc in (aa,ac)],
                      gain_after_normalization=b*z/(norm(total)+EPS))
    return result


def main(output):
    receipt = json.loads(blob("runtime.json"))["evidence_sha256"]
    m1,m3 = (archive_inputs(arm,receipt) for arm in ("M1","M3"))
    populated = {r[0]+c[0]:accounting("M1",r,c,m1) for r in OWNERS for c in OWNERS}
    empty = {"0"+c[0]:accounting("M3","zero",c,m3) for c in OWNERS}
    diffs = {}
    for r in ("A","C"):
        a,c=populated[r+"A"],populated[r+"C"]
        diffs[r]={key:a[key]-c[key] for key in ("omitted_numerator","restored_numerator","omitted_margin","restored_margin","native_margin")}
        for metric in ("numerator","margin"):
            diffs[r]["effect_on_"+metric]=diffs[r]["restored_"+metric]-diffs[r]["omitted_"+metric]
    shifts={name:empty["0A"]["reconstructed_scores"][name]-empty["0C"]["reconstructed_scores"][name] for name in OWNERS}
    result={"input_revision":ARCHIVE,"M1_terms":["retained","direct","signed_subtraction"],
            "M1":populated,"M1_donor_contrasts":diffs,"M3":empty,"M3_candidate_shifts":shifts,
            "M3_D0":empty["0A"]["native_margin"]-empty["0C"]["native_margin"],
            "M3_reconstructed_D0":shifts["Alder"]-shifts["Cedar"]}
    with Path(output).open("x",encoding="utf-8",newline="\n") as stream:
        json.dump(result,stream,indent=2,allow_nan=False)
        stream.write("\n")


if __name__=="__main__":
    main(sys.argv[1])
