"""Independent WP11 CPU audit; never opens runtime roots or runs observers.

Adapted from the independently used WP9 /008 compare_published.py. GitReader,
path checks, direct B0/v1 reproduction and telemetry inspection retain attribution.
New WP11 diagnostics, finite status validation, manifests and sentinel binding are
reviewer code only. Future completed publications must be supplied explicitly.
"""
from pathlib import Path, PurePosixPath, PureWindowsPath
import argparse,datetime,hashlib,importlib.abc,json,re,subprocess,sys,traceback

ROOT=Path(__file__).resolve().parents[5]
OWN=Path(__file__).resolve().parent
SOURCE='253519e07e7d45cf1f5ecb3e03053582f7f7d4cc'
TREE='6bdab544c9fe26cbf093cc765212db2a2e7a97a5'
PROTOCOL='03b13a41a0047c827af32e71209933700457a5dfd6d38ec106daed82ef5b9000'
sys.path.insert(0,str(ROOT))
class NoModel(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in ('torch','transformers','triton','pypdfium2') or fullname=='q0harness.backend_torch':raise RuntimeError('CPU review prohibits model/renderer imports: '+fullname)
sys.meta_path.insert(0,NoModel())
from qualification.mapping_v1.common import mapping,parse_native,ParseError,baseline_prediction,score_document,summarize
from qualification.mapping_v1.mapper import extract_prediction
from qualification.coverage_v1.release import schedule,validate_release
from qualification.coverage_v1.common import protocol
from qualification.coverage_v1.diagnostics import diagnose,paired_conditions
from qualification.coverage_v1.contract import validate

def sha(data):return hashlib.sha256(data).hexdigest()
def require(ok,message):
    if not ok:raise ValueError(message)
def safe(path):
    require(isinstance(path,str),'Path must be text');path=path.replace('\\','/')
    p=PurePosixPath(path)
    require(path and not p.is_absolute() and not PureWindowsPath(path).drive and all(x not in ('','.','..') for x in path.split('/')),'Unsafe published path')
    return path
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def load(data):return json.loads(data.decode('utf-8-sig'))
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def json_value(value):return load(canonical(value))

def source_inventory():
    p=protocol();out=[]
    for prefix,expected in [('qualification/coverage_v1',TREE),('qualification/mapping_v1',p['mapping_v1_tree']),('qualification/baseline',p['comparator_tree']),('qualification/q0/harness/q0harness',p['q0_core_tree'])]:
        require(git('rev-parse','HEAD:'+prefix).decode().strip()==expected,'Accepted source tree changed: '+prefix)
        for path in git('ls-tree','-r','--name-only','HEAD','--',prefix).decode().splitlines():
            data=(ROOT/path).read_bytes();committed=git('show','HEAD:'+path)
            blob=git('rev-parse','HEAD:'+path).decode().strip()
            require(git('hash-object','--',path).decode().strip()==blob,'Uncommitted source alteration: '+path)
            require(data==committed or data.replace(b'\r\n',b'\n')==committed,'Unexplained working/Git bytes: '+path)
            out.append({'path':path,'bytes_working':len(data),'sha256_working':sha(data),'bytes_git':len(committed),'sha256_git':sha(committed),'git_blob':blob})
    for key in ('q0_protocol','dependency_lock','model_manifest'):
        path=p[key+'_path'];data=(ROOT/path).read_bytes();require(sha(data)==p[key+'_sha256'],'Qualified input changed: '+key)
        out.append({'path':path,'bytes':len(data),'sha256':sha(data)})
    return out

class GitReader:
    def __init__(self,revision):
        require(bool(re.fullmatch('[0-9a-f]{40}',revision)),'Full published revision required')
        self.revision=revision;self.inputs={}
    def read(self,path):
        path=safe(path);data=git('show',self.revision+':'+path)
        self.inputs[path]={'commit':self.revision,'path':path,'bytes':len(data),'sha256':sha(data),'git_blob':git('rev-parse',self.revision+':'+path).decode().strip()}
        return data
    def all_under(self,prefix):
        prefix=safe(prefix)
        paths=git('ls-tree','-r','--name-only',self.revision,'--',prefix).decode().splitlines()
        require(paths and all(p.startswith(prefix+'/') for p in paths),'Empty/escaping published packet')
        for path in paths:self.read(path)
        return paths

def reproduce(raw,expected,reference,completion,rules):
    def unavailable(exc):return {'fields':[],'tables':[],'anchors':[],'unmapped':[{'kind':'parse_failure','detail':str(exc)}],'pages':[],'parse_errors':[str(exc)]}
    try:parsed=parse_native(raw)
    except (ParseError,ValueError,TypeError) as exc:before=unavailable(exc);after=unavailable(exc)
    else:
        def predict(mapper):
            try:return mapper(parsed,rules)
            except (ParseError,ValueError,TypeError) as exc:return unavailable(exc)
        before=predict(baseline_prediction);after=predict(extract_prediction)
    return {'raw_sha256':sha(raw.encode('utf-8')),'completion':completion,'predictions':{'b0':before,'mapping_v1':after},'scores':{k:score_document(v,expected,reference,completion) for k,v in [('b0',before),('mapping_v1',after)]}}

def field_changes(pair):
    out={}
    for metric in ('fields','normalized_fields','cells','normalized_cells'):
        a=pair['scores']['b0'][metric]['details'];b=pair['scores']['mapping_v1'][metric]['details']
        require(len(a)==len(b),'Paired denominator changed')
        out[metric]={'gains':[],'losses':[],'other_changes':[]}
        for ordinal,(x,y) in enumerate(zip(a,b)):
            if x==y:continue
            kind='gains' if y['credited_exact'] and not x['credited_exact'] else 'losses' if x['credited_exact'] and not y['credited_exact'] else 'other_changes'
            out[metric][kind].append({'ordinal':ordinal,'before':x,'after':y})
    out['non_field_changed_objects']=[k for k in ('cells','normalized_cells','rows','expected_absences','page_count','page_sentinels','adjacency','cross_page_links','text','parse_errors') if pair['scores']['b0'][k]!=pair['scores']['mapping_v1'][k]]
    return out

def inspect_run(read,p,release,owner,fixture_data,published_scores=None):
    """read(relative) supplies immutable publication bytes, or explicit self-test memory bytes."""
    result=load(read('run-result.json'));plan=load(read('plan.json'));planned=schedule(p,owner)
    require(result['release']==release==plan['release'],'Run/plan/release mismatch')
    require(result['executing_head']==release['executing_head']==plan['executing_head'],'Executing HEAD mismatch')
    require(plan['calls']==planned==release['schedule'],'Plan/release denominator mismatch')
    require(result.get('schema')=='eld-coverage-v1-run/1' and 'failure' in result and (result['failure'] is None or isinstance(result['failure'],str)),'Malformed run result')
    require([{k:c[k] for k in ('fixture_id','kind','excluded')} for c in result['calls']]==planned,'Actual call schedule mismatch')
    issues=[];calls=[];records=[];diagnostics=[];material={};stopped=False
    allfx={f['fixture_id']:f for f in p['historical_warmups']+p['fresh_fixtures']}
    for call in result['calls']:
        fid=call['fixture_id'];fx=allfx[fid];status=call['status'];label=fid+'.'+call['kind']
        require(status in ('completed','failed','not_run_after_failure'),'Unknown call status')
        require({'observation','observation_status'}<=call.keys(),'Incomplete call record')
        require(call['observation_status'] in ('available','absent','unavailable'),'Unknown observation status')
        if status=='completed':require(call['observation_status']=='available' and isinstance(call['observation'],str) and call['observation'],'Completed observation unavailable')
        if status=='not_run_after_failure':require(call['observation'] is None,'Not-run scored observation')
        if call['observation'] is not None:require(call['observation_status']=='available','Unavailable observation reference')
        if stopped:require(status=='not_run_after_failure','Later call substituted after first failure')
        if status!='completed':stopped=True
        raw=b'';tokens=None;obs=None;render=None;missing=[]
        if call.get('observation'):
            opath=safe(call['observation']);obs=load(read(opath));parent=PurePosixPath(opath).parent
            require(isinstance(obs.get('flags'),list),'Malformed observation flags')
            require(obs.get('fixture_id')==fid and obs.get('kind')==call['kind'],'Observation identity mismatch')
            require(obs.get('family_id')==fx['family_id'] and obs.get('page_count_in')==fx['page_count'],'Observation fixture/page mismatch')
            require(obs.get('excluded_from_warm_statistics') is call['excluded'],'Warmup exclusion mismatch')
            if 'raw_output' in obs:
                desc=obs['raw_output'];raw=read(safe(str(parent/safe(desc['name']))))
                require(sha(raw)==desc['sha256_written'] and len(raw)==desc['bytes_written'],'Retained raw identity mismatch')
            if 'token_ids_file' in obs:
                desc=obs['token_ids_file'];data=read(safe(str(parent/safe(desc['name']))))
                require(sha(data)==desc['sha256_written'] and len(data)==desc['bytes_written'],'Retained token file identity mismatch')
                try:
                    tokens=load(data);require(isinstance(tokens,list) and all(type(x) is int for x in tokens),'Invalid token sequence')
                except (ValueError,UnicodeError):
                    require(status!='completed','Invalid completed token sequence');tokens=None;missing.append('Retained failed-call token bytes are not a complete integer sequence')
                if tokens is not None:require(sha(json.dumps(tokens).encode())==obs['native']['token_ids_sha256'],'Native token sequence hash mismatch')
            render=load(read('evidence/'+label+'.render.json'))
            expected_pdf=fx['sha256'] if fid in p['warmups'] else next(a['sha256'] for a in fx['artifacts'] if a['role']=='pdf')
            require(render['pdf_sha256']==expected_pdf and len(render['raster'])==fx['page_count'],'Render/input binding mismatch')
            require([r['page'] for r in render['raster']]==list(range(1,fx['page_count']+1)),'Render page order mismatch')
            require(all(type(x.get('width')) is int and x['width']>0 and type(x.get('height')) is int and x['height']>0 and re.fullmatch('[0-9a-f]{64}',x.get('rgb_sha256','')) for x in render['raster']),'Malformed raster identity')
            kwargs=dict(p['call']['fixed_kwargs'],max_new_tokens=8000*fx['page_count'],ngram_window=1024 if fx['page_count']>1 else 128)
            require(obs['call_kwargs']==kwargs,'Qualified call parameters changed')
        if status=='completed':
            require(obs is not None and not obs.get('flags') and not obs.get('error'),'Completed call lacks successful observation')
            require(tokens is not None and 'raw_output' in obs,'Completed raw/token evidence missing')
            require(obs['raw_output']['truncated_by_writer'] is False and obs['raw_output']['utf8_lossless'] is True,'Completed raw is truncated/lossy')
            native=obs['native'];require(native['text_sha256']==sha(raw) and native['finish_reason']=='stop','Native text/finish mismatch')
            require(native['expected_pages']==native['num_pages_out']==fx['page_count'],'Native page count mismatch')
            require(native['output_tokens']==len(tokens),'Native output token count mismatch')
            require(0<native['prompt_len'] and native['prompt_len']+kwargs['max_new_tokens']<=kwargs['max_length'],'Context budget mismatch')
            require(obs['kernel_path']['label']=='triton_import_failed_dense_fallback','Qualified kernel path changed')
        else:
            if obs is None:missing.append('no retained observation; empty prediction is accounting only')
            if tokens is None:missing.append('no retained token sequence')
        calls.append({'fixture_id':fid,'kind':call['kind'],'excluded':call['excluded'],'status':status,'raw_sha256':sha(raw) if obs and 'raw_output' in obs else None,'token_sequence_sha256':None if tokens is None else sha(json.dumps(tokens).encode()),'missing':missing,'timing':None if obs is None else obs.get('timing'),'host_memory':None if obs is None else obs.get('host_memory'),'cuda_memory':None if obs is None else obs.get('cuda_memory'),'render':render})
        if call['excluded']:continue
        expected,reference,annotations=fixture_data(fid);validate(expected,reference,annotations)
        require(expected['fixture_id']==fid and expected['family_id']==fx['family_id'] and expected['page_count']==fx['page_count'],'Expected corpus identity mismatch')
        require(isinstance(reference['pages'],list) and len(reference['pages'])==fx['page_count'],'Reference page count mismatch')
        pair=reproduce(raw.decode('utf-8'),expected,reference,status,mapping())
        diagnostic=diagnose(raw.decode('utf-8') if obs and 'raw_output' in obs else None,expected,reference,status,annotations,pair)
        diagnostics.append(diagnostic)
        records.append(json_value({'fixture_id':fid,**pair,'diagnostic':{k:v for k,v in diagnostic.items() if k!='historical_scores'}}))
        material[fid]={'available':status=='completed' and tokens is not None,'raw':raw,'tokens':tokens,'scores':pair['scores'],'predictions':pair['predictions'],'diagnostic':json_value(diagnostic),'render':render,'status':status}
    require(not stopped or bool(result['failure']),'Incomplete calls without run failure')
    require(len(records)==(12 if owner=='author' else 1),'Wrong primary document denominator')
    summary={key:summarize([x['scores'][key] for x in records]) for key in ('b0','mapping_v1')}
    pairing=paired_conditions(diagnostics) if owner=='author' else {'sentinel_documents':1,'preselected_id':p['reviewer_sentinel'],'limit':'Reviewer sentinel is not the twelve-author-document population.'}
    expected_packet={'schema':'eld-coverage-paired/1','owner':owner,'run_result_sha256':sha(read('run-result.json')),'records':records,
        'historical_summary':summary,'diagnostic_pairing':pairing,
        'interpretation':'Unchanged B0/v1 full metrics plus separately versioned stage evidence; no quality treatment or causal certainty.'}
    if published_scores is not None:
        require(canonical(published_scores)==canonical(expected_packet),'Published full prediction/score/diagnostic/denominator packet differs')
    observer_checks=[]
    for obs in result.get('observers',[]):
        name=PureWindowsPath(obs['path']).name;data=read(safe(name));require(len(data)==obs['bytes'],'Observer captured byte count mismatch')
        observer_checks.append({'tag':obs.get('tag'),'index':obs.get('index'),'returncode':obs.get('returncode'),'bytes':len(data),'sha256':sha(data),'truncated_or_stderr':len(data)>=65536 or b'--- stderr ---' in data})
        if obs.get('returncode')!=0 or len(data)>=65536 or b'--- stderr ---' in data:issues.append('Observer unavailable/truncated/stderr: '+name)
    def optional(path):
        try:return load(read(path))
        except (FileNotFoundError,subprocess.CalledProcessError):issues.append('Missing published '+path);return None
    worker=optional('evidence/worker-outcome.json');preflight=optional('evidence/preflight.json');loaded=optional('evidence/load.json')
    if worker is None or worker.get('failure') or worker.get('no_retry') is not True:issues.append('Worker failure/termination or missing no-retry evidence')
    if result.get('failure') or result.get('child_returncode')!=0 or result.get('observed_child_exit') is not True:issues.append('Supervisor reports failure/nonzero or unknown child exit')
    if not observer_checks:issues.append('No runtime observer captures')
    if preflight:
        require(preflight['release']==release,'Preflight release mismatch')
        if preflight.get('renderer',{}).get('distribution_version')!=p['renderer']['version']:issues.append('Renderer version mismatch')
        model=preflight.get('model',{}).get('files',[])
        if len(model)!=18 or not all(f.get('ok') is True for f in model):issues.append('Model object verification incomplete')
        notices=preflight.get('notice',{}).get('notices',[])
        if not notices or not all(n.get('ok') is True for n in notices):issues.append('Model notice verification failed/incomplete')
    if loaded:
        modules=loaded.get('module_cache',{}).get('modules',[])
        if not modules or not all(m.get('identical') is True for m in modules):issues.append('Loaded module cache mismatch/incomplete')
    changes={x['fixture_id']:field_changes(x) for x in records}
    public={'owner':owner,'primary_document_denominator':len(records),'completed_primary':sum(x['completion']=='completed' for x in records),'excluded_warmups':2,'records':records,'summary':summary,'per_item_changes':changes,'calls':calls,'observer_checks':observer_checks,'metadata_issues':issues,'worker_outcome':worker,'preflight':preflight,'load':loaded,'runtime_outcome':{k:result.get(k) for k in ('failure','supervisor_error','secondary_errors','finalization_errors','final_observation_status','child_launcher_pid','child_returncode','observed_child_exit','elapsed_s','free_bytes_after','owned_bytes_after')},'checks_requiring_separate_exact_coordinator_proof':['supervisor tool exit distinct from child exit','owner lease return and independently observed process absence/job cleanup','post-run model/notice identity and current ownership'],'limits':['Twelve author documents in three families and one reviewer sentinel are different denominators.','Latency/memory are descriptive per-call observations; WDDM/desktop sharing and sampled peaks remain confounders.','Unmapped or empty evidence does not prove recognition omission; unverified absences and unmatched candidates do not prove no inventions.','No population accuracy or deterministic GPU output guarantee.']}
    public['diagnostic_pairing']=pairing;public['complete_reproduced_packet']=expected_packet
    public['presence_denominator']={k:sum(d['presence_denominator'][k] for d in diagnostics) for k in ('all_expected_slots','eligible_slots','unavailable_slots')}
    return {'public':public,'material':material}

def compare_sentinel(author,reviewer):
    fid='WP11-F03-degraded-v0';require(author['public']['owner']=='author' and reviewer['public']['owner']=='reviewer','Wrong comparison owners')
    a=author['material'][fid];b=reviewer['material'][fid]
    available=a['available'] and b['available']
    return {'fixture_id':fid,'author_denominator':12,'reviewer_denominator':1,'both_completed':available,
        'raw_bytes_equal':a['raw']==b['raw'] if available else None,'token_ids_equal':a['tokens']==b['tokens'] if available else None,
        'full_scores_equal':a['scores']==b['scores'],'full_predictions_equal':a['predictions']==b['predictions'],
        'full_diagnostics_equal':a['diagnostic']==b['diagnostic'],
        'author_raw_sha256':sha(a['raw']) if a['available'] else None,'reviewer_raw_sha256':sha(b['raw']) if b['available'] else None,
        'author_token_sequence_sha256':sha(json.dumps(a['tokens']).encode()) if a['tokens'] is not None else None,
        'reviewer_token_sequence_sha256':sha(json.dumps(b['tokens']).encode()) if b['tokens'] is not None else None,
        'render_rasters_equal':a['render']['raster']==b['render']['raster'] if a['render'] and b['render'] else None,
        'author_status':a['status'],'reviewer_status':b['status'],
        'interpretation':'Empirical equality/differences, not GPU determinism. If either call is unavailable, score/diagnostic equality describes accounting only; no observed-output equality is inferred.'}

def verify_manifest(read,actual_paths,manifest):
    """Normalized future root binding records original and copied identities.

    Original bytes are attested by immutable collection evidence; this helper
    independently hashes publication bytes, and does not open a runtime root.
    """
    require(manifest.get('schema')=='eld-review-run-copy-manifest/1','Unknown copy manifest')
    rows=manifest.get('files');require(isinstance(rows,list),'Missing copy manifest rows')
    paths=[safe(x['relative_path']) for x in rows]
    require(len(set(paths))==len(paths) and set(paths)==set(actual_paths),'Incomplete/duplicate run copy inventory')
    results=[]
    for row in rows:
        data=read(row['relative_path'])
        require(len(data)==row['bytes']==row['original_bytes'] and sha(data)==row['sha256']==row['original_sha256'],'Original/copied publication identity mismatch')
        results.append({'relative_path':row['relative_path'],'bytes':len(data),'sha256':sha(data)})
    return {'files':results,'count':len(results),'original_comparison_limit':'Original hashes are authenticated retained-collection claims, independently reconciled to published bytes. Live original files are not reread by this helper.'}

def bound(binding):
    reader=GitReader(binding['commit']);data=reader.read(binding['path']);require(sha(data)==binding['sha256'],'Bound evidence digest mismatch')
    return load(data),list(reader.inputs.values())

def verify_publication_inventory(binding,publication):
    inventory,inputs=bound(binding);reader=GitReader(inventory['deliverable_commit'])
    require(inventory.get('schema')=='eld-review-publication-inventory/1','Unknown normalized publication inventory')
    def listing(rev):return {x.split(b'\t',1)[1].decode():x.split(b'\t',1)[0] for x in git('ls-tree','-r','-z',rev).split(b'\0') if x}
    base=listing(inventory['base_commit']);end=listing(inventory['deliverable_commit']);pub=listing(publication)
    require(all(end.get(k)==v for k,v in base.items()),'Result publication modified prior paths')
    added=set(end)-set(base);rows=inventory['files'];require(added=={x['path'] for x in rows} and len(rows)==len(added),'Incomplete deliverable inventory')
    for row in rows:
        data=reader.read(row['path']);require(sha(data)==row['sha256_git'] and len(data)==row['bytes_git'],'Deliverable bytes mismatch')
        require(end[row['path']].decode().split()[-1]==row['git_blob'] and pub.get(row['path'])==end[row['path']],'Deliverable/publication blob mismatch')
    return {'protected_paths':len(base),'deliverable_paths':len(rows),'inputs':inputs+list(reader.inputs.values())}

def audit_published(spec):
    p=protocol();pub=GitReader(spec['publication']);authority=GitReader(spec['authority']);r=load(authority.read(spec['release_path']))
    require(r['owner']==spec['owner'] and r['source_commit']==SOURCE and r['source_tree']==TREE and r['protocol_sha256']==PROTOCOL,'Released source identity mismatch')
    validate_release(r,p,spec['owner'],head=r['executing_head'],source_tree=TREE,protocol_digest=PROTOCOL,clean=True,execution=False)
    require(r['lease']['scope']=='sole_model_job' and r['lease']['sole_lease'] is True,'Wrong lease scope')
    require(git('rev-parse',r['executing_head']+':qualification/coverage_v1').decode().strip()==TREE,'Executing source tree mismatch')
    require(r['comparator_tree']==p['comparator_tree'] and r['mapping_v1_tree']==p['mapping_v1_tree'] and r['q0_core_tree']==p['q0_core_tree'] and r['reservation_sha256']==p['public_reservation_sha256'],'Released comparator/Q0/reservation changed')
    for prefix,key in [('qualification/baseline','comparator_tree'),('qualification/mapping_v1','mapping_v1_tree'),('qualification/q0/harness/q0harness','q0_core_tree')]:
        require(git('rev-parse',r['executing_head']+':'+prefix).decode().strip()==p[key],'Executing protected tree mismatch')
    proofs=[]
    for binding in [r['source_review'],r['admission_review'],r['unseal'],*r['lease']['observations']]:
        reader=GitReader(binding['commit']);data=reader.read(binding['path']);require(sha(data)==binding['sha256'],'Release proof digest mismatch');proofs.extend(reader.inputs.values())
    unseal,unseal_inputs=bound(r['unseal']);proofs.extend(unseal_inputs)
    require(unseal.get('schema')=='eld-coverage-v1-unseal/1' and unseal.get('allow_content') is True and unseal.get('source_commit')==SOURCE and unseal.get('source_review_commit')==r['source_review']['commit'] and unseal.get('admission_review_commit')==r['admission_review']['commit'] and unseal.get('reservation_sha256')==p['public_reservation_sha256'],'Unseal/release mismatch')
    corpus=GitReader(r['corpus_commit']);fixtures={f['fixture_id']:f for f in p['fresh_fixtures']}
    def fixture_data(fid):
        records={}
        for artifact in fixtures[fid]['artifacts']:
            data=corpus.read(p['publication_prefix']+artifact['sealed_relative_path']);require(sha(data)==artifact['sha256'] and len(data)==artifact['bytes'],'Admitted corpus changed')
            if artifact['role'] in ('expected','reference','annotations'):records[artifact['role']]=load(data)
        return records['expected'],records['reference'],records['annotations']
    prefix=safe(spec['run_prefix']);require(prefix.startswith(('docs/evidence/WP-0011/','docs/reviews/WP-0011/')),'Only immutable WP-0011 published evidence accepted')
    paths=pub.all_under(prefix)
    def read(path):return pub.read(prefix+'/'+safe(path))
    plan=load(read('plan.json'));require(plan['authority_commit']==spec['authority'] and plan['release_path']==spec['release_path'],'Plan authority mismatch')
    copied,copyinputs=bound(spec['run_copy_manifest']);proofs.extend(copyinputs)
    copycheck=verify_manifest(read,[x[len(prefix)+1:] for x in paths],copied)
    publication_check=verify_publication_inventory(spec['publication_inventory'],spec['publication'])
    proof_receipts=[]
    require({'supervisor_tool_exit','lease_return','post_identity'}<={x.get('role') for x in spec['runtime_receipts']},'Complete runtime proof roles required')
    for binding in spec['runtime_receipts']:
        receipt,inputs=bound(binding);proofs.extend(inputs);proof_receipts.append({'binding':binding,'receipt':receipt})
    require(proof_receipts,'Supervisor/tool and lease-return proofs must be supplied')
    scores=load(pub.read(spec['scores_path']))
    result=inspect_run(read,p,r,spec['owner'],fixture_data,scores)
    result['public']['copy_inventory']=copycheck;result['public']['publication_inventory']=publication_check
    result['public']['bound_runtime_receipts']=proof_receipts
    result['public']['separate_human_proof_review_required']='Independently inspect actual supervisor-tool exit/start/end versus lease, returned-owner receipt, process absence and post model/notice equality. Bound receipt content is retained without guessing its schema or treating a child exit as supervisor success.'
    result['public']['input_inventory']=[*pub.inputs.values(),*authority.inputs.values(),*corpus.inputs.values(),*proofs]
    result['public']['publication_binding']=spec
    return result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--author-spec',required=True,type=Path);ap.add_argument('--reviewer-spec',type=Path);ap.add_argument('--out',required=True,type=Path);args=ap.parse_args()
    output=args.out.resolve();output.relative_to(OWN);require(not output.exists(),'Never overwrite review evidence')
    require(git('rev-parse','HEAD:qualification/coverage_v1').decode().strip()==TREE,'Current reviewed source changed')
    require(sha((ROOT/'qualification/coverage_v1/protocol.json').read_bytes())==PROTOCOL,'Current protocol changed')
    report={'status':'FAILED','helper_head':git('rev-parse','HEAD').decode().strip(),'source_inventory':source_inventory(),'specs':[]}
    try:
        for path in [args.author_spec,*([args.reviewer_spec] if args.reviewer_spec else [])]:
            data=path.read_bytes();report['specs'].append({'path':str(path),'bytes':len(data),'sha256':sha(data)})
        a=audit_published(load(args.author_spec.read_bytes()));report['author']=a['public']
        if args.reviewer_spec:
            b=audit_published(load(args.reviewer_spec.read_bytes()));report['reviewer']=b['public'];report['sentinel_comparison']=compare_sentinel(a,b)
        report['status']='AUDITED';returncode=0
    except Exception:
        report['failure']=traceback.format_exc();returncode=1
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x',encoding='utf-8',newline='\n') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps({'status':report['status'],'output':str(output)}));return returncode

if __name__=='__main__':raise SystemExit(main())
