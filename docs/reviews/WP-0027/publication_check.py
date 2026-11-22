"""Verify deterministic author outputs and semantic table equality against a fresh candidate execution."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import SCRATCH,blob,save,sha

def verify(reader_evidence,reader_run,prefix):
    rank_evidence="0573f69c481eea2e815899e00ddd5e68bb4e3c42"
    ranks={}
    for name in ("owner-rankings.json","owner-progression.json"):
        actual=(SCRATCH/"rank-author-r1"/name).read_bytes()
        published=blob(rank_evidence,"docs/research/WP-0027/owners/"+name)
        assert published==actual
        ranks[name]=sha(actual)
    folder=SCRATCH/reader_run/"results"
    t="parser-cases.json"
    actual=json.loads((folder/t).read_bytes())
    published=json.loads(blob(reader_evidence,prefix+"/"+t))
    key=lambda row:{k:v for k,v in row.items() if k!="cpu_wall_ns"}
    assert len(actual["cases"])==len(published["cases"])==actual["matched"]==published["matched"]
    actual_rows={c["case"]:key(c) for c in actual["cases"]}
    assert actual_rows=={c["case"]:key(c) for c in published["cases"]}
    saved={}
    for name in ("b01w01H.json","b01w02H.json","k0014-native.json","k0014-source.json","k0014-ids-through-eos.u32le","k0014.json"):
        data=(folder/name).read_bytes()
        assert data==blob(reader_evidence,prefix+"/"+name)
        saved[name]=sha(data)
    rr=json.loads((SCRATCH/"rank-author-r1/runtime.json").read_bytes())
    return {"rank_candidate":rr["worktree_head"],"rank_evidence":rank_evidence,"rank_outputs":ranks,
            "rank_replay_seconds":rr["process_replay_wall_seconds"],"reader_candidate":actual["execution_head"],
            "reader_evidence":reader_evidence,"reader_cases":len(actual_rows),"reader_exact_witnesses":saved,
            "reader_replay_seconds":actual["cpu_wall_ns"]/1e9,"reader_table_run_sha":sha((folder/t).read_bytes()),
            "published_reader_table_sha":sha(blob(reader_evidence,prefix+"/"+t)),
            "case_level_comparison":"all fields except individual case time; whole fixed witnesses matched byte for byte"}

if __name__=="__main__":
    save(SCRATCH/sys.argv[4],verify(*sys.argv[1:4]))

