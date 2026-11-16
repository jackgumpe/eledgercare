"""Finite baseline runtime; Q0 model/observer primitives reused read-only, no Q0 session edits."""
from __future__ import annotations
import datetime,json,os,shutil,subprocess,sys,time,traceback,uuid
from pathlib import Path
from corpus import ROOT,pdf_for,sha,load_json
from release import HERE,protocol,read_release,schedule,git

def write(path,obj):
    with Path(path).open('x',encoding='utf-8',newline='\n') as f:json.dump(obj,f,indent=2,ensure_ascii=False);f.write('\n')
def q0_imports():sys.path.insert(0,str(ROOT/'qualification/q0/harness'))
def directory_size(root):
    total=0
    for p in Path(root).rglob('*'):
        if p.is_symlink() or (p.stat().st_file_attributes & 0x400):raise RuntimeError('Reparse path in owned runtime root')
        if p.is_file():total+=p.stat().st_size
    return total

def guard_reason(*,elapsed,phase_elapsed,progress_elapsed,stall_monitored,phase_limit,log_bytes,root_bytes,free_bytes,p):
    if elapsed>p['guards']['timeouts_s']['session']:return 'SESSION_TIMEOUT'
    if phase_elapsed>phase_limit:return 'PHASE_TIMEOUT'
    if stall_monitored and progress_elapsed>p['guards']['stall_s']:return 'NO_FORWARD_PROGRESS'
    if log_bytes>p['guards']['max_log_bytes']:return 'LOG_LIMIT'
    if root_bytes>p['storage_cap_bytes']:return 'STORAGE_CAP'
    if free_bytes<p['free_floor_bytes']:return 'FREE_SPACE_FLOOR'
    return None

def execute(authority,release_path,split,owner):
    r=read_release(authority,release_path,split,owner);p=protocol();q0_imports()
    from q0harness.environment import build_child_env,resolve_host_git,audit_child_env
    from q0harness.supervisor import run_observers
    import winjob
    root=Path(r['runtime_root']);base=Path(p['read_only_q0_root']);python=base/'venv/Scripts/python.exe'
    if not python.is_file():raise RuntimeError('Pinned existing venv missing')
    # Reject existing reparse ancestors and capacity before creating any runtime state.
    for parent in (root,*root.parents):
        if parent.exists() and (parent.is_symlink() or parent.stat().st_file_attributes & 0x400):raise RuntimeError('Reparse runtime ancestor')
    free=shutil.disk_usage(root.anchor).free
    if free<p['free_floor_bytes'] or (root.exists() and directory_size(root)>p['storage_cap_bytes']):raise RuntimeError('Storage gate')
    run=root/'runs'/owner/(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8])
    run.mkdir(parents=True,exist_ok=False)
    env=build_child_env(dict(os.environ),root=root,owner=owner,run_dir=run,gpu_uuid=r['gpu_uuid'],git_executable=resolve_host_git())
    env['VIRTUAL_ENV']=str(base/'venv');env['PATH']=str(base/'venv/Scripts')+os.pathsep+env['PATH']
    # HF caches must be per-run as well as task-local; never write reused Q0 root.
    for key,suffix in [('HF_HOME','hf-home'),('HF_HUB_CACHE','hf-home/hub'),('HUGGINGFACE_HUB_CACHE','hf-home/hub'),('TRANSFORMERS_CACHE','hf-home/transformers')]:env[key]=str(run/suffix)
    for key in ['TEMP','TMP','TMPDIR','HF_HOME','HF_MODULES_CACHE','CUDA_CACHE_PATH','TORCH_HOME','TORCHINDUCTOR_CACHE_DIR','USERPROFILE']:
        Path(env[key]).mkdir(parents=True,exist_ok=True)
    audit_child_env(env,root=root,owner=owner,run_dir=run)
    plan=schedule(p,split,r['sentinels'] if owner=='reviewer' else None)
    write(run/'plan.json',{'release':r,'authority_commit':authority,'release_path':release_path,'executing_head':git('rev-parse','HEAD').decode().strip(),'calls':plan})
    jobname='Local\\eLedgerCare-B0-'+uuid.uuid4().hex;job=winjob.create(jobname)
    cmd=[str(python),'-I','-B',str(HERE/'baseline.py'),'worker','--authority',authority,'--release-path',release_path,'--split',split,'--owner',owner,'--run-dir',str(run),'--job',jobname]
    observed=run_observers(p['gpu']['observer']['commands'],run,'pre');proc=None;failure=None;start=time.monotonic();last_phase=None;phase_start=start;progress_start=start;last_progress=None;next_obs=start+60
    try:
        with (run/'stdout.txt').open('xb') as stdout,(run/'stderr.txt').open('xb') as stderr:
            proc=subprocess.Popen(cmd,cwd=ROOT,env=env,stdout=stdout,stderr=stderr,stdin=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            while proc.poll() is None:
                now=time.monotonic()
                try:hb=load_json(run/'heartbeat.json')
                except (OSError,ValueError):hb={}
                if hb.get('phase')!=last_phase:last_phase=hb.get('phase');phase_start=now;progress_start=now;last_progress=hb.get('progress')
                elif hb.get('progress')!=last_progress:last_progress=hb.get('progress');progress_start=now
                failure=guard_reason(elapsed=now-start,phase_elapsed=now-phase_start,progress_elapsed=now-progress_start,
                  stall_monitored=hb.get('stall_monitored',False),phase_limit=hb.get('phase_timeout_s') or 1800,
                  log_bytes=(run/'stdout.txt').stat().st_size+(run/'stderr.txt').stat().st_size,root_bytes=directory_size(root),free_bytes=shutil.disk_usage(root).free,p=p)
                if failure:break
                if now>=next_obs:observed+=run_observers(p['gpu']['observer']['commands'],run,f'during-{int(now-start)}');next_obs=now+60
                time.sleep(1)
            if failure:winjob.close(job);job=None;proc.kill()
            proc.wait(timeout=60)
    except BaseException as e:
        failure=failure or 'SUPERVISOR_ERROR:'+repr(e)
    finally:
        if job is not None:winjob.close(job)
        if proc is not None and proc.poll() is None:proc.kill();proc.wait(timeout=60)
    observed+=run_observers(p['gpu']['observer']['commands'],run,'post')
    records=[]
    worker_outcome=load_json(run/'evidence/worker-outcome.json') if (run/'evidence/worker-outcome.json').is_file() else {}
    for call in plan:
        name=call['fixture_id']+'.'+call['kind'];path=run/'evidence'/f'{name}.observation.json'
        record=load_json(path) if path.is_file() else None
        state='completed' if record and not record.get('flags') and not record.get('error') else 'failed' if record else 'not_run_after_failure'
        if worker_outcome.get('failure') and worker_outcome.get('active_call')==name:state='failed'
        if failure and last_phase in ('call:'+name,'render:'+call['fixture_id']):state='failed'
        records.append({**call,'status':state,'observation':str(path.relative_to(run)) if record else None})
    if proc is None or proc.returncode!=0:failure=failure or 'CHILD_EXIT_FAILURE'
    result={'schema':'eld-baseline-run/1','run':str(run),'executing_head':git('rev-parse','HEAD').decode().strip(),'release':r,'calls':records,'failure':failure,
      'child_launcher_pid':None if proc is None else proc.pid,'child_returncode':None if proc is None else proc.returncode,'observed_child_exit':proc is not None and proc.poll() is not None,
      'elapsed_s':time.monotonic()-start,'observers':observed,'free_bytes_after':shutil.disk_usage(root).free,'owned_bytes_after':directory_size(root)}
    write(run/'run-result.json',result);print(str(run));return 0 if not failure and all(x['status']=='completed' for x in records) else 1

def worker(authority,release_path,split,owner,run_dir,job):
    import winjob
    winjob.join(job)  # Fail before model imports if supervisor ownership is unavailable.
    r=read_release(authority,release_path,split,owner);p=protocol();run=Path(run_dir).resolve();root=Path(r['runtime_root']).resolve()
    run.relative_to(root/'runs'/owner)
    if not (run/'plan.json').is_file():raise PermissionError('Parent plan missing')
    q0_imports()
    from q0harness.session import Session
    from q0harness.backend_torch import TorchBackend
    from q0harness.locks import validate_lock,git_blob_reader,verify_installed,verify_wheelhouse
    from q0harness.modelfiles import load_manifest,verify_model_dir,verify_notices,verify_module_cache
    from q0harness.sourcecheck import analyze_model_sources,MODEL_DIR_NAMES
    from q0harness.render import check_renderer,renderer_identity,render_pdf_bytes,raster_tuples
    from q0harness.telemetry import NativeObserver,resolve_targets
    from q0harness.procmem import PeakSampler
    from q0harness.environment import audit_child_env
    q=load_json(ROOT/p['q0_protocol_path']);lock=load_json(ROOT/p['dependency_lock_path']);be=TorchBackend();base=Path(p['read_only_q0_root']);model_dir=base/p['model_relative']
    session=Session(protocol=q,protocol_sha256=p['q0_protocol_sha256'],lock=lock,lock_sha256=p['dependency_lock_sha256'],release=None,root=root,owner=owner,run_dir=run,backend=be,repo_root=ROOT,expected_root=str(root),forbidden_parents=[],code={'baseline_source_commit':r['source_commit']},lock_reader=git_blob_reader(ROOT))
    session.heartbeat.start();failure=None;active_call=None
    try:
        session.phase('preflight',1800);audit_child_env(dict(os.environ),root=root,owner=owner,run_dir=run)
        packages=validate_lock(lock,git_blob_reader(ROOT));wheels=verify_wheelhouse(packages,base/'wheelhouse',lock)
        installed=verify_installed(packages,lock,be.installed(),be.importable)
        if be.importable('triton'):raise RuntimeError('Triton changes baseline path')
        session._check_platform(be.platform())
        pdfium=be.pdfium();renderer=renderer_identity(pdfium,be.dist_version);check_renderer(renderer,q)
        manifest=load_manifest(ROOT/p['model_manifest_path']);model_report=verify_model_dir(model_dir,manifest);notice=verify_notices(base/p['notice_relative'],manifest);safety=analyze_model_sources(model_dir,MODEL_DIR_NAMES)
        session.writer.write_json('preflight.json',{'wheels':wheels,'installed':installed,'model':model_report,'notice':notice,'safety':safety,'renderer':renderer,'worker_pid':os.getpid(),'release':r},cap_bytes=8<<20)
        session.phase('load',1800)
        with PeakSampler(.25) as sampler:tok,model,timing=be.load(model_dir,q)
        package=type(model).__module__.rsplit('.',1)[0]
        loaded={n:getattr(m,'__file__',None) for n,m in sys.modules.items() if n=='transformers_modules' or n.startswith('transformers_modules.')}
        cache=verify_module_cache(Path(os.environ['HF_MODULES_CACHE']),model_dir,loaded)
        session.writer.write_json('load.json',{'timing':timing,'host_memory':sampler.result(),'cuda_memory':be.cuda_memory(),'module_cache':cache},cap_bytes=8<<20)
        targets,missing=resolve_targets(sys.modules,prefix=package+'.');session.observer=NativeObserver(targets,missing,memory_probe=be.memory_probe).install()
        for call in schedule(p,split,r['sentinels'] if owner=='reviewer' else None):
            active_call=call['fixture_id']+'.'+call['kind']
            fx=next(f for f in p['fixtures'] if f['fixture_id']==call['fixture_id']);fx=dict(fx,max_new_tokens=8000*fx['page_count'],ngram_window=1024 if fx['page_count']>1 else 128)
            session.phase('render:'+fx['fixture_id'],1800);start=time.perf_counter();images=render_pdf_bytes(pdfium,pdf_for(fx,split=='eval_holdout'))
            if len(images)!=fx['page_count']:raise RuntimeError('Rendered page count mismatch')
            raster=[{'page':i+1,'width':w,'height':h,'rgb_sha256':sha(rgb)} for i,(w,h,rgb) in enumerate(raster_tuples(images))]
            session.writer.write_json(fx['fixture_id']+'.'+call['kind']+'.render.json',{'render_s':time.perf_counter()-start,'raster':raster,'pdf_sha256':fx['sha256']},cap_bytes=1<<20)
            label=fx['fixture_id']+'.'+call['kind'];session.phase('call:'+label,1800 if fx['page_count']==1 else 3600,stall=True)
            try:rec=session._observe(fx,dict(call,repeat=1),label,images,tok,model)
            finally:
                for image in images:image.close()
            if rec.get('flags') or rec.get('error') or rec['raw_output']['truncated_by_writer']:raise RuntimeError('Observed failed completion; stop without retry')
            if rec['kernel_path']['label']!='triton_import_failed_dense_fallback':raise RuntimeError('Unexpected native path')
    except BaseException as e:
        failure={'type':type(e).__name__,'detail':str(e),'traceback':traceback.format_exc(limit=20)}
    finally:
        if session.observer:session.observer.uninstall()
        session.heartbeat.set_phase('finished',None,False);session.heartbeat.stop();session.events.close()
    session.writer.write_json('worker-outcome.json',{'failure':failure,'active_call':active_call,'worker_pid':os.getpid(),'no_retry':True},cap_bytes=2<<20)
    return int(failure is not None)
