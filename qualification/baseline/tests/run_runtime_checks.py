"""Freeze-first CPU capture for /009; outputs/scratch stay in the owned worktree."""
import datetime,hashlib,json,os,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parents[1];ROOT=HERE.parents[1]
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def main():
    head=git('rev-parse','HEAD').decode().strip()
    if git('status','--porcelain').strip():raise RuntimeError('Freeze source before decisive checks')
    out=ROOT/'docs/evidence/WP-0007/eld-rd-astra/runtime-correction'/head[:8];out.mkdir(parents=True,exist_ok=False)
    scratch=ROOT/'.scratch/runtime-correction'/head[:8];scratch.mkdir(parents=True,exist_ok=False)
    env=dict(os.environ)
    for k in ('TEMP','TMP','TMPDIR'):env[k]=str(scratch)
    results=[]
    for name in ['test_baseline.py','test_runtime_correction.py']:
        cmd=[sys.executable,'-I','-B',str(HERE/'tests'/name),'-v']
        cp=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,timeout=120)
        (out/(name+'.stdout.txt')).write_bytes(cp.stdout);(out/(name+'.stderr.txt')).write_bytes(cp.stderr)
        results.append({'argv':cmd,'exit_code':cp.returncode})
    protected=['qualification/baseline/'+x for x in ['native.py','score.py','typed_values.py','corpus.py','mapping.json','protocol.json','winjob.py']]+['qualification/q0','evaluation','src','tests','web','workers','docs/evidence/WP-0007/eld-rd-astra/runtime-dev','docs/agent-reports/eld-rd-astra']
    identities=[]
    for path in protected:
        old=git('rev-parse','69ee8796b9b86e7c0090ae91d9efc27999088a7a:'+path).decode().strip();new=git('rev-parse',head+':'+path).decode().strip()
        identities.append({'path':path,'base_object':old,'candidate_object':new,'identical':old==new})
    inventory=[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(out.iterdir())]
    record={'candidate':head,'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python':sys.version,'commands':results,'protected':identities,'inventory':inventory,'scratch':str(scratch),'passed':all(x['exit_code']==0 for x in results) and all(x['identical'] for x in identities),'limits':['author CPU checks, not independent acceptance','no external runtime/model/GPU or heldout content access','actual heartbeat overlap is accelerated, not original failure attribution']}
    (out/'checks.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({'candidate':head,'passed':record['passed'],'evidence':str(out)}));return 0 if record['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
