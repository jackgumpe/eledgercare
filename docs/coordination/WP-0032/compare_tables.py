"""Cross-check both independent WP-0032 tables and the coordinator's archived-tensor accounting."""
import hashlib
import json
import math
import struct
import subprocess
import sys
from pathlib import Path

NAMES = ("Alder", "Cedar")


def payload(rev, role, filename):
    path = f"docs/{role}/WP-0032/evidence/{filename}"
    return subprocess.check_output(["git", "cat-file", "blob", f"{rev}:{path}"])


def unpack(hex_text):
    data = bytes.fromhex(hex_text)
    return struct.unpack("<128d", data)


def reconcile(author_sha, reviewer_sha, scalar):
    summary = {}
    counts = {"native_byte_pairs": 0, "component_coordinates": 0}

    def check(group, location, *values):
        assert all(map(math.isfinite, values)), location
        error = max(values) - min(values)
        limit = 2e-5 * (1 + max(map(abs, values)))
        assert error <= limit, (group, location, values)
        state = summary.setdefault(group, {"checks": 0, "max_absolute": -1.0})
        state["checks"] += 1
        if error > state["max_absolute"]:
            state.update(max_absolute=error, at=location, values=values, limit=limit)

    for rev, role, name in [(author_sha,"research","runtime.json"),(reviewer_sha,"reviews","run.json")]:
        runtime = json.loads(payload(rev,role,name))
        assert runtime["deterministic"] and runtime["torch"] == "2.13.0+cpu"
        for filename, digest in runtime["evidence_sha256"].items():
            assert hashlib.sha256(payload(rev,role,filename)).hexdigest() == digest
    rt = json.loads(payload(reviewer_sha, "reviews", "tables.json"))
    for arm in ("M1", "M3"):
        doc = json.loads(payload(author_sha, "research", arm+".json"))
        assert set(doc["cells"]) == set(rt["cells"][arm]) == set(scalar[arm])
        for tag, a in doc["cells"].items():
            r, root = rt["cells"][arm][tag], scalar[arm][tag]
            label = arm + "/" + tag
            assert a["binding"]["native_score_f32le"] == r["binding"]["score_f32le"] == root["native_score_f32le"]
            assert a["native_read"]["bytes_le"] == r["binding"]["native_read_f32le"]
            counts["native_byte_pairs"] += 1
            for stage in (("omitted","restored") if arm == "M1" else ("restored",)):
                for field in ("numerator","denominator","margin"):
                    check(stage+"_"+field,label,a[stage]["metrics"][field],r[stage][field],root[stage+"_"+field])
            for name in NAMES:
                check("candidate_score",label+"/"+name,a["restored"]["metrics"][name.lower()+"_score"],
                      r["restored"]["scores"][name],root["reconstructed_scores"][name])
            if arm == "M1":
                for i, term in enumerate(("R","V","E")):
                    x,y = a["terms"][term],r["components"][term]
                    check("term_numerator",label+"/"+term,x["numerator"],y["numerator"],root["term_numerators"][i])
                    check("common_normalized_term",label+"/"+term,x["numerator_over_common_native_denominator"],
                          y["common_denominator_contribution"],root["term_margin_contributions"][i])
                    for j,(left,right) in enumerate(zip(unpack(x["vector"]["bytes_le"]),unpack(y["vector_f64le"]),strict=True)):
                        check("term_vector",f"{label}/{term}[{j}]",left,right)
                        counts["component_coordinates"] += 1
            else:
                for key, first, second in (("z","owner_key_dot","z"),("gain","beta_times_owner_key_dot","scale"),("beta","beta","beta")):
                    check("empty_"+key,label,a[first],r[second],root[key])
                for i,name in enumerate(NAMES):
                    x,y = a["value"]["alignment"][name],r["alignments"][name]
                    check("raw_value_alignment",label+"/"+name,x["raw_dot"],y["raw_dot"],root["anchor_dot_v"][i])
                    check("normalized_value_alignment",label+"/"+name,x["dot_with_epsilon_normalized_value"],
                          y["eps_normalized_value_dot"],root["anchor_dot_direction_v"][i])
        for prefix,d in doc["alder_donor_minus_cedar_donor"].items():
            other = rt["donor_Alder_minus_Cedar"][arm+"/"+prefix]
            if arm == "M1":
                for stage in ("omitted","restored"):
                    for field in ("margin","numerator"):
                        check("donor_"+stage+"_"+field,prefix,d[field][stage]["value"],other[stage][field]["value"],
                              scalar["M1_donor_contrasts"][prefix][stage+"_"+field])
            else:
                for name in NAMES:
                    check("donor_score_shift",name,d[name.lower()+"_score"]["restored"]["value"],
                          other["restored"][name]["value"],scalar["M3_candidate_shifts"][name])
                check("D0",arm,d["margin"]["restored"]["value"],other["restored"]["margin"]["value"],scalar["M3_reconstructed_D0"])
    assert counts == {"native_byte_pairs":6,"component_coordinates":1536}
    return {"author_evidence":author_sha,"reviewer_independent_evidence":reviewer_sha,**counts,
            "comparison_groups":summary,"root_scalar_tables":scalar}


if __name__ == "__main__":
    author,reviewer,scalar_path,output = sys.argv[1:]
    tables = json.loads(Path(scalar_path).read_bytes())
    result = reconcile(author,reviewer,tables)
    with Path(output).open("x",encoding="utf-8",newline="\n") as stream:
        json.dump(result,stream,indent=2,allow_nan=False)
        stream.write("\n")
