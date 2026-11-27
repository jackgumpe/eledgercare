"""Compare indistinguishable frozen CPU byte artifacts at the normal score entry."""
import copy
from hashlib import sha256
import json
from pathlib import Path
import struct
import subprocess
import sys


def encode(obj):
    return json.dumps(obj,sort_keys=True,separators=(",",":")).encode()


def cli(path, *args):
    return json.loads(subprocess.check_output([sys.executable,"-B",str(path),*map(str,args)]))


def main(src, fixture, work):
    work.mkdir(parents=True)
    cases={x["case_id"]:x for x in map(json.loads,(fixture/"cases.jsonl").read_bytes().splitlines())}
    results=[]
    for left,right in (("F1.pristine","F1.recompute_forged"),
                       ("F4.pristine","F4.c_late_hook_inactive"),("F4.pristine","F4.c_swap_labels_stay")):
        a,b=cases[left],cases[right]
        ea=json.loads((fixture/a["reference_evidence_path"]).read_bytes())["arms"]
        eb=json.loads((fixture/b["reference_evidence_path"]).read_bytes())["arms"]
        assert ea==eb and a["scenario"]==b["scenario"] and a["injection"]!=b["injection"]
        s=a["scenario"]
        doc=ea["untouched"]["public"]
        doc={"ids":doc["token_ids"],"terminal":doc["finish_reason"]}
        raw=(fixture/s["raw"][0]["input"]).read_bytes()
        contract={"vocab":s["vocab"]["ids"],"page":s["page_id"],"eos":s["eos_id"],"cap":s["max_page_tokens"],
                  "order":s["ngram"]["order"],"window":s["ngram"]["window"],"prompt":s["prompt_ids"],
                  "histories":[s["generated_prefix"]],"raw_words":[[f"{x:08x}" for x, in struct.iter_unpack("<I",raw)]],
                  "document":doc}
        for name, obj in (("case",{"contract":contract,"document":doc,"injections":[]}),("contract",contract)):
            (work/(name+".json")).write_bytes(encode(obj))
        pristine=cli(src/"stock.py","capture",work/"case.json")
        injected=copy.deepcopy(pristine)
        hashes={}
        for phase,rec in eb["observed"]["rows"][0]["captures"].items():
            data=(fixture/"blobs"/(rec["blob"]+".bin")).read_bytes()
            assert sha256(data).hexdigest()==rec["blob"]
            assert pristine["rows"][0]["phases"][phase]["hex"]==data.hex()
            injected["rows"][0]["phases"][phase]["hex"]=data.hex()
            hashes[phase]=rec["blob"]
        assert encode(injected)==encode(pristine)
        responses=[]
        for obj in (pristine,injected):
            (work/"evidence.json").write_bytes(encode(obj))
            responses.append(cli(src/"stock.py","score",work/"evidence.json",work/"contract.json"))
        assert responses[0]==responses[1]
        results.append({"control":left,"alternative":right,"frozen_arm_evidence_equal":ea==eb,
                        "score_input_byte_identical":encode(injected)==encode(pristine),
                        "phase_blob_sha256":hashes,"two_normal_scorer_verdicts":[r["verdict"] for r in responses],
                        "scope":"Only the control producer executed. All receipts are its original CPU receipts. Alternative supplied only already-identical frozen phase bytes; no native observation."})
    print(json.dumps(results,indent=2))


if __name__=="__main__":
    main(*map(Path,sys.argv[1:]))
