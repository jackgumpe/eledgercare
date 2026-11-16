"""Focused CPU-only runtime correction checks; no model or external runtime access."""
import contextlib,copy,errno,importlib.abc,json,os,stat,subprocess,sys,tempfile,threading,time,types,unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parents[1];ROOT=HERE.parents[1]
sys.path[:0]=[str(HERE),str(ROOT/'qualification/q0/harness'),str(HERE/'tests')]
class NoModelImports(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in ('torch','transformers','triton') or fullname=='q0harness.backend_torch':
            raise RuntimeError('CPU checks forbid model imports: '+fullname)
sys.meta_path.insert(0,NoModelImports())
import runtime,release,baseline
from q0harness.session import Heartbeat
import test_baseline as original_tests
truth=original_tests.truth

class Entries:
    def __init__(self,items):self.items=iter(items)
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def __iter__(self):return self
    def __next__(self):return next(self.items)
def entries(items):return Entries(items)

def info(mode,size=0,attrs=0):return types.SimpleNamespace(st_mode=mode,st_size=size,st_file_attributes=attrs)

class Entry:
    def __init__(self,path,metadata=None,error=None,after=None):self.path=str(path);self.metadata=metadata;self.error=error;self.after=after;self.calls=0
    def stat(self,*,follow_symlinks):
        assert follow_symlinks is False
        self.calls+=1
        if self.error:raise self.error
        if self.after:self.after()
        return self.metadata

class SizeTests(unittest.TestCase):
    def test_stable_nested_empty_and_one_metadata_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'deep').mkdir();(root/'empty').mkdir();(root/'a').write_bytes(b'abc');(root/'deep/b').write_bytes(b'12345')
            self.assertEqual(runtime.directory_size(root),8)
            entry=Entry(root/'once',info(stat.S_IFREG,7))
            with patch('runtime.os.scandir',return_value=entries([entry])):self.assertEqual(runtime.directory_size(root),7)
            self.assertEqual(entry.calls,1)
    def test_disappearing_enumerated_file_and_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);gone=Entry(root/'gone',error=FileNotFoundError(errno.ENOENT,'gone',str(root/'gone')))
            child=Entry(root/'dir',info(stat.S_IFDIR));stable=Entry(root/'stable',info(stat.S_IFREG,9))
            def scan(path):
                if Path(path)==root:return entries([gone,child,stable])
                raise FileNotFoundError(errno.ENOENT,'vanished directory',str(path))
            with patch('runtime.os.scandir',side_effect=scan):self.assertEqual(runtime.directory_size(root),9)
    def test_disappearance_after_snapshot_needs_no_second_stat(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);target=root/'transient';target.write_bytes(b'123')
            entry=Entry(target,info(stat.S_IFREG,3),after=target.unlink)
            with patch('runtime.os.scandir',return_value=entries([entry])):self.assertEqual(runtime.directory_size(root),3)
            self.assertEqual(entry.calls,1);self.assertFalse(target.exists())
    def test_missing_non_directory_and_reparse_roots_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with self.assertRaises(FileNotFoundError):runtime.directory_size(root/'missing')
            (root/'file').write_bytes(b'x')
            with self.assertRaises(NotADirectoryError):runtime.directory_size(root/'file')
            with patch.object(Path,'stat',return_value=info(stat.S_IFDIR,attrs=0x400)) as metadata:
                with self.assertRaisesRegex(RuntimeError,'Reparse'):runtime.directory_size(root)
                metadata.assert_called_once_with(follow_symlinks=False)
            with patch('runtime.os.scandir',side_effect=FileNotFoundError('root vanished')):
                with self.assertRaises(FileNotFoundError):runtime.directory_size(root)
    def test_child_reparse_and_non_disappearance_errors_propagate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for entry,error in [(Entry(root/'link',info(stat.S_IFDIR,attrs=0x400)),RuntimeError),(Entry(root/'denied',error=PermissionError('denied')),PermissionError),(Entry(root/'io',error=OSError(errno.EIO,'io')),OSError)]:
                with patch('runtime.os.scandir',return_value=entries([entry])):
                    with self.assertRaises(error):runtime.directory_size(root)
            with patch('runtime.os.scandir',side_effect=PermissionError('denied root scan')):
                with self.assertRaises(PermissionError):runtime.directory_size(root)
    def test_actual_concurrent_unmodified_heartbeat(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'stable').write_bytes(b'x'*1000)
            state={'beats':0,'error':None};stop=threading.Event();ready=threading.Event()
            heartbeat=Heartbeat(root/'heartbeat.json',5,lambda:state['beats']);heartbeat.set_phase('cpu_probe',30,False)
            def writer():
                try:
                    while not stop.is_set():heartbeat.beat();state['beats']+=1;ready.set()
                except BaseException as exc:state['error']=repr(exc);ready.set()
            thread=threading.Thread(target=writer,name='author-owned-heartbeat');thread.start();ready.wait(2)
            scans=0;start=time.monotonic()
            try:
                while time.monotonic()-start<3:
                    self.assertGreaterEqual(runtime.directory_size(root),1000);scans+=1
            finally:stop.set();thread.join(5)
            self.assertFalse(thread.is_alive());self.assertIsNone(state['error']);self.assertGreater(scans,0);self.assertGreater(state['beats'],0)
            print(json.dumps({'actual_heartbeat':state,'successful_scans':scans,'seconds':time.monotonic()-start,'thread_joined':not thread.is_alive()}))

class RecoveryTests(unittest.TestCase):
    def valid(self):
        r=original_tests.CorpusReleaseTests().release();r['supplemental_recovery']=copy.deepcopy(release.RECOVERY_BINDING);return r
    def test_actual_prior_git_binding_and_exact_schedule(self):
        p=release.protocol();r=self.valid();release.validate_release(r,p,'dev','author',tree='2'*40)
        plan=release.released_schedule(p,r,'dev','author')
        self.assertEqual([x['fixture_id'] for x in plan if x['excluded']],p['warmups'])
        self.assertEqual([x['fixture_id'] for x in plan if not x['excluded']],['SYN-MP-01-v2-skew-pos4deg'])
        self.assertEqual(len(plan),3)
    def test_recovery_shape_scope_and_identity_rejections(self):
        p=release.protocol();r=self.valid()
        for key,value in [('fixture_id','SYN-WO-01-v0-clean'),('fixture_id','unknown'),('fixture_id','SYN-MP-02-v0-clean'),('fixture_id',['SYN-MP-01-v2-skew-pos4deg']*2),('prior_evidence_commit','0'*40),('prior_run_result_sha256','0'*64),('prior_authority_commit','0'*40),('prior_release_path','wrong')]:
            bad=copy.deepcopy(r);bad['supplemental_recovery'][key]=value
            with self.subTest(key=key,value=value),self.assertRaises(PermissionError):release.validate_recovery(bad,p,'dev','author')
        for split,owner in [('eval_holdout','author'),('dev','reviewer')]:
            with self.assertRaises(PermissionError):release.validate_recovery(r,p,split,owner)
        for value in [None,{},[],{**release.RECOVERY_BINDING,'extra':1}]:
            with self.assertRaises(PermissionError):release.validate_recovery({**r,'supplemental_recovery':value},p,'dev','author')
    def test_prior_missing_changed_bytes_and_semantic_mismatch(self):
        r=self.valid();p=release.protocol();b=release.RECOVERY_BINDING
        original=release.git('show',b['prior_evidence_commit']+':'+b['prior_run_result_path'])
        authority=release.git('show',b['prior_authority_commit']+':'+b['prior_release_path'])
        with patch('release.git',side_effect=subprocess.CalledProcessError(1,['git'])):
            with self.assertRaises(PermissionError):release.validate_recovery(r,p,'dev','author')
        with patch('release.git',side_effect=[original+b' ',authority]):
            with self.assertRaisesRegex(PermissionError,'byte mismatch'):release.validate_recovery(r,p,'dev','author')
        for mutation in ['completed','duplicate','unknown','heldout','authority','failure']:
            prior=json.loads(original)
            if mutation=='completed':prior['calls'][-1]['status']='completed'
            if mutation=='duplicate':prior['calls'].append(prior['calls'][-1])
            if mutation=='unknown':prior['calls'][-1]['fixture_id']='unknown'
            if mutation=='heldout':prior['calls'][-1]['fixture_id']='SYN-MP-02-v0-clean'
            if mutation=='authority':prior['release']['owner']='reviewer'
            if mutation=='failure':prior['failure']=None
            # Isolate semantic defenses after deliberately bypassing the independently tested byte gate.
            with self.subTest(mutation=mutation),patch('release.sha',return_value=b['prior_run_result_sha256']),patch('release.git',side_effect=[json.dumps(prior).encode(),authority]):
                with self.assertRaises(PermissionError):release.validate_recovery(r,p,'dev','author')
    def test_normal_author_and_reviewer_schedules_unchanged(self):
        p=release.protocol();r=original_tests.CorpusReleaseTests().release()
        for split in ('dev','eval_holdout'):
            self.assertEqual(release.released_schedule(p,r,split,'author'),release.schedule(p,split))
            self.assertEqual(release.released_schedule(p,r,split,'reviewer'),release.schedule(p,split,r['sentinels']))
    def test_old_review_route_rejected(self):
        r=original_tests.CorpusReleaseTests().release();r['accepted_review_path']=release.REVIEW_PATH.replace('/010_','/003_')
        with self.assertRaises(PermissionError):release.validate_release(r,release.protocol(),'dev','author',tree='2'*40)
    def test_supplemental_scoring_one_failed_denominator_no_original_rewrite(self):
        r=self.valid();p=release.protocol();before=release.git('show',release.RECOVERY_BINDING['prior_evidence_commit']+':'+release.RECOVERY_BINDING['prior_run_result_path'])
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'run-result.json').write_text(json.dumps({'release':r,'calls':[]}),encoding='utf-8')
            expected=truth();expected['fixture_id']=release.RECOVERY_BINDING['fixture_id']
            with patch('baseline.read_release',return_value=r),patch('baseline.expected_for',return_value=expected) as read,patch('baseline.reference_for',return_value={'pages':[],'coverage':{}}):
                baseline.score_run(root,root/'score.json','mock','mock','dev','author')
            packet=json.loads((root/'score.json').read_text(encoding='utf-8'))
            self.assertEqual(len(packet['scores']),1);self.assertEqual(packet['scores'][0]['fields']['total'],2)
            self.assertEqual(packet['summary']['dev']['document_denominator'],1);self.assertEqual(read.call_count,1)
            self.assertEqual(read.call_args.args[0]['fixture_id'],release.RECOVERY_BINDING['fixture_id'])
            self.assertIn('supplemental_single_failed_dev',packet['scope']);self.assertEqual(packet['supplemental_recovery'],release.RECOVERY_BINDING)
        self.assertEqual(before,release.git('show',release.RECOVERY_BINDING['prior_evidence_commit']+':'+release.RECOVERY_BINDING['prior_run_result_path']))

class SupervisorTests(unittest.TestCase):
    def test_structured_error_retains_cleanup(self):
        import q0harness.environment as env,q0harness.supervisor as observer,winjob
        with tempfile.TemporaryDirectory() as tmp:
            scratch=Path(tmp);base=scratch/'base';(base/'venv/Scripts').mkdir(parents=True);(base/'venv/Scripts/python.exe').write_bytes(b'not executed')
            root=scratch/'runtime';r=original_tests.CorpusReleaseTests().release();r['runtime_root']=str(root)
            p=release.protocol();p['read_only_q0_root']=str(base)
            child_env={k:str(scratch/'cache'/k) for k in ['TEMP','TMP','TMPDIR','HF_HOME','HF_MODULES_CACHE','CUDA_CACHE_PATH','TORCH_HOME','TORCHINDUCTOR_CACHE_DIR','USERPROFILE']};child_env['PATH']=''
            class Process:
                pid=123;returncode=None;killed=False;waited=False
                def poll(self):return self.returncode
                def kill(self):self.killed=True;self.returncode=1
                def wait(self,timeout):self.waited=True;return self.returncode
            proc=Process();original_load=runtime.load_json
            def load(path):
                if Path(path).name=='heartbeat.json':return {'phase':'call:owned-stub','progress':1}
                return original_load(path)
            exc=PermissionError(errno.EACCES,'denied scan',str(root/'denied'))
            with patch('runtime.read_release',return_value=r),patch('runtime.protocol',return_value=p),patch('runtime.git',return_value=b'cpu-test'),patch.object(env,'build_child_env',return_value=child_env),patch.object(env,'audit_child_env'),patch.object(env,'resolve_host_git',return_value='git'),patch.object(observer,'run_observers',return_value=[]),patch.object(winjob,'create',return_value=42),patch.object(winjob,'close') as close,patch('runtime.subprocess.Popen',return_value=proc),patch('runtime.load_json',side_effect=load),patch('runtime.directory_size',side_effect=[exc,0]):
                self.assertEqual(runtime.execute('mock','mock','dev','author'),1)
            self.assertTrue(proc.killed);self.assertTrue(proc.waited);close.assert_called_once_with(42)
            result=json.loads(next(root.rglob('run-result.json')).read_text(encoding='utf-8'))
            error=result['supervisor_error'];self.assertEqual(error['type'],'PermissionError');self.assertEqual(error['filename'],str(root/'denied'))
            self.assertEqual(error['active_phase'],'call:owned-stub');self.assertIn('PermissionError',error['traceback']);self.assertIn('denied scan',error['message'])
            self.assertTrue(result['failure'].startswith('SUPERVISOR_ERROR:'));self.assertEqual(len([c for c in result['calls'] if not c['excluded']]),13)

if __name__=='__main__':unittest.main()
