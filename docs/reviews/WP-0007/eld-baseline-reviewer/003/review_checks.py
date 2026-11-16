"""Independent CPU review probes. Never opens holdout content or loads a model."""
from __future__ import annotations
import collections, copy, ctypes, datetime, hashlib, json, os, subprocess, sys, time, traceback, uuid
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[5]
HERE = ROOT / 'qualification/baseline'
OWN = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import baseline, corpus, native, release, runtime, score

CANDIDATE = 'a998b765f7734453d27ec4a189a2156778f0913d'
PUBLICATION = '7abf4c1f6c3e6d8d92b6ddb8e45ec75e8daaf4d2'
VENV = Path(r'C:\Users\jackg\eLedgerCare-Q0\WP-0005\venv\Scripts\python.exe')
SENTINELS = ['SYN-WO-02-v3-hybrid-note', 'SYN-INV-03-v1-raster300', 'SYN-MP-02-v0-clean']
RULES = {'labels': [{'label':'ID','field_id':'id'}, {'label':'Optional','field_id':'optional'}],
         'tables':[{'table_id':'lines','headers':['Code','Price'],'columns':['code','price']}]}

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode().strip()

def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write('\n')

def block(text, kind='text'):
    return f'<BLOCK>{kind}[0,0,100,100]<FORK>{text}\n'

def expected():
    return {'fixture_id':'review-synthetic','family_id':'review','split':'dev','variant_kind':'v0_clean','page_count':1,
            'expected_fields':[{'field_id':'id','page_number':1,'printed_text':'007','normalized_value':'007'}],
            'expected_absences':[{'field_id':'optional','page_number':1}],
            'expected_tables':[{'table_id':'lines','rows':[{'row_id':'r1','page_number':1,
                'cells':{'code':{'printed_text':'A'},'price':{'printed_text':'$1'}}}]}],
            'page_sentinels':[],'expected_adjacent_page_pairs':[],'cross_page_links':[]}

def scored(raw, completion='completed', truth=None):
    pred = baseline.prediction(raw, RULES)
    return pred, score.score_document(pred, truth or expected(), {'pages':['ID: 007 Code Price A $1'],'coverage':{'status':'review-synthetic'}}, completion)

HEADER = '<tr><td>Code</td><td>Price</td></tr>'
ROW = '<tr><td>A</td><td>$1</td></tr>'

def content_audit():
    allowed = set()
    for f in corpus.fixtures():
        if f['split']=='dev':
            allowed.update(str((ROOT/f[k]).resolve()).casefold() for k in ('file_path','source_record_path','expected_ground_truth_path'))
    seen=[]; denied=[]
    def hook(event,args):
        if event=='open' and isinstance(args[0], (str,bytes)):
            p=Path(os.fsdecode(args[0])).resolve()
            if 'evaluation/synthetic/' in p.as_posix():
                if str(p).casefold() not in allowed:
                    denied.append(str(p)); raise PermissionError('Independent review forbids non-dev synthetic content')
                seen.append(str(p))
        if event=='import' and str(args[0]).split('.')[0] in ('torch','transformers'):
            raise PermissionError('No model/runtime library import in CPU review')
    sys.addaudithook(hook)
    return seen, denied

def probes(scratch, only=None):
    findings=[]
    def check(name, fn):
        if only and name not in only:return
        try:
            passed, detail=fn()
            findings.append({'name':name,'passed':bool(passed),'detail':detail})
        except Exception as e:
            findings.append({'name':name,'passed':False,'exception':type(e).__name__,'detail':str(e),'traceback':traceback.format_exc(limit=4)})

    good='<PAGE>'+block('ID: 007')+block('<table>'+HEADER+ROW+'</table>','table')
    def strict():
        _,s=scored(good.replace('007','7'))
        return s['fields']['correct']==0 and s['cells']['correct']==2, {'fields':s['fields']['correct'],'cells':s['cells']['correct']}
    check('strict_identifier_and_independent_cell_credit', strict)

    def failure():
        _,s=scored(good,'timeout')
        return (s['fields']['total'],s['cells']['total'],s['fields']['correct'],s['cells']['correct'],s['completed_documents'])==(1,2,0,0,0), {k:s[k] for k in ('fields','cells','completed_documents')}
    check('failed_completion_keeps_exact_denominators_and_zero_credit',failure)

    def duplicate():
        _,s=scored(good+block('ID: 007'))
        return s['fields']['unmatched_candidates']==1, s['fields']
    check('duplicate_ordinary_field_counted',duplicate)

    def short_extra():
        raw='<PAGE>'+block('ID: 007')+block('<table>'+HEADER+ROW+'<tr><td>EXTRA</td></tr></table>','table')
        pred,s=scored(raw)
        represented=s['cells']['extra_rows']>0 or any(x.get('values')==['EXTRA'] for x in pred['unmapped'])
        return represented, {'raw':raw,'predicted_tables':pred['tables'],'unmapped':pred['unmapped'],'extra_rows':s['cells']['extra_rows'],'extra_cells':s['cells']['extra_cells'],'exact_cells':s['cells']['correct']}
    check('short_extra_table_row_is_counted_or_explicitly_unmapped',short_extra)

    def spanned_extra():
        raw='<PAGE>'+block('<table>'+HEADER+ROW+'<tr><td colspan="2">EXTRA</td></tr></table>','table')
        pred,s=scored(raw)
        return s['cells']['extra_rows']>0 or any('EXTRA' in str(x) for x in pred['unmapped']), {'raw':raw,'tables':pred['tables'],'unmapped':pred['unmapped'],'extra_rows':s['cells']['extra_rows'],'extra_cells':s['cells']['extra_cells']}
    check('spanned_extra_table_row_is_counted_or_explicitly_unmapped',spanned_extra)

    def absence_duplicate():
        raw='<PAGE>'+block('Optional: EXTRA')*2
        pred,s=scored(raw)
        return s['fields']['unmatched_candidates']>=1, {'raw':raw,'field_candidates':pred['fields'],'unmatched_candidates':s['fields']['unmatched_candidates'],'absence':s['expected_absences']}
    check('duplicate_absence_candidates_remain_excess_candidates',absence_duplicate)

    def malformed(name,html):
        pred,s=scored('<PAGE>'+block('<table>'+HEADER+html,'table'))
        return bool(pred['parse_errors']) and s['cells']['correct']==0, {'variant':name,'parse_errors':pred['parse_errors'],'cells':s['cells'],'unmapped':pred['unmapped']}
    check('missing_table_close_invalidates_exact_credit',lambda:malformed('unclosed-table',ROW))
    check('unknown_table_attribute_invalidates_exact_credit',lambda:malformed('table-attribute',ROW+'</table><table unexpected="yes"></table>'))
    check('valueless_colspan_becomes_parse_failure_not_exception',lambda:malformed('valueless-colspan','<tr><td colspan>A</td><td>$1</td></tr></table>'))

    def holdout_refusal():
        f=next(f for f in corpus.fixtures() if f['split']=='eval_holdout');n=0
        with patch('corpus.verified',side_effect=AssertionError('content reader reached')):
            for fn in (corpus.pdf_for,corpus.expected_for,corpus.reference_for):
                try:fn(f)
                except PermissionError:n+=1
        return n==3, {'refused_before_verified_reader':n}
    check('holdout_pdf_expected_and_reference_refuse_before_content_read',holdout_refusal)

    def no_release():
        with patch('runtime.q0_imports',side_effect=AssertionError('runtime reached')):
            try:runtime.execute(None,None,'dev','reviewer')
            except PermissionError as e:return True, str(e)
        return False,'unexpected success'
    check('no_release_refused_before_runtime_imports',no_release)

    def new_review_path():
        p=release.protocol();tree=release.source_tree();head=git('rev-parse','HEAD')
        r={'schema':'eld-baseline-release/1','owner':'reviewer','source_commit':CANDIDATE,'executing_head':head,'source_tree':tree,
           'protocol_sha256':corpus.sha((HERE/'protocol.json').read_bytes()),'mapping_sha256':corpus.sha((HERE/'mapping.json').read_bytes()),'lock_sha256':p['dependency_lock_sha256'],
           'accepted_review_commit':'3'*40,'accepted_review_path':'docs/agent-reports/eld-baseline-reviewer/WP-0007/003_2026-11-16_review_eld-baseline-reviewer.md',
           'split':'dev','runtime_root':p['runtime_roots']['reviewer'],'lease_id':'CPU-TEST-NOT-A-LEASE','gpu_uuid':p['gpu']['uuid'],'expires_utc':'2099-01-01T00:00:00Z',
           'allow_test_content':False,'sentinels':SENTINELS,'observed_gpu_state':{'synthetic_unit_test':True},'torchvision_local_sha256_TOFU_accepted':True}
        real_git=release.git
        def fake_git(*args):
            if args==('status','--porcelain'):return b'' # Reviewed source was frozen; ignore this probe's new evidence files.
            if args==('show','1'*40+':docs/coordination/WP-0007/review-cpu-test.json'):return json.dumps(r).encode()
            if args==('show',r['accepted_review_commit']+':'+r['accepted_review_path']):return b'CPU validation placeholder, no acceptance or lease'
            return real_git(*args)
        with patch('release.git',side_effect=fake_git):
            try:release.read_release('1'*40,'docs/coordination/WP-0007/review-cpu-test.json','dev','reviewer')
            except PermissionError as e:return False, str(e)
        return True,'New canonical reviewer path accepted by pure release reader; no execution'
    check('newly_assigned_canonical_review_path_is_accepted',new_review_path)

    def completed_aborted_schedule():
        fake=scratch/'supervisor-stub';fake.mkdir()
        (fake/'baseline.py').write_text('import sys,json,time,os\nfrom pathlib import Path\nsys.path.insert(0,'+repr(str(HERE))+')\nimport winjob\na=sys.argv\nrun=Path(a[a.index("--run-dir")+1]);winjob.join(a[a.index("--job")+1])\n(run/"heartbeat.json").write_text(json.dumps({"phase":"call:SYN-WO-01-v0-clean.warmup","phase_timeout_s":0.1,"stall_monitored":True,"progress":0,"pid":os.getpid()}))\ntime.sleep(30)\n',encoding='utf-8')
        p=copy.deepcopy(release.protocol());p['guards']['timeouts_s']['session']=5
        r={'runtime_root':str(scratch/'supervisor-root'),'gpu_uuid':p['gpu']['uuid'],'sentinels':SENTINELS}
        with patch('runtime.read_release',return_value=r),patch('runtime.protocol',return_value=p),patch('runtime.HERE',fake),patch('q0harness.supervisor.run_observers',return_value=[]):
            rc=runtime.execute('CPU-TEST','docs/coordination/WP-0007/CPU-TEST-NOT-A-RELEASE.json','dev','author')
        results=list((scratch/'supervisor-root').rglob('run-result.json'));result=corpus.load_json(results[0])
        # Production scoring against the synthetic run; no release or GPU action occurs.
        with patch('baseline.read_release',return_value=r):
            baseline.score_run(results[0].parent,scratch/'supervisor-scores.json','CPU-TEST','CPU-TEST','dev','author')
        scored_docs=[]
        for f in corpus.fixtures():
            if f['split']=='dev':
                scored_docs.append(score.score_document(baseline.prediction('',RULES),corpus.expected_for(f),corpus.reference_for(f),'not_run_after_failure'))
        summary=score.summarize(scored_docs)
        wrapper_scores=corpus.load_json(scratch/'supervisor-scores.json')
        remaining=[c['status'] for c in result['calls'][1:]]
        return rc==1 and len(result['calls'])==15 and result['failure']=='PHASE_TIMEOUT' and result['calls'][0]['status']=='failed' and set(remaining)=={'not_run_after_failure'} and summary['dev']['document_denominator']==13 and wrapper_scores['summary']==summary, {'runtime_result':result,'dev_summary':summary,'score_run_matches_direct_scoring':wrapper_scores['summary']==summary}
    runtime.q0_imports()
    check('real_supervisor_timeout_retains_all_fifteen_planned_calls_and_thirteen_measured_denominators',completed_aborted_schedule)
    return findings

def reference_check():
    seen,denied=content_audit()
    import pypdfium2 as pdfium
    rows=[]
    def chars(s):return collections.Counter(c for c in native.norm(s) if not c.isspace())
    for f in corpus.fixtures():
        if f['split']!='dev' or f['variant_kind']!='v0_clean':continue
        ref=corpus.reference_for(f);doc=pdfium.PdfDocument(corpus.pdf_for(f));pages=[]
        for n in range(len(doc)):
            page=doc[n];textpage=page.get_textpage();text=textpage.get_text_range()
            pages.append({'page':n+1,'reference_nonspace_characters':sum(chars(ref['pages'][n]).values()),'pdfium_nonspace_characters':sum(chars(text).values()),'same_nonspace_character_multiset':chars(ref['pages'][n])==chars(text)})
            textpage.close();page.close()
        doc.close();rows.append({'fixture_id':f['fixture_id'],'page_count':len(ref['pages']),'pages':pages})
    hybrid=next(f for f in corpus.fixtures() if f['split']=='dev' and f['variant_kind']=='v3_hybrid')
    ref=corpus.reference_for(hybrid);source=json.loads(corpus.verified(hybrid['source_record_path'],hybrid['source_record_sha256']))
    add=source['hybrid_control'];added=[r for r in ref['runs'][add['target_page']-1] if r['source']=='declared_raster_addendum']
    print(json.dumps({'references':rows,'hybrid_declared_lines_exact':[r['text'] for r in added]==[add['label'],add['printed_text']], 'synthetic_files_opened':sorted(set(seen)),'denied':denied,'model_imports':[m for m in sys.modules if m in ('torch','transformers')],'limitation':'Character multiset verifies per-page inclusion independently; does not validate spatial reading order.'}))

def lifetime_check(scratch):
    """Crash an owned supervisor; wait on handles for actual venv launcher and worker."""
    import winjob
    k=winjob.api();k.OpenProcess.argtypes=[ctypes.c_ulong,ctypes.c_int,ctypes.c_ulong];k.OpenProcess.restype=ctypes.c_void_p
    k.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_ulong];k.WaitForSingleObject.restype=ctypes.c_ulong
    marker=scratch/'lifetime';marker.mkdir();job='Local\\B0-review-'+uuid.uuid4().hex
    worker=marker/'worker.py';worker.write_text('import sys,os,time\nfrom pathlib import Path\nsys.path.insert(0,'+repr(str(HERE))+')\nimport winjob\nwinjob.join('+repr(job)+')\nPath('+repr(str(marker/'worker.pid'))+').write_text(str(os.getpid()))\ntime.sleep(30)\n',encoding='utf-8')
    supervisor=marker/'supervisor.py';supervisor.write_text('import sys,subprocess,time\nfrom pathlib import Path\nsys.path.insert(0,'+repr(str(HERE))+')\nimport winjob\nh=winjob.create('+repr(job)+')\np=subprocess.Popen(['+repr(str(VENV))+',"-I","-B",'+repr(str(worker))+'],creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))\nPath('+repr(str(marker/'launcher.pid'))+').write_text(str(p.pid))\ntime.sleep(30)\n',encoding='utf-8')
    unrelated=subprocess.Popen([sys.executable,'-I','-B','-c','import time;time.sleep(30)'],creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    parent=subprocess.Popen([sys.executable,'-I','-B',str(supervisor)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    handles=[];pids=[]
    try:
        end=time.monotonic()+10
        while time.monotonic()<end and not (marker/'worker.pid').is_file():time.sleep(.05)
        pids=[int((marker/'launcher.pid').read_text()),int((marker/'worker.pid').read_text())]
        for pid in pids:
            handle=k.OpenProcess(0x100000,False,pid)
            if not handle:raise ctypes.WinError(ctypes.get_last_error())
            handles.append(handle)
        parent.kill();parent.wait(timeout=5)
        exits=[k.WaitForSingleObject(h,5000)==0 for h in handles]
        unaffected=unrelated.poll() is None
        return {'passed':all(exits) and unaffected,'supervisor_pid':parent.pid,'launcher_pid':pids[0],'actual_worker_pid':pids[1],'distinct_launcher_and_worker':pids[0]!=pids[1],'observed_handle_signaled':exits,'unrelated_owned_sentinel_survived':unaffected,'supervisor_returncode':parent.returncode}
    finally:
        if parent.poll() is None:parent.kill();parent.wait(timeout=5)
        if unrelated.poll() is None:unrelated.kill();unrelated.wait(timeout=5)
        for h in handles:k.CloseHandle(h)
        out,err=parent.communicate(timeout=5)
        (marker/'supervisor.stdout.txt').write_bytes(out);(marker/'supervisor.stderr.txt').write_bytes(err)

def main():
    if len(sys.argv)>1 and sys.argv[1]=='reference':reference_check();return
    head=git('rev-parse','HEAD');tag=head[:8]+'-'+datetime.datetime.now(datetime.timezone.utc).strftime('%H%M%S')
    scratch=ROOT/'.scratch'/'wp0007-review-003'/tag;scratch.mkdir(parents=True)
    evidence=OWN/'evidence'/tag;evidence.mkdir(parents=True)
    expected_tree=git('rev-parse',CANDIDATE+':qualification/baseline')
    if expected_tree!=git('rev-parse','HEAD:qualification/baseline'):raise RuntimeError('Reviewed candidate tree differs')
    if len(sys.argv)>1 and sys.argv[1]=='supervisor-only':
        seen,denied=content_audit()
        results=probes(scratch,only={'real_supervisor_timeout_retains_all_fifteen_planned_calls_and_thirteen_measured_denominators'})
        dump(evidence/'supervisor-recheck.json',{'execution_head':head,'candidate':CANDIDATE,'checks':results,'synthetic_files_opened':sorted(set(seen)),'denied':denied,'reason':'Correct reviewer test argument None to a string release path; initial run stopped in Popen before launching a child.'})
        print(json.dumps({'evidence':str(evidence),'checks':results}));return
    commands=[]
    for label,cmd in [('author-tests',[sys.executable,'-I','-B',str(HERE/'tests/test_baseline.py'),'-v']),
                      ('pdfium-reference',[str(VENV),'-I','-B',str(Path(__file__).resolve()),'reference'])]:
        cp=subprocess.run(cmd,cwd=ROOT,capture_output=True,timeout=120)
        (evidence/(label+'.stdout.txt')).write_bytes(cp.stdout);(evidence/(label+'.stderr.txt')).write_bytes(cp.stderr)
        commands.append({'label':label,'argv':cmd,'exit_code':cp.returncode})
    seen,denied=content_audit()
    results=probes(scratch)
    baseline.dev_check(scratch/'dev')
    reproduced=[]
    for name in ['F01.prediction.json','F01.reference.json','F01.score.json','F07.prediction.json','F07.reference.json','F07.score.json','summary.json']:
        a=(scratch/'dev'/name).read_bytes();b=(ROOT/'docs/evidence/WP-0007/eld-rd-astra/a998b765/dev'/name).read_bytes()
        reproduced.append({'file':name,'byte_identical':a==b,'sha256':corpus.sha(a)})
    try:lifetime=lifetime_check(scratch)
    except Exception as e:lifetime={'passed':False,'exception':type(e).__name__,'detail':str(e),'traceback':traceback.format_exc()}
    record={'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'review_execution_head':head,'candidate':CANDIDATE,'author_publication':PUBLICATION,'source_tree':expected_tree,'python':sys.version,'scratch':str(scratch),
            'commands':commands,'checks':results,'abrupt_supervisor_lifetime':lifetime,'dev_reproduction':reproduced,'synthetic_files_opened':sorted(set(seen)),'denied_synthetic_access':denied,'model_modules':[m for m in sys.modules if m in ('torch','transformers')],
            'unreleased_runtime_roots_exist':{k:Path(p).exists() for k,p in release.protocol()['runtime_roots'].items()}}
    dump(evidence/'results.json',record)
    print(json.dumps({'evidence':str(evidence),'checks':len(results),'failed_checks':[x['name'] for x in results if not x['passed']],'lifetime_passed':lifetime['passed'],'commands':commands}))

if __name__=='__main__':main()
