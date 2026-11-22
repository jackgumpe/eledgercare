"""Compare before/after identical independent inputs and verify every source-specific nontext allowance."""
from collections import Counter
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import SCRATCH,blob,save,sha

FIXED="8bf8ec2c9eb6eff282366d61711ec1a249f4760a"
def data(name):
    return json.loads((SCRATCH/name).read_bytes())

def check():
    for f in ("source_ruling.py","review_regression.py"):
        assert (SCRATCH/"reader-source/docs/research/WP-0027/reader"/f).read_bytes()==blob(FIXED,"docs/research/WP-0027/reader/"+f)
    first=data("reader-challenge-r1.json")
    second=data("reader-challenge-r2.json")
    assert second["candidate"]==FIXED and not second["mismatches"]
    old={r["case"]:r for r in first["cases"]}
    new={r["case"]:r for r in second["cases"]}
    assert old.keys()==new.keys() and len(old)==31
    changes=[]
    required=Counter()
    for name,row in new.items():
        for f in ("expected","native_sha256","binding_sha256","trusted_binding_sha256","ordered_images"):
            assert row[f]==old[name][f]
        required[row["expected"]]+=1
        if row["actual"]!=old[name]["actual"]:
            changes.append({"case":name,"before":old[name]["actual"],"after":row["actual"],
                            "new_reason":row["reason"],"native_sha256":row["native_sha256"]})
    assert len(changes)==1 and changes[0]["case"]=="source raster contains untranscribed text/ordinary"
    assert changes[0]["before"]=="A" and changes[0]["after"]=="U"
    original=data("h0-residual-r1.json")["pages"]
    allowances=[]
    for tag in ("b01w01H","b01w02H"):
        mapped=data("reader-replay-02/results/"+tag+".json")["candidate"]["source_to_section"]
        for m in mapped:
            source=m["source"]
            n=source["page"]
            independent=original[n-1]
            proof=source["verified_pdf_ruling"]
            assert source["ink_outside_source_lines"]==independent["residual_pixel_count"]
            if proof is None:
                assert independent["residual_pixel_count"]==0
                continue
            assert proof["full_rerender_rgb_sha256"]==independent["complete_original_rgb_sha256"]
            assert proof["nontext_layer_rgb_sha256"]==independent["lines_only_full_raster_sha256"]
            assert proof["differing_residual_rgb_pixels"]==independent["residual_samples_differing_from_independent_text_removed_pdf"]==0
            segments=[[p[1:] for p in path] for path in independent["path_geometry_pt"]]
            assert segments==proof["axis_aligned_segments_pt"]
            assert proof["actual_residual_rgb_sha256"]==proof["path_residual_rgb_sha256"]
            allowances.append({"page":n,"tag":tag,"num_paths":len(segments),"residual_pixels":source["ink_outside_source_lines"],
                               "full_path_only_rgb":proof["nontext_layer_rgb_sha256"],"residual_rgb":proof["actual_residual_rgb_sha256"],
                               "independent_surviving_path_objects_and_all_residual_pixels_verified":True})
    assert [a["page"] for a in allowances]==[1,4]
    return {"candidate":FIXED,"identical_independent_fixtures":len(old),"requirements":dict(required),
            "changed_outcomes":changes,"verified_special_cases":allowances,
            "first_evidence_sha256":sha((SCRATCH/"reader-challenge-r1.json").read_bytes()),
            "second_evidence_sha256":sha((SCRATCH/"reader-challenge-r2.json").read_bytes())}

if __name__=="__main__":
    save(SCRATCH/sys.argv[1],check())

