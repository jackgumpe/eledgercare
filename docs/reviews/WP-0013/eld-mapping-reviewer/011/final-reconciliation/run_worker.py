"""Same four fixed scenarios through actual Windows owned-job worker entry."""
import copy,datetime,hashlib,json,os,subprocess,sys,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[6];HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT),str(ROOT/'qualification/q0/harness'),str(ROOT/'qualification/baseline')]
from q0harness.environment import build_child_env,resolve_host_git
from qualification.mapping_v2 import runtime,release
from qualification.mapping_v2.process_identity import process_identity
import winjob
SOURCE='ae790497f3fdd10573e8179757416bc2d1736250';TREE='8fd68c96bb18ca0177f227ad9a82505090d997b0'
AUTHORITY='61f37aa6bd0e67918f2a1225be8028bf8031ce29'
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def sha(data):return hashlib.sha256(data).hexdigest()
def write(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2);f.write('\n')
def main():
    assert not git('status','--porcelain').strip();head=git('rev-parse','HEAD').decode().strip()
    assert git('rev-parse','HEAD:qualification/mapping_v2').decode().strip()==TREE
    root=ROOT/'.scratch/wp0013-reviewer-011-final/worker-attempt-1';root.mkdir(parents=True,exist_ok=False)
    p=runtime.protocol();base=Path(p['read_only_q0_root']);python=base/'venv/Scripts/python.exe'
    original=json.loads(git('show',AUTHORITY+':docs/coordination/WP-0013/author-failed-after/original-plan.json'))['release']
    rows=[]
    for case in ('clean','earlier_path','current_directory','path_and_current_directory'):
        subroot=root/case;run=subroot/'runs/reviewer/probe';run.mkdir(parents=True,exist_ok=False)
        env=build_child_env(dict(os.environ),root=subroot,owner='reviewer',run_dir=run,gpu_uuid=p['gpu']['uuid'],git_executable=resolve_host_git())
        env['VIRTUAL_ENV']=str(base/'venv');env['PATH']=str(base/'venv/Scripts')+os.pathsep+env['PATH']
        for key,suffix in [('HF_HOME','hf-home'),('HF_HUB_CACHE','hf-home/hub'),('HUGGINGFACE_HUB_CACHE','hf-home/hub'),('TRANSFORMERS_CACHE','hf-home/transformers')]:env[key]=str(run/suffix)
        runtime.enable_pinned_git_lookup(env,root=subroot,owner='reviewer',run_dir=run)
        # Fixtures arrive after the parent snapshot; the actual worker must recheck.
        cwd=ROOT;fixtures=[]
        if case in ('earlier_path','path_and_current_directory'):fixtures.append(subroot/'venv/Scripts/git.exe')
        if case in ('current_directory','path_and_current_directory'):
            cwd=run/'child-current-directory';cwd.mkdir();fixtures.append(cwd/'git.exe')
        for path in fixtures:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'CPU invalid image after parent snapshot: '+case.encode())
        fixture=copy.deepcopy(original)
        fixture.update(owner='reviewer',source_commit=SOURCE,source_tree=TREE,executing_head=head,
            protocol_sha256=sha((ROOT/'qualification/mapping_v2/runtime_protocol.json').read_bytes()),
            runtime_root=p['runtime_roots']['reviewer'],schedule=release.schedule(p,'reviewer'))
        fixture['source_review'].update(path=p['source_review_path'],reviewed_source_commit=SOURCE)
        fixture['lease'].update(owner='reviewer',id='CPU-ONLY-WORKER-BOUNDARY-NO-RUNTIME-AUTHORITY')
        job='Local\\eLedgerCare-WP13-Reviewer-CPU-'+uuid.uuid4().hex;handle=winjob.create(job)
        config={'case':case,'source':SOURCE,'root':str(subroot),'run':str(run),'job':job,'authority':AUTHORITY,
            'release_path':'docs/coordination/WP-0013/releases/reviewer.json','fixture':fixture,
            'test_interceptions':['worker storage-root data only','initial release object only','stop after actual frozen pins']}
        write(run/'config.json',config)
        cmd=[str(python),'-I','-B',str(HERE/'worker_probe.py'),str(run/'config.json')]
        start=datetime.datetime.now(datetime.timezone.utc).isoformat();proc=None
        try:
            with (run/'stdout.txt').open('xb') as out,(run/'stderr.txt').open('xb') as err:
                proc=subprocess.Popen(cmd,cwd=cwd,env=env,stdin=subprocess.PIPE,stdout=out,stderr=err);identity=process_identity(proc.pid)
                proc.communicate(b'RUN\n',timeout=60)
        finally:
            winjob.close(handle)
            if proc is not None and proc.poll() is None:proc.wait(timeout=10)
        child=json.loads((run/'child-receipt.json').read_bytes())
        row={'case':case,'helper_head':head,'source':SOURCE,'command':cmd,'cwd':str(cwd),'job_name':job,
            'job_handle_closed':True,'launcher_identity':identity,'child_exit':proc.returncode,
            'start_utc':start,'end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'control_passed':child['control_passed'],'read_release_calls':child['read_release_calls'],
            'stdout_sha256':sha((run/'stdout.txt').read_bytes()),'stderr_sha256':sha((run/'stderr.txt').read_bytes())}
        write(run/'execution.json',row);rows.append(row)
    result={'result':'PASS' if all(r['control_passed'] and r['child_exit']==1 for r in rows) else 'FAIL',
        'source':SOURCE,'source_tree':TREE,'cases':rows,'model_calls':0,'actual_runtime_roots_created':0,
        'limit':'Real owned Windows job/worker-entry gates; CPU storage/root and release fixture overlays; stop after genuine pins; no model continuation or runtime authority'}
    write(root/'summary.json',result);print(json.dumps(result));assert result['result']=='PASS'
if __name__=='__main__':main()
