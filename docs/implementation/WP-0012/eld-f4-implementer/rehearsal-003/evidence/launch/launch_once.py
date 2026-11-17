from pathlib import Path
from datetime import datetime, timezone
import json, os, subprocess, sys
root=Path.cwd()
scratch=root/".local/wp0012-author003-20261117T164734Z"
helper=root/"docs/implementation/WP-0012/eld-f4-implementer/correction-006/helpers/run_wp0012_rehearsal.py"
sys.path.insert(0,str(helper.parent))
import run_wp0012_rehearsal as driver
def utc(): return datetime.now(timezone.utc).isoformat()
def save(): (scratch/"launcher-receipt.json").write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
head=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
assert head=="f1b8306ef62bf1c82a9106509ce31988e94b1dab"
assert not subprocess.check_output(["git","status","--porcelain","--untracked-files=all"],text=True).strip()
receipt={"schema":"eledgercare.wp0012.author003-launch/1","started_utc":utc(),"source_head":head,"lease_id":"WP-0012-author-003-20261117T164734Z","release_commit":"0815c028e706751deea13781cb0a08f8d1afc8aa","wrapper_identity":driver.get_win32_process_identity(os.getpid()),"python_version":sys.version,"cwd":str(root),"invocations":[]}
save()
for mode in ("--validate-release","--execute-live"):
 tag="validate-release" if mode=="--validate-release" else "execute-live"
 command=[sys.executable,"-B",str(helper),mode,"--release-commit",receipt["release_commit"],"--release-path","docs/coordination/WP-0012/releases/author-003.json"]
 item={"mode":mode,"command":command,"started_utc":utc(),"stdout":tag+".stdout.log","stderr":tag+".stderr.log"}
 receipt["invocations"].append(item)
 save()
 with (scratch/item["stdout"]).open("wb") as out,(scratch/item["stderr"]).open("wb") as err:
  proc=subprocess.Popen(command,cwd=str(root),env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1"},stdout=out,stderr=err)
  item["identity"]=driver.get_win32_process_identity(proc.pid)
  save()
  print(json.dumps({"event":"START", "mode":mode,"identity":item["identity"],"utc":item["started_utc"]}),flush=True)
  item["exit_code"]=proc.wait()
 item["ended_utc"]=utc()
 save()
 print(json.dumps({"event":"EXIT","mode":mode,"exit_code":item["exit_code"],"utc":item["ended_utc"]}),flush=True)
 if item["exit_code"]!=0:
  receipt["ended_utc"]=utc()
  receipt["wrapper_exit_code"]=item["exit_code"]
  save()
  sys.exit(item["exit_code"])
receipt["ended_utc"]=utc()
receipt["wrapper_exit_code"]=0
save()
