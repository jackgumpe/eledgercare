"""C0 parent capture must stop at the first observed child scope, including across spans."""
import json
import subprocess
import sys


def test(revision):
    spec=f"{revision}:docs/fixtures/WP-0024/score.py"
    source=subprocess.check_output(["git","show",spec])
    module={}
    exec(compile(source,spec,"exec"),module)
    expected={"owner":"A","unit":"U1","schema":["Item","Amount","Ref"]}
    def evaluate(literals):
        spans=[]
        for i,(literal,cells) in enumerate(literals):
            spans.append({"index":i,"page":1,"kind":"row" if cells else "block","cells":cells,
                          "text":literal,"char_range":[i*100,i*100+len(literal)]})
        result=module["captured"]({"spans":spans},expected)
        return {"passed":result["pass_c0"],"misses":result["miss_reasons"],"visible":result["visible"]}
    directory=("Owners: A / B",[])
    owner=("Ledger: A",[])
    unit=("Unit: U1",[])
    schema=("Item Amount Ref",expected["schema"])
    child=("Supporting schedule",[])
    data={"active_before_child":evaluate([directory,owner,unit,schema,child]),
          "all_declarations_only_inside_child":evaluate([directory,child,owner,unit,schema]),
          "only_schema_inside_child":evaluate([directory,owner,unit,child,schema])}
    expected_outputs=[True,False,False]
    observed=[r["passed"] for r in data.values()]
    return {"source":revision,"cases":data,"expected":expected_outputs,"observed":observed,"passed":observed==expected_outputs}


if __name__=="__main__":
    assert sys.flags.isolated and sys.dont_write_bytecode
    print(json.dumps(test(sys.argv[1]),indent=2))

