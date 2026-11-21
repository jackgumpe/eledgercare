"""Independently exercise the signed worker's archival fault cases in reviewer-owned CPU scratch."""
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from zipfile import ZipFile

sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit_common import ROOT,SCRATCH,cpu,pinned,save,sha

def exercise(path,pin):
    release = pinned(path,pin)
    dev = Path(release["worktree"])
    names = ("docs/research/WP-0026/worker.py","docs/research/WP-0026/preflight.py",
             "docs/research/WP-0024/sensor/capture.py","docs/research/WP-0023/trial/stock.py")
    digests = {f:sha((dev/f).read_bytes()) for f in names}
    assert all(v == release["source_files"][k] for k,v in digests.items())
    sys.path.insert(0,str(dev/"docs/research/WP-0026"))
    import preflight
    sources = ROOT/"docs/reviews/WP-0024/h0-r1.zip"
    with TemporaryDirectory(dir=SCRATCH) as d, ZipFile(sources) as z:
        tmp = Path(d)
        cases = [preflight.exercise(z,tmp,order) for order in ("p1","p2")]
        for case in ("wrong_order","wrong_prompt","study_overlap","warm_eos","scored_hidden"):
            cases.append(preflight.exercise(z,tmp,"p2",case))
        no_hidden = preflight.feature_only(z,tmp)
    assert "torch" not in sys.modules
    return {"candidate":release["review_worktree_head"],"release_sha256":pin,"sources":digests,"cases":cases,
            "pooled_only_archival_stream":no_hidden,"live_model_calls":0}

if __name__ == "__main__":
    cpu()
    save(Path(sys.argv[3]),exercise(Path(sys.argv[1]),sys.argv[2]))
