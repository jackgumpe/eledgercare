"""Bounded CPU counterexample: invalid-image Git name in prior owned PATH slot."""
import datetime,json,os,subprocess,sys,hashlib,traceback,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[6]
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE),str(ROOT),str(ROOT/'qualification/q0/harness')]
import probe_v2  # Reuse frozen import denial and explicitly owned PID identity.
from q0harness.environment import build_child_env,resolve_host_git
from qualification.mapping_v2.process_identity import process_identity
def write(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2);f.write('\n')
def child(config_path):
    config=json.loads(Path(config_path).read_bytes());root=Path(config['root']);run=Path(config['run'])
    receipt={'schema':'eld-wp13-git-shadow-counterexample/1','identity':process_identity(os.getpid()),
             'source':'b60624ac7a0ae23540ab019b63d7a7e904fb1c36','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    assert sys.stdin.readline().strip()=='RUN'
    from qualification.mapping_v2.runtime import enable_pinned_git_lookup
    from qualification.mapping_v2.common import verify_frozen_mappers
    env=enable_pinned_git_lookup(dict(os.environ),root=root,owner='reviewer',run_dir=run)
    receipt['candidate_environment_audits_returned']=True
    os.environ.clear();os.environ.update(env)
    receipt['explicit_git']=env['Q0_GIT_EXECUTABLE'];receipt['resolved_bare_git']=shutil.which('git');receipt['path']=env['PATH']
    explicit=subprocess.run([env['Q0_GIT_EXECUTABLE'],'--version'],cwd=ROOT,capture_output=True,timeout=10)
    receipt['explicit_git_exit']=explicit.returncode;receipt['explicit_git_stdout']=explicit.stdout.decode()
    try:
        verify_frozen_mappers()
        receipt['pin_outcome']='unexpectedly_completed'
    except BaseException as exc:
        traceback.print_exc()
        receipt['pin_outcome']='exception';receipt['exception']={'type':type(exc).__name__,'message':str(exc),'winerror':getattr(exc,'winerror',None)}
    receipt['invalid_image_fixture_sha256']=hashlib.sha256(Path(config['shadow']).read_bytes()).hexdigest()
    receipt['blocked_import_attempts']=probe_v2.blocked_imports
    receipt['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    write(run/'child-receipt.json',receipt)
    return 1
def parent():
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT).strip()
    root=ROOT/'.scratch/wp0013-reviewer-011/shadow-attempt-1';run=root/'runs/reviewer/probe';run.mkdir(parents=True,exist_ok=False)
    p=json.loads((ROOT/'qualification/mapping_v2/runtime_protocol.json').read_bytes());base=Path(p['read_only_q0_root'])
    env=build_child_env(dict(os.environ),root=root,owner='reviewer',run_dir=run,gpu_uuid=p['gpu']['uuid'],git_executable=resolve_host_git())
    env['VIRTUAL_ENV']=str(base/'venv');env['PATH']=str(base/'venv/Scripts')+os.pathsep+env['PATH']
    for key,suffix in [('HF_HOME','hf-home'),('HF_HUB_CACHE','hf-home/hub'),('HUGGINGFACE_HUB_CACHE','hf-home/hub'),('TRANSFORMERS_CACHE','hf-home/transformers')]:env[key]=str(run/suffix)
    shadow=root/'venv/Scripts/git.exe';shadow.parent.mkdir(parents=True);shadow.write_bytes(b'CPU invalid-image fixture; no executable code; never valid PE')
    config={'root':str(root),'run':str(run),'shadow':str(shadow)};write(run/'config.json',config)
    cmd=[str(base/'venv/Scripts/python.exe'),'-I','-B',str(Path(__file__).resolve()),'--child',str(run/'config.json')]
    start=datetime.datetime.now(datetime.timezone.utc).isoformat()
    with (run/'stdout.txt').open('xb') as out,(run/'stderr.txt').open('xb') as err:
        proc=subprocess.Popen(cmd,cwd=ROOT,env=env,stdin=subprocess.PIPE,stdout=out,stderr=err);identity=process_identity(proc.pid)
        proc.communicate(b'RUN\n',timeout=30)
    record=json.loads((run/'child-receipt.json').read_bytes())
    assert proc.returncode==1 and record['candidate_environment_audits_returned']
    assert Path(record['resolved_bare_git']).resolve()==shadow.resolve()
    assert record['explicit_git_exit']==0 and record['exception']['winerror']==193
    assert not record['blocked_import_attempts']
    receipt={'result':'REPRODUCED_SHADOW_RESOLUTION','helper_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip(),
        'command':cmd,'start_utc':start,'end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'launcher_identity':identity,'child_exit':proc.returncode,'evidence':str(run),
        'limit':'Invalid PE bytes were never executed. Actual Windows bare-Git loader selection fails193 at mutable earlier PATH file while explicit Git succeeds. No model/live observer or source edit.'}
    write(root/'execution.json',receipt);print(json.dumps(receipt))
if __name__=='__main__':
    if len(sys.argv)>1:raise SystemExit(child(sys.argv[2]))
    parent()
