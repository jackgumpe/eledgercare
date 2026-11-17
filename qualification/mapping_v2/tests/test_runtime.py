"""CPU-owned process tests and fault injection; never calls a model or real observer."""
import contextlib
import ast
import csv
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from unittest.mock import patch
from qualification.mapping_v2 import runtime
from qualification.mapping_v2.common import ROOT,BASELINE,protocol,git,HERE
from qualification.mapping_v2.release import schedule
from test_release import valid_release

SCRATCH=ROOT/'.scratch/wp0013-vocabulary'


class RuntimeTests(unittest.TestCase):
    def setUp(self):SCRATCH.mkdir(parents=True,exist_ok=True)

    def test_runtime_worker_and_model_settings_preserve_accepted_source(self):
        old=git('show','253519e07e7d45cf1f5ecb3e03053582f7f7d4cc:qualification/coverage_v1/runtime.py').decode()
        expected=old.replace('eLedgerCare-CoverageV1-','eLedgerCare-MappingV2-').replace('coverage_v1_source_commit','mapping_v2_source_commit')
        current=(HERE/'runtime.py').read_text().split('\ndef worker(',1)[1]
        identity_block="    if parent_plan.get('supervisor_identity')!=process_identity(parent_plan['supervisor_pid']):\n        raise PermissionError('Supervisor creation identity changed')\n    worker_identity=process_identity(os.getpid())\n"
        self.assertIn(identity_block,current)
        current=current.replace(identity_block,'').replace(",'worker_identity':worker_identity",'')
        git_guard="    q0_imports()\n    from q0harness.environment import audit_child_env\n    audit_child_env(dict(os.environ),root=Path(protocol()['runtime_roots'][owner]),owner=owner,run_dir=Path(run_dir))\n    verify_bare_git_lookup(os.environ)  # Actual worker image/caller cwd, before frozen bare-Git checks.\n"
        self.assertIn(git_guard,current)
        current=current.replace(git_guard,'')
        self.assertEqual(current,expected.split('\ndef worker(',1)[1])
        previous=json.loads(git('show','253519e07e7d45cf1f5ecb3e03053582f7f7d4cc:qualification/coverage_v1/protocol.json'))
        p=protocol()
        for key in ('model','renderer','call','guards','gpu','read_only_q0_root','model_relative','notice_relative','storage_cap_bytes','free_floor_bytes','warmups','historical_warmups'):
            self.assertEqual(p[key],previous[key],key)

    def test_current_owned_process_creation_identity_is_stable(self):
        first=runtime.process_identity(os.getpid());second=runtime.process_identity(os.getpid())
        self.assertEqual(first,second);self.assertEqual(first['pid'],os.getpid())
        self.assertGreater(first['creation_filetime_100ns'],0)

    def test_exact_storage_time_log_and_stall_guards(self):
        p=protocol();base=dict(elapsed=0,phase_elapsed=0,progress_elapsed=0,stall_monitored=True,
                            phase_limit=1800,log_bytes=0,root_bytes=0,free_bytes=p['free_floor_bytes'],p=p)
        self.assertIsNone(runtime.guard_reason(**base))
        for key,value,want in [('elapsed',21601,'SESSION_TIMEOUT'),('phase_elapsed',1801,'PHASE_TIMEOUT'),
          ('progress_elapsed',301,'NO_FORWARD_PROGRESS'),('log_bytes',p['guards']['max_log_bytes']+1,'LOG_LIMIT'),
          ('root_bytes',p['storage_cap_bytes']+1,'STORAGE_CAP'),('free_bytes',p['free_floor_bytes']-1,'FREE_SPACE_FLOOR')]:
            with self.subTest(key=key):self.assertEqual(runtime.guard_reason(**{**base,key:value}),want)

    def test_gpu_observation_unavailable_or_wrong_device_rejected(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            root=Path(tmp);p=protocol();a=root/'a';b=root/'b';a.write_text('timestamp, '+p['gpu']['uuid']);b.write_text('')
            observed=[{'returncode':0,'bytes':x.stat().st_size,'path':str(x)} for x in (a,b)]
            runtime.verify_device_observation(observed,p)
            b.write_text('123, unrelated.exe, [N/A]')
            observed[1]['bytes']=b.stat().st_size
            self.assertIn('unrelated.exe',runtime.verify_device_observation(observed,p)['process_observation_text'])
            b.write_text('--- stderr --- warning')
            with self.assertRaises(PermissionError):runtime.verify_device_observation(observed,p)
            b.write_text('');a.write_text('wrong device')
            with self.assertRaises(PermissionError):runtime.verify_device_observation(observed,p)
            with self.assertRaises(PermissionError):runtime.verify_device_observation([],p)

    def test_retained_wddm_and_new_desktop_rows_are_preserved_not_classified(self):
        retained=json.loads((ROOT/'docs/coordination/WP-0007/gpu-reviewer-heldout-release/host-before.json').read_text())
        p=protocol()
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            paths=[Path(tmp)/str(i) for i in range(2)]
            for path,capture in zip(paths,retained['gpu_observer']):path.write_text(capture['stdout'],newline='')
            observed=[{'returncode':0,'bytes':path.stat().st_size,'path':str(path)} for path in paths]
            outcome=runtime.verify_device_observation(observed,p)
            self.assertEqual(len(list(csv.reader(io.StringIO(outcome['process_observation_text'])))),22)
            paths[1].write_text(retained['gpu_observer'][1]['stdout']+'42, C:/Edge/msedge.exe, [N/A]\n',newline='')
            observed[1]['bytes']=paths[1].stat().st_size
            self.assertIn('42, C:/Edge/msedge.exe',runtime.verify_device_observation(observed,p)['process_observation_text'])
            self.assertIn('without automatic classification',outcome['limit'])

    def supervisor_case(self,case):
        runtime.q0_imports()
        import q0harness.environment as env
        import q0harness.supervisor as observers
        import winjob
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            scratch=Path(tmp);base=scratch/'read-only-base';(base/'venv/Scripts').mkdir(parents=True)
            (base/'venv/Scripts/python.exe').write_bytes(b'CPU stub; never executed')
            p=protocol();p['read_only_q0_root']=str(base);p['free_floor_bytes']=0
            r=valid_release(p);r['runtime_root']=str(scratch/'owned-runtime');plan=schedule(p,'author')
            active=plan[2]['fixture_id']+'.measured';root=Path(r['runtime_root'])
            class Process:
                pid=123456;returncode=None if case=='scan_failure' else 0;kills=0;waits=0;polls=0
                def poll(self):
                    self.polls+=1
                    return None if case=='post_nonzero' and self.polls==1 else self.returncode
                def kill(self):self.kills+=1;self.returncode=1
                def wait(self,timeout):self.waits+=1;return self.returncode
            proc=Process()
            def spawn(*args,**kwargs):
                self.assertIn('--owner',args[0]);self.assertNotIn('--split',args[0]);self.assertEqual(kwargs['stdin'],subprocess.DEVNULL)
                run=next((root/'runs/author').iterdir());evidence=run/'evidence';evidence.mkdir()
                calls=plan[:2] if case=='scan_failure' else plan
                for c in calls:
                    (evidence/(c['fixture_id']+'.'+c['kind']+'.observation.json')).write_text(json.dumps({'flags':[]}))
                outcome={'failure':{'type':'test'} if case=='scan_failure' else None,'active_call':active}
                (evidence/'worker-outcome.json').write_text('{' if case=='malformed_outcome' else json.dumps(outcome))
                (run/'heartbeat.json').write_text(json.dumps({'phase':'call:'+active,'progress':1}))
                if case=='malformed_record':(evidence/(active+'.observation.json')).write_text('{')
                return proc
            def observe(commands,run,tag):
                if tag=='post' and case=='post_failure':raise OSError('CPU injected post-observer failure')
                paths=[run/('cpu-observer-'+tag+'-'+str(i)+'.txt') for i in range(2)]
                paths[0].write_text('timestamp, '+p['gpu']['uuid']);paths[1].write_text('')
                rows=[{'returncode':0,'bytes':x.stat().st_size,'path':str(x)} for x in paths]
                phase,_,fault=case.partition('_')
                if tag==phase:
                    if fault=='nonzero':rows[0]['returncode']=1
                    elif fault=='timeout':rows[0]['returncode']=None;rows[0]['error']='TimeoutExpired'
                    elif fault=='wrong_device':paths[0].write_text('timestamp, OTHER');rows[0]['bytes']=paths[0].stat().st_size
                    elif fault=='empty':return []
                    elif fault=='truncated':rows[0]['bytes']=65536
                    elif fault=='size_mismatch':rows[0]['bytes']+=1
                    elif fault=='error':rows[0]['error']='observer error despite zero exit'
                return rows
            environment={k:str(scratch/'cache'/k) for k in ['TEMP','TMP','TMPDIR','HF_HOME','HF_MODULES_CACHE','CUDA_CACHE_PATH','TORCH_HOME','TORCHINDUCTOR_CACHE_DIR','USERPROFILE']};environment['PATH']=os.environ.get('SystemRoot',r'C:\Windows')
            environment['Q0_GIT_EXECUTABLE']=env.resolve_host_git()  # Real lookup guard; other supervisor boundary effects remain mocked.
            with contextlib.ExitStack() as stack:
                for obj,name,kw in [(runtime,'read_release',{'return_value':r}),(runtime,'protocol',{'return_value':p}),
                    (runtime,'git',{'return_value':b'cpu-head'}),
                    (runtime,'process_identity',{'side_effect':lambda pid:{'pid':pid,'creation_filetime_100ns':pid,'created_utc':'CPU'}}),(env,'build_child_env',{'return_value':environment}),
                    (env,'audit_child_env',{}),(env,'resolve_host_git',{'return_value':'git'}),
                    (observers,'run_observers',{'side_effect':observe}),(winjob,'create',{'return_value':42}),
                    (runtime.time,'sleep',{}),
                    (runtime.subprocess,'Popen',{'side_effect':spawn})]:stack.enter_context(patch.object(obj,name,**kw))
                close=stack.enter_context(patch.object(winjob,'close'))
                if case=='scan_failure':stack.enter_context(patch.object(runtime,'directory_size',side_effect=PermissionError('CPU injected denied scan')))
                code=runtime.execute('CPU','CPU','author')
            close.assert_called_once_with(42)
            result=json.loads(next(root.rglob('run-result.json')).read_text())
            self.assertEqual(len(result['calls']),14);self.assertEqual(sum(not c['excluded'] for c in result['calls']),12)
            self.assertEqual(code,0 if case=='normal' else 1)
            if case=='normal':
                self.assertTrue(all(c['status']=='completed' for c in result['calls']))
                self.assertEqual(result['child_launcher_identity']['pid'],proc.pid)
                self.assertEqual(result['supervisor_identity']['pid'],os.getpid())
            if case=='scan_failure':
                self.assertEqual(proc.kills,1);self.assertGreaterEqual(proc.waits,1)
                self.assertEqual([x['status'] for x in result['calls']],['completed','completed','failed']+['not_run_after_failure']*11)
                self.assertEqual(result['supervisor_error']['type'],'PermissionError');self.assertIsNone(result['owned_bytes_after'])
            if case=='malformed_record':
                self.assertEqual(result['calls'][2]['status'],'failed')
                self.assertTrue(all(x['status']=='not_run_after_failure' for x in result['calls'][3:]))
                self.assertTrue(result['calls'][3]['unexpected_later_observation'])
            if case in ('malformed_outcome','post_failure'):self.assertTrue(result['finalization_errors'])
            if case.startswith('post_'):
                self.assertTrue(all(c['status']=='completed' for c in result['calls']))
                self.assertEqual(result['final_observation_status']['post_observers'],'unavailable')
                self.assertTrue(result['finalization_errors']);self.assertEqual(proc.kills,0)
            if case.startswith('pre_'):
                self.assertIsNone(result['child_launcher_pid']);self.assertEqual(proc.polls,0)
                self.assertTrue(all(c['status']=='not_run_after_failure' for c in result['calls']))
            self.assertFalse(list(base.glob('**/run-result.json')))
            print(json.dumps({'cpu_supervisor_case':case,'exit':code,'primary_denominator':12,'states':[x['status'] for x in result['calls']],'owned_child_kills':proc.kills}))

    def test_success_and_failure_retention(self):
        for case in ('normal','scan_failure','malformed_outcome','malformed_record','post_failure'):
            with self.subTest(case=case):self.supervisor_case(case)

    def test_returned_pre_and_post_observer_failures(self):
        for phase in ('pre','post'):
            for fault in ('nonzero','timeout','wrong_device','empty','truncated','size_mismatch','error'):
                with self.subTest(phase=phase,fault=fault):self.supervisor_case(phase+'_'+fault)

    @unittest.skipUnless(os.name=='nt','Windows job API')
    def test_real_owned_windows_job_closes_only_its_child(self):
        import winjob
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            marker=Path(tmp)/'joined';name='Local\\eLedgerCare-MappingV2-CPU-'+uuid.uuid4().hex
            handle=winjob.create(name);child=None;unrelated=None
            code="import sys,pathlib,time;sys.path.insert(0,sys.argv[1]);import winjob;winjob.join(sys.argv[2]);pathlib.Path(sys.argv[3]).write_text('joined');time.sleep(20)"
            try:
                child=subprocess.Popen([sys.executable,'-I','-B','-c',code,str(BASELINE),name,str(marker)],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
                unrelated=subprocess.Popen([sys.executable,'-I','-B','-c','import time;time.sleep(20)'],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
                start=time.monotonic()
                while not marker.exists() and child.poll() is None and time.monotonic()-start<5:time.sleep(.05)
                self.assertTrue(marker.exists(),'Owned child did not join job')
                winjob.close(handle);handle=None;child.wait(timeout=5)
                self.assertIsNone(unrelated.poll(),'Closing owned job affected unrelated owned test child')
                print(json.dumps({'real_windows_job':'PASS','owned_child_exit':child.returncode,'unrelated_child_alive_before_own_cleanup':True}))
            finally:
                if handle is not None:winjob.close(handle)
                for proc in (child,unrelated):
                    if proc and proc.poll() is None:proc.kill();proc.wait(timeout=5)
                    if proc and proc.stderr:proc.stderr.close()


if __name__=='__main__':unittest.main()
