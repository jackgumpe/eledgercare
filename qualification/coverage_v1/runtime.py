"""Finite WP-0011 adaptation of accepted mapping-v1 runtime at 23e023045b335540d830ce01b75be247552a63f1.
Underlying B0 runtime source: 522f15f1f6e399c36b9c6c107fc08f51862f1fc1.
Q0 model/session/render/observation code is reused unchanged, imported only after release.
New finite input/release binding, owned job prefix, fail-closed preflight/record accounting.
"""
from __future__ import annotations
import csv,datetime,io,json,os,shutil,subprocess,sys,time,traceback,uuid
from pathlib import Path
from .common import ROOT,HERE,sha,load_json,write,protocol,git
from .release import read_release,schedule,fixture,pdf_bytes
from qualification.baseline.runtime import directory_size,guard_reason,supervisor_diagnostic,q0_imports


def verify_device_observation(observed,p):
    """Verify successful device capture, not an empty desktop or automatic lease proof."""
    if not isinstance(observed,list) or len(observed)!=2 or any(not isinstance(x,dict) or
        type(x.get('returncode')) is not int or x['returncode']!=0 or x.get('error') or x.get('truncated') or
        type(x.get('bytes')) is not int or not 0<=x['bytes']<65536 for x in observed):
        raise PermissionError('GPU observation unavailable/truncated')
    captures=[Path(x['path']).read_bytes() for x in observed]
    if any(len(data)!=row['bytes'] for row,data in zip(observed,captures)):
        raise PermissionError('GPU observation capture size mismatch')
    first,second=[data.decode('utf-8') for data in captures]
    device=list(csv.reader(io.StringIO(first),skipinitialspace=True))
    if len(device)!=1 or len(device[0])<2 or device[0][1]!=p['gpu']['uuid'] or '--- stderr ---' in first or '--- stderr ---' in second:
        raise PermissionError('Expected GPU observation unavailable')
    return {'expected_device_observed':True,'process_observation_text':second,
            'limit':'Process rows, including desktop sharing and WDDM [N/A], are retained without automatic classification. Root grants the sole model-job lease from reviewed process evidence; no OS-exclusive hardware assurance.'}


def execute(authority,release_path,owner):
    r=read_release(authority,release_path,owner);p=protocol();q0_imports()
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
    env=build_child_env(dict(os.environ),root=root,owner=owner,run_dir=run,gpu_uuid=r['lease']['gpu_uuid'],git_executable=resolve_host_git())
    env['VIRTUAL_ENV']=str(base/'venv');env['PATH']=str(base/'venv/Scripts')+os.pathsep+env['PATH']
    # HF caches must be per-run as well as task-local; never write reused Q0 root.
    for key,suffix in [('HF_HOME','hf-home'),('HF_HUB_CACHE','hf-home/hub'),('HUGGINGFACE_HUB_CACHE','hf-home/hub'),('TRANSFORMERS_CACHE','hf-home/transformers')]:env[key]=str(run/suffix)
    for key in ['TEMP','TMP','TMPDIR','HF_HOME','HF_MODULES_CACHE','CUDA_CACHE_PATH','TORCH_HOME','TORCHINDUCTOR_CACHE_DIR','USERPROFILE']:
        Path(env[key]).mkdir(parents=True,exist_ok=True)
    audit_child_env(env,root=root,owner=owner,run_dir=run)
    plan=schedule(p,owner)
    executing_head=git('rev-parse','HEAD').decode().strip()
    jobname='Local\\eLedgerCare-CoverageV1-'+uuid.uuid4().hex
    write(run/'plan.json',{'release':r,'authority_commit':authority,'release_path':release_path,'executing_head':executing_head,'calls':plan,'job_name':jobname,'supervisor_pid':os.getpid()})
    job=None
    cmd=[str(python),'-I','-B',str(HERE/'cli.py'),'worker','--authority',authority,'--release-path',release_path,'--owner',owner,'--run-dir',str(run),'--job',jobname]
    observed=[];process_checks=[];proc=None;failure=None;failure_detail=None;start=time.monotonic();last_phase=None;phase_start=start;progress_start=start;last_progress=None;next_obs=start+60
    secondary_errors=[];finalization_errors=[]
    def finish(stage,action,unavailable=None):
        # Bounded best-effort finalization, never a successful zero for a failed observation.
        nonlocal failure,failure_detail
        try:return action()
        except Exception as exc:
            detail={**supervisor_diagnostic(exc,last_phase),'stage':stage}
            finalization_errors.append(detail)
            if failure_detail is None:failure_detail=detail
            else:secondary_errors.append(detail)
            failure=failure or 'SUPERVISOR_FINALIZATION_ERROR:'+repr(exc)
            return unavailable
    def read_record(path,stage,worker=False):
        def read():
            try:value=load_json(path)
            except FileNotFoundError:return None,'absent'
            if not isinstance(value,dict):raise ValueError('Record must be a JSON object')
            if worker:
                if 'failure' not in value or 'active_call' not in value:raise ValueError('Malformed worker outcome')
            elif not isinstance(value.get('flags'),list):raise ValueError('Malformed call observation')
            return value,'available'
        return finish(stage,read,(None,'unavailable'))
    try:
        job=winjob.create(jobname)
        observed=run_observers(p['gpu']['observer']['commands'],run,'pre')
        process_checks.append({'stage':'pre',**verify_device_observation(observed,p)})
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
                if datetime.datetime.now(datetime.timezone.utc)>=datetime.datetime.fromisoformat(r['expires_utc'].replace('Z','+00:00')):failure=failure or 'LEASE_EXPIRED'
                if failure:break
                if now>=next_obs:
                    capture=run_observers(p['gpu']['observer']['commands'],run,f'during-{int(now-start)}');observed+=capture
                    process_checks.append({'stage':'during','elapsed_s':now-start,**verify_device_observation(capture,p)})
                    next_obs=now+60
                time.sleep(1)
            if failure:winjob.close(job);job=None;proc.kill()
            proc.wait(timeout=60)
    except BaseException as e:
        failure_detail={**supervisor_diagnostic(e,last_phase),'stage':'supervision'}
        failure=failure or 'SUPERVISOR_ERROR:'+repr(e)
    finally:
        call_phase_failure=failure  # Later cleanup/post failures do not undo completed calls.
        if job is not None:finish('cleanup_job_close',lambda:winjob.close(job))
        if proc is not None:
            alive=finish('cleanup_child_poll',proc.poll)
            if alive is None:
                finish('cleanup_child_kill',proc.kill)
                finish('cleanup_child_wait',lambda:proc.wait(timeout=60))
    post=finish('post_observers',lambda:run_observers(p['gpu']['observer']['commands'],run,'post'))
    if isinstance(post,list):observed+=post
    post_check=finish('post_observer_validation',lambda:verify_device_observation(post,p)) if post is not None else None
    if post_check is not None:process_checks.append({'stage':'post',**post_check})
    records=[]
    worker_outcome,worker_status=read_record(run/'evidence/worker-outcome.json','worker_outcome',worker=True)
    worker_outcome=worker_outcome or {}
    for call in plan:
        name=call['fixture_id']+'.'+call['kind'];path=run/'evidence'/f'{name}.observation.json'
        record,record_status=read_record(path,'call_observation:'+name)
        state='completed' if record and not record.get('flags') and not record.get('error') else 'failed' if record or record_status=='unavailable' else 'not_run_after_failure'
        if worker_outcome.get('failure') and worker_outcome.get('active_call')==name:state='failed'
        if call_phase_failure and last_phase in ('call:'+name,'render:'+call['fixture_id']):state='failed'
        records.append({**call,'status':state,'observation':str(path.relative_to(run)) if record else None,
                        'observation_status':record_status})
    # No later record can replace a first failed/unavailable scheduled call.
    stopped=False
    for record in records:
        if stopped:
            if record['status']=='completed':
                failure=failure or 'OBSERVATION_AFTER_FIRST_FAILURE'
                record['unexpected_later_observation']=record['observation']
            record['status']='not_run_after_failure';record['observation']=None
        elif record['status']!='completed':stopped=True
    if worker_status!='available':failure=failure or 'WORKER_OUTCOME_UNAVAILABLE'
    if worker_outcome.get('failure'):failure=failure or 'CHILD_REPORTED_FAILURE'
    if any(c['status']!='completed' for c in records):failure=failure or 'INCOMPLETE_SCHEDULE'
    if proc is None or proc.returncode!=0:failure=failure or 'CHILD_EXIT_FAILURE'
    child_exit=finish('child_exit_observation',proc.poll) if proc is not None else None
    free_after=finish('free_bytes_after',lambda:shutil.disk_usage(root).free)
    owned_after=finish('owned_bytes_after',lambda:directory_size(root))
    result={'schema':'eld-coverage-v1-run/1','run':str(run),'executing_head':executing_head,'release':r,'calls':records,'failure':failure,'supervisor_error':failure_detail,
      'secondary_errors':secondary_errors,'finalization_errors':finalization_errors,
      'final_observation_status':{'post_observers':'available' if post_check is not None else 'unavailable','worker_outcome':worker_status,
         'free_bytes_after':'available' if free_after is not None else 'unavailable','owned_bytes_after':'available' if owned_after is not None else 'unavailable'},
      'child_launcher_pid':None if proc is None else proc.pid,'child_returncode':None if proc is None else proc.returncode,
      'observed_child_exit':None if any(x['stage']=='child_exit_observation' for x in finalization_errors) else proc is not None and child_exit is not None,
      'elapsed_s':time.monotonic()-start,'observers':observed,'gpu_process_checks':process_checks,'free_bytes_after':free_after,'owned_bytes_after':owned_after}
    write(run/'run-result.json',result);print(str(run));return 0 if not failure and all(x['status']=='completed' for x in records) else 1

def worker(authority,release_path,owner,run_dir,job):
    import winjob
    winjob.join(job)  # Fail before model imports if supervisor ownership is unavailable.
    r=read_release(authority,release_path,owner);p=protocol();run=Path(run_dir).resolve();root=Path(r['runtime_root']).resolve()
    run.relative_to(root/'runs'/owner)
    if not (run/'plan.json').is_file():raise PermissionError('Parent plan missing')
    parent_plan=load_json(run/'plan.json')
    if (run.parent!=root/'runs'/owner or parent_plan.get('release')!=r or parent_plan.get('calls')!=schedule(p,owner)
        or parent_plan.get('job_name')!=job or not job.startswith('Local\\eLedgerCare-CoverageV1-')):
        raise PermissionError('Owned parent plan/job mismatch')
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
    session=Session(protocol=q,protocol_sha256=p['q0_protocol_sha256'],lock=lock,lock_sha256=p['dependency_lock_sha256'],release=None,root=root,owner=owner,run_dir=run,backend=be,repo_root=ROOT,expected_root=str(root),forbidden_parents=[],code={'coverage_v1_source_commit':r['source_commit']},lock_reader=git_blob_reader(ROOT))
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
        for call in schedule(p,owner):
            if datetime.datetime.now(datetime.timezone.utc)>=datetime.datetime.fromisoformat(r['expires_utc'].replace('Z','+00:00')):raise PermissionError('Lease expired before next call')
            active_call=call['fixture_id']+'.'+call['kind']
            fx=fixture(p,call['fixture_id']);fx=dict(fx,max_new_tokens=8000*fx['page_count'],ngram_window=1024 if fx['page_count']>1 else 128)
            session.phase('render:'+fx['fixture_id'],1800);start=time.perf_counter();images=render_pdf_bytes(pdfium,pdf_bytes(r,p,fx))
            if len(images)!=fx['page_count']:raise RuntimeError('Rendered page count mismatch')
            raster=[{'page':i+1,'width':w,'height':h,'rgb_sha256':sha(rgb)} for i,(w,h,rgb) in enumerate(raster_tuples(images))]
            session.writer.write_json(fx['fixture_id']+'.'+call['kind']+'.render.json',{'render_s':time.perf_counter()-start,'raster':raster,'pdf_sha256':sha(pdf_bytes(r,p,fx))},cap_bytes=1<<20)
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
