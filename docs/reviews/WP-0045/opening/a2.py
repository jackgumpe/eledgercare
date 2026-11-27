"""Two post-opening counterexamples. Separate from the blind matrix."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
from common import BASE, HOME, save
from clauses import scores

src=HOME.parent/"eld-fixture-claude"/"oracle"/"oracle.py"
spec=importlib.util.spec_from_file_location("frozen_oracle",src)
oracle=importlib.util.module_from_spec(spec)
spec.loader.exec_module(oracle)
rows={}
for label,final,reference,oracle_conflicts in [
    ("later_changes_wrong_predecessor","ff800000",[["repeat",0],["page",0]],[["repeat",0]]),
    ("later_preserves_wrong_predecessor","00000000",[["repeat",0]],[["repeat",0],["page",0]])]:
    request=dict(clause="A2",raw=["00000000","3f800000"],repeat=["00000000","3f800000"],
                 page=[final,"3f800000"],repeat_block=[0],page_block=[])
    author=HOME/"opened"/"edition"/"docs"/"editions"/"WP-0045"/"clauses.py"
    a=json.loads(subprocess.check_output([str(BASE),"-I","-B",str(author)],input=json.dumps(request).encode()))
    b=scores(request)
    assert a==b and a["conflicts"]==reference
    old=oracle.a2(request)
    assert old["conflicts"]==oracle_conflicts
    rows[label]=dict(input=request,amended=a,sealed_oracle=old)
save(HERE/"opening"/"a2-boundaries.json",rows)
print("two complementary finite boundaries")
