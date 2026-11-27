"""Score a partial, reversed append journal using only reviewer-owned synthetic scratch."""
from pathlib import Path
import json
import sys


def main(src, work):
    sys.path.insert(0,str(src))
    import native_score
    from capture import code_identity
    from bindings import resolve
    native_score.OUT=work
    observed=work/"observed"
    observed.mkdir(parents=True)
    table=resolve(native_score.MODEL)
    gen,offset=next((c,o) for c,sites in table.items() for o,tag in sites.items() if tag=="D")
    archive,_=native_score.archived("F07.warm1")
    with (observed/"observations.jsonl").open("x",encoding="utf8") as dest:
        for seq,index in enumerate([1,0],1):
            data={"index":index,"pos":827+index,"id":archive["ids"][index]}
            item={"row":None,"tag":"append","journal_seq":seq,"frame":11,"identity":code_identity(gen),
                  "instruction":offset,"data":data}
            dest.write(json.dumps(item)+"\n")
    result=native_score.score_native()
    print(json.dumps({"test":"two internally ordered file receipts name reversed native appended indices",
        "serialized_indices":[1,0],"serialized_sequences":[1,2],"verdict":result["verdict"],
        "conflict_keys":result["conflict_keys"],"missing_keys":result["missing_keys"],
        "public_verdict":result["public_verdict"],"complete_rows":result["complete_rows"]},indent=2))


if __name__=="__main__":
    main(Path(sys.argv[1]),Path(sys.argv[2]))
