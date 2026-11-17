"""Freeze before source-bound execution; actual PATH/CWD lookup, never a worker."""
import argparse,datetime,hashlib,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[6]
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT),str(ROOT/'qualification/q0/harness')]
from q0harness.environment import build_child_env,resolve_host_git,audit_child_env
from qualification.mapping_v2.process_identity import process_identity
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def sha(data):return hashlib.sha256(data).hexdigest()
def write(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2);f.write('\n')
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);ap.add_argument('--tree',required=True);ap.add_argument('--attempt',required=True);args=ap.parse_args()
    assert len(args.source)==40 and len(args.tree)==40 and args.attempt=='selection-attempt-1'
    assert not git('status','--porcelain').strip()
    assert git('rev-parse',args.source+':qualification/mapping_v2').decode().strip()==args.tree
    assert git('rev-parse','HEAD:qualification/mapping_v2').decode().strip()==args.tree
    assert git('rev-parse','HEAD:evaluation/mapping_v2').decode().strip()=='af22f632c2b69531f61866ca467c6f04f386df7e'
    root=ROOT/'.scratch/wp0013-reviewer-011-final'/args.attempt;root.mkdir(parents=True,exist_ok=False)
    p=json.loads((ROOT/'qualification/mapping_v2/runtime_protocol.json').read_bytes());base=Path(p['read_only_q0_root'])
    python=base/'venv/Scripts/python.exe';git_exe=resolve_host_git();head=git('rev-parse','HEAD').decode().strip()
    results=[]
    # Separate subroots keep a prior PATH shadow out of later independent cases.
    for case in ('clean','earlier_path','current_directory','path_and_current_directory'):
        subroot=root/case;run=subroot/'runs/reviewer/probe';run.mkdir(parents=True,exist_ok=False)
        env=build_child_env(dict(os.environ),root=subroot,owner='reviewer',run_dir=run,gpu_uuid=p['gpu']['uuid'],git_executable=git_exe)
        env['VIRTUAL_ENV']=str(base/'venv');env['PATH']=str(base/'venv/Scripts')+os.pathsep+env['PATH']
        for key,suffix in [('HF_HOME','hf-home'),('HF_HUB_CACHE','hf-home/hub'),('HUGGINGFACE_HUB_CACHE','hf-home/hub'),('TRANSFORMERS_CACHE','hf-home/transformers')]:env[key]=str(run/suffix)
        audit_child_env(env,root=subroot,owner='reviewer',run_dir=run)
        cwd=ROOT;fixtures=[]
        if case in ('earlier_path','path_and_current_directory'):
            fixtures.append(subroot/'venv/Scripts/git.exe')
        if case in ('current_directory','path_and_current_directory'):
            cwd=run/'child-current-directory';cwd.mkdir();fixtures.append(cwd/'git.exe')
        for fixture in fixtures:
            fixture.parent.mkdir(parents=True,exist_ok=True)
            fixture.write_bytes(b'CPU INVALID IMAGE: no executable code; '+case.encode())
        config={'case':case,'root':str(subroot),'run':str(run),'source':args.source,
            'fixtures':[{'path':str(x),'bytes':x.stat().st_size,'sha256':sha(x.read_bytes())} for x in fixtures]}
        write(run/'config.json',config)
        cmd=[str(python),'-I','-B',str(HERE/'selection_probe.py'),str(run/'config.json')]
        start=datetime.datetime.now(datetime.timezone.utc).isoformat()
        with (run/'stdout.txt').open('xb') as out,(run/'stderr.txt').open('xb') as err:
            proc=subprocess.Popen(cmd,cwd=cwd,env=env,stdin=subprocess.PIPE,stdout=out,stderr=err);identity=process_identity(proc.pid)
            proc.communicate(b'RUN\n',timeout=60)
        child=json.loads((run/'child-receipt.json').read_bytes())
        row={'case':case,'command':cmd,'cwd':str(cwd),'helper_head':head,'source':args.source,'source_tree':args.tree,
            'launcher_identity':identity,'start_utc':start,'end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'exit_code':proc.returncode,'control_passed':child['control_passed'],'gate_returned':child['gate_returned'],
            'pins_completed':child['pins_completed'],'stdout_sha256':sha((run/'stdout.txt').read_bytes()),
            'stderr_sha256':sha((run/'stderr.txt').read_bytes())}
        write(run/'execution.json',row);results.append(row)
    report={'result':'PASS' if all(x['control_passed'] for x in results) else 'FAIL','source':args.source,'source_tree':args.tree,
        'helper_head':head,'cases':results,'actual_existing_executables':[{'path':str(x),'sha256':sha(x.read_bytes())} for x in (python,Path(git_exe))],
        'limits':'Actual Windows subprocess lookup with invalid-image fixtures only. Safe gate rejection or real pin completion is required; loader errors after accepted gate fail. No model, observer, worker or renderer.'}
    write(root/'summary.json',report);print(json.dumps(report));assert report['result']=='PASS'
if __name__=='__main__':main()
