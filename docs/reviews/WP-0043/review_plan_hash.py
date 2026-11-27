from pathlib import Path
import hashlib,json,subprocess,sys
from itertools import zip_longest
src=Path(sys.argv[1])
sys.path.insert(0,str(src))
import native
f=lambda b:hashlib.sha256(b).hexdigest()
relrev="e95b754bd4dedd44da6f7ab8366843907e676f7c"
release=json.loads(subprocess.check_output(["git","show",relrev+":docs/coordination/WP-0043/device-release.json"]))
cli=subprocess.check_output([sys.executable,"-B","-u",str(src/"stock.py"),"plan"],cwd=src)
p=native.plan()
mem=native.bytes_json(p)
printed=json.loads(cli)
rebuilt=native.bytes_json(printed)
original_keys=next(v for v in p["cuts"].values() if len(v)>1 and list(sorted(map(str,v)))!=list(map(str,sorted(v))))
canonical=native.bytes_json(release["plan"])
print(json.dumps(dict(release_revision=relrev,release_plan_sha256=release["plan_sha256"],cli_stdout_sha256=f(cli),in_memory_plan_sha256=f(mem),cli_roundtrip_plan_sha256=f(rebuilt),published_plan_canonical_sha256=f(canonical),byte_lengths=[len(mem),len(rebuilt),len(canonical)],first_differing_byte=next(i for i,(a,b) in enumerate(zip_longest(mem,rebuilt)) if a!=b),object_values_equal=(json.loads(mem)==release["plan"]==printed),offsets_numeric_order=sorted(original_keys),offsets_json_order=sorted(map(str,original_keys)),source_revision=subprocess.check_output(["git","-C",str(src),"rev-parse","HEAD"],text=True).strip(),no_torch_import="torch" not in sys.modules,source_output_exists=native.OUT.exists()),indent=2))
assert json.loads(mem)==release["plan"]==printed and rebuilt==canonical and mem!=rebuilt
