"""Exact released execute/score wrapper. No model or observer work during import."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import traceback

ROOT=Path(__file__).resolve().parents[5];sys.path.insert(0,str(ROOT))
HERE=Path(__file__).resolve().parent
SCRATCH=ROOT/'.scratch/wp0011-reviewer-execution'
SOURCE='253519e07e7d45cf1f5ecb3e03053582f7f7d4cc'
TREE='6bdab544c9fe26cbf093cc765212db2a2e7a97a5'
PROTOCOL='03b13a41a0047c827af32e71209933700457a5dfd6d38ec106daed82ef5b9000'
RELEASE_PATH='docs/coordination/WP-0011/releases/reviewer.json'
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(data):return hashlib.sha256(data).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2);f.write('\n')
def load(path):return json.loads(path.read_bytes())
def identity(path):
    data=path.read_bytes();return {'path':str(path),'bytes':len(data),'sha256':sha(data)}
def inside(path,parent):
    path=Path(path).resolve();path.relative_to(parent.resolve());return path

def invoke(command,attempt,kind,metadata,on_started=None):
    """One subprocess, explicit binary stdout/stderr including genuine empty files."""
    launch={**metadata,'kind':kind,'command':command,'wrapper_pid':os.getpid(),'python_executable':sys.executable,'started_utc':now()}
    write(attempt/(kind+'-launch.json'),launch)
    proc=None;code=None;error=None
    try:
        with (attempt/(kind+'.stdout.txt')).open('xb') as stdout,(attempt/(kind+'.stderr.txt')).open('xb') as stderr:
            proc=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,
                                  creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            started={**launch,'supervisor_pid':proc.pid}
            write(attempt/(kind+'-started.json'),started)
            print(json.dumps({'event':'STARTED','kind':kind,'wrapper_pid':os.getpid(),'supervisor_pid':proc.pid,'attempt':str(attempt),'started_utc':launch['started_utc']}),flush=True)
            if on_started:on_started(proc)
            code=proc.wait()
    except BaseException:
        error=traceback.format_exc()
    completion={**launch,'finished_utc':now(),'supervisor_pid':None if proc is None else proc.pid,'supervisor_exit_code':code,
                'wrapper_error':error,'observed_exit':code is not None,
                'stdout':identity(attempt/(kind+'.stdout.txt')) if (attempt/(kind+'.stdout.txt')).exists() else None,
                'stderr':identity(attempt/(kind+'.stderr.txt')) if (attempt/(kind+'.stderr.txt')).exists() else None,
                'limit':'Actual subprocess wait result, distinct from runtime worker outcome. No process-absence/GPU-ownership claim.'}
    write(attempt/(kind+'-completion.json'),completion)
    print(json.dumps({'event':'COMPLETED','kind':kind,'supervisor_exit_code':code,'wrapper_error':error,'attempt':str(attempt)}),flush=True)
    return completion

def checked_release(authority,execution):
    if not re.fullmatch('[0-9a-f]{40}',authority):raise ValueError('Full exact runtime authority required')
    from qualification.coverage_v1.release import read_release
    r=read_release(authority,RELEASE_PATH,'reviewer',execution=execution)
    if r['source_commit']!=SOURCE or r['source_tree']!=TREE or r['protocol_sha256']!=PROTOCOL:raise ValueError('Accepted source binding changed')
    return r

def main():
    p=argparse.ArgumentParser();p.add_argument('kind',choices=('execute','score'));p.add_argument('--authority',required=True)
    p.add_argument('--attempt',required=True);p.add_argument('--run');a=p.parse_args()
    r=checked_release(a.authority,a.kind=='execute')
    attempt=inside(a.attempt,SCRATCH);head=git('rev-parse','HEAD').decode().strip()
    metadata={'schema':'eld-reviewer-execution-wrapper/1','runtime_authority':a.authority,'release_path':RELEASE_PATH,'owner':'reviewer',
              'executing_head':head,'source_commit':SOURCE,'source_tree':TREE,'protocol_sha256':PROTOCOL,'lease_id':r['lease']['id'],
              'helper_sha256':sha(Path(__file__).read_bytes()),'initial_worktree_clean':not git('status','--porcelain').strip()}
    base=[sys.executable,'-I','-B',str(ROOT/'qualification/coverage_v1/cli.py')]
    binding=['--authority',a.authority,'--release-path',RELEASE_PATH,'--owner','reviewer']
    if a.kind=='execute':
        if attempt.exists():raise FileExistsError('One attempt only; no overwrite/retry')
        # Exclusive per-lease marker prevents a second attempt directory from bypassing no retry.
        marker=SCRATCH/'lease-markers'/(sha(r['lease']['id'].encode())+'.json')
        write(marker,metadata);attempt.mkdir(parents=True,exist_ok=False)
        completion=invoke(base+['execute']+binding,attempt,'execute',metadata)
    else:
        launched=load(attempt/'execute-launch.json');completed=load(attempt/'execute-completion.json')
        if launched['executing_head']!=head or launched['runtime_authority']!=a.authority or not completed['observed_exit']:
            raise ValueError('Execute receipt/head/authority incomplete; no score while execution is unobserved')
        run=inside(a.run,Path(r['runtime_root'])/'runs/reviewer')
        if run.parent!=(Path(r['runtime_root'])/'runs/reviewer').resolve():raise ValueError('Exact direct owned run required')
        metadata['run']=str(run)
        command=base+['score-run']+binding+['--run',str(run),'--output',str(attempt/'scores.json')]
        completion=invoke(command,attempt,'score',metadata)
    return completion['supervisor_exit_code'] if completion['supervisor_exit_code'] is not None else 1
if __name__=='__main__':raise SystemExit(main())
