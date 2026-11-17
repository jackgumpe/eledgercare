"""One-time auditable WP11 -> WP13 comparison adaptation; no model or actual run access."""
from pathlib import Path
OWN=Path(__file__).resolve().parent;ROOT=OWN.parents[4]
OLD=ROOT/'docs/reviews/WP-0011/eld-mapping-reviewer/comparison-preparation/compare_published.py'
text=OLD.read_text()
def replace(old,new):
    global text
    assert old in text,old[:100]
    text=text.replace(old,new)
replace('Independent WP11 CPU audit','Independent WP13 CPU audit')
replace('New WP11 diagnostics, finite status validation, manifests and sentinel binding are','New WP13 three-mapper/policy accounting, process identity and sentinel binding are')
replace("SOURCE='253519e07e7d45cf1f5ecb3e03053582f7f7d4cc'","SOURCE='c0a1af638e807803b6014b3a93ecb7f9946ce6e1'")
replace("TREE='6bdab544c9fe26cbf093cc765212db2a2e7a97a5'","TREE='4477104eb2a3c73f496ef451cef9578f54d96518'")
replace("PROTOCOL='03b13a41a0047c827af32e71209933700457a5dfd6d38ec106daed82ef5b9000'","PROTOCOL='46a0d3e7bec0f14a3911eb7365385b7d132db8e8a72c8edb3f030aeeda124ec2'\nCORPUS='373106d94b56e619e2210308ca3bf237b45affc0'\nCORPUS_TREE='af22f632c2b69531f61866ca467c6f04f386df7e'")
replace('from qualification.coverage_v1.release import schedule,validate_release','from qualification.mapping_v2.release import schedule,validate_release')
replace('from qualification.coverage_v1.common import protocol','from qualification.mapping_v2.common import protocol')
replace('from qualification.coverage_v1.diagnostics import diagnose,paired_conditions','from qualification.mapping_v2.mapper import extract_prediction as v2_prediction\nfrom qualification.mapping_v2.protocol.scoring import score_policy,summarize_policy')
replace('from qualification.coverage_v1.contract import validate','from qualification.mapping_v2.protocol.contract import validate')
replace("('qualification/coverage_v1',TREE)","('qualification/mapping_v2',TREE),('qualification/coverage_v1',p['coverage_v1_tree'])")
start=text.index('class GitReader:');end=text.index('\ndef reproduce(',start)
text=text[:start]+'''class GitReader:
    def __init__(self,revision):
        require(isinstance(revision,str) and bool(re.fullmatch('[0-9a-f]{40}',revision)),'Full published revision required')
        self.revision=revision;self.inputs={};self.tree={}
        for row in git('ls-tree','-rz',revision).split(b'\\0'):
            if row:
                identity,path=row.split(b'\\t',1);self.tree[path.decode()]=identity.decode().split()
    def read(self,path):
        path=safe(path)
        if path not in self.tree:raise FileNotFoundError(path)
        identity=self.tree[path];require(identity[0]=='100644' and identity[1]=='blob','Only regular committed evidence files')
        data=git('cat-file','blob',identity[2])
        self.inputs[path]={'commit':self.revision,'path':path,'bytes':len(data),'sha256':sha(data),'git_blob':identity[2]}
        return data
    def all_under(self,prefix):
        prefix=safe(prefix);paths=sorted(x for x in self.tree if x.startswith(prefix+'/'))
        require(paths,'Empty published packet')
        for path in paths:self.read(path)
        return paths

'''+text[end:]
replace("before=unavailable(exc);after=unavailable(exc)","before=unavailable(exc);after=unavailable(exc);new=unavailable(exc)")
replace("before=predict(baseline_prediction);after=predict(extract_prediction)","before=predict(baseline_prediction);after=predict(extract_prediction);new=predict(v2_prediction)")
replace("'predictions':{'b0':before,'mapping_v1':after},'scores':{k:score_document(v,expected,reference,completion) for k,v in [('b0',before),('mapping_v1',after)]}","'predictions':{'b0':before,'mapping_v1':after,'mapping_v2':new},'scores':{k:score_document(v,expected,reference,completion) for k,v in [('b0',before),('mapping_v1',after),('mapping_v2',new)]},'v2_status':'provided_prediction'")
start=text.index('def field_changes(');end=text.index('\ndef inspect_run(',start)
text=text[:start]+'''def field_changes(pair):
    out={}
    metrics={'fields':'credited_exact','normalized_fields':'credited_exact','cells':'credited_exact','normalized_cells':'credited_exact','rows':'exact','expected_absences':'verified_absent'}
    for left,right in [('b0','mapping_v1'),('b0','mapping_v2'),('mapping_v1','mapping_v2')]:
        changes={}
        for metric,credit in metrics.items():
            a=pair['scores'][left][metric]['details'];b=pair['scores'][right][metric]['details']
            require(len(a)==len(b),'Paired denominator changed')
            changes[metric]={'gains':[],'losses':[],'other_changes':[]}
            for ordinal,(x,y) in enumerate(zip(a,b)):
                if x==y:continue
                kind='gains' if y[credit] and not x[credit] else 'losses' if x[credit] and not y[credit] else 'other_changes'
                changes[metric][kind].append({'ordinal':ordinal,'before':x,'after':y})
        changes['other_changed_score_objects']=[k for k in pair['scores'][left] if k not in metrics and pair['scores'][left][k]!=pair['scores'][right][k]]
        out[left+'_to_'+right]=changes
    return out

def process_identities(plan,result,worker,preflight,issues):
    def valid(value):
        return isinstance(value,dict) and type(value.get('pid')) is int and value['pid']>0 and type(value.get('creation_filetime_100ns')) is int and value['creation_filetime_100ns']>0 and isinstance(value.get('created_utc'),str) and bool(value['created_utc'])
    require(valid(plan.get('supervisor_identity')),'Supervisor creation identity missing')
    require(plan['supervisor_pid']==plan['supervisor_identity']['pid'] and result.get('supervisor_identity')==plan['supervisor_identity'],'Supervisor creation identity mismatch')
    launcher=result.get('child_launcher_identity')
    if result.get('child_launcher_pid') is not None:
        require(valid(launcher) and launcher['pid']==result['child_launcher_pid'],'Launcher creation identity mismatch')
    for record in (worker,preflight):
        if record is not None:
            require(valid(record.get('worker_identity')) and record['worker_pid']==record['worker_identity']['pid'],'Worker creation identity missing/mismatch')
    if worker and preflight:require(worker['worker_identity']==preflight['worker_identity'],'Worker identity changed across execution')
    if any(x['status']=='completed' for x in result['calls']) and (worker is None or preflight is None):
        issues.append('Completed calls lack complete worker identity evidence')
    return {'supervisor':plan['supervisor_identity'],'launcher':launcher,'worker':None if worker is None else worker.get('worker_identity'),'limit':'Published creation identities only. Actual process ownership/absence requires separate root observations.'}

'''+text[end:]
replace("'eld-coverage-v1-run/1'","'eld-mapping-v2-run/1'")
replace('issues=[];calls=[];records=[];diagnostics=[];material={};stopped=False','issues=[];calls=[];records=[];material={};stopped=False')
replace('expected,reference,annotations=fixture_data(fid);validate(expected,reference,annotations)','expected,reference,policy=fixture_data(fid);validate(expected,reference,policy)')
start=text.index('        diagnostic=diagnose(');end=text.index("    require(not stopped",start)
text=text[:start]+'''        policy_scores={key:score_policy(prediction,expected,reference,policy,status) for key,prediction in pair['predictions'].items()}
        records.append(json_value({'fixture_id':fid,'raw_available':obs is not None and 'raw_output' in obs,**pair,'policy_scores':policy_scores}))
        material[fid]={'available':status=='completed' and tokens is not None,'raw':raw,'tokens':tokens,'scores':pair['scores'],'predictions':pair['predictions'],'policy_scores':json_value(policy_scores),'render':render,'status':status}
'''+text[end:]
replace("for key in ('b0','mapping_v1')","for key in ('b0','mapping_v1','mapping_v2')")
start=text.index('    pairing=paired_conditions(');end=text.index('    if published_scores is not None:',start)
text=text[:start]+'''    policy_summary={key:summarize_policy([row['policy_scores'][key] for row in records]) for key in ('b0','mapping_v1','mapping_v2')} if owner=='author' else {'sentinel_documents':1,'preselected_id':p['reviewer_sentinel'],'limit':'Single prespecified sentinel; not the twelve-author-document population.'}
    expected_packet={'schema':'eld-mapping-v2-paired/1','owner':owner,'executing_head':release['executing_head'],'run_result_sha256':sha(read('run-result.json')),'records':records,
        'historical_summary':summary,'policy_summary':policy_summary,
        'interpretation':'Unchanged end-to-end metrics and accepted separate policy metrics on identical raw outputs. Gains, losses, neutral and unavailable all retained; abstentions are not correct values.'}
'''+text[end:]
replace('Published full prediction/score/diagnostic/denominator packet differs','Published full prediction/score/policy/denominator packet differs')
replace("    changes={x['fixture_id']:field_changes(x) for x in records}","    identities=process_identities(plan,result,worker,preflight,issues)\n    changes={x['fixture_id']:field_changes(x) for x in records}")
replace('Twelve author documents in three families','Twelve author documents in four families')
replace("public['diagnostic_pairing']=pairing;public['complete_reproduced_packet']=expected_packet\n    public['presence_denominator']={k:sum(d['presence_denominator'][k] for d in diagnostics) for k in ('all_expected_slots','eligible_slots','unavailable_slots')}","public['policy_summary']=policy_summary;public['complete_reproduced_packet']=expected_packet;public['process_identities']=identities\n    public['policy_denominators']={key:{metric:sum(row['policy_scores'][key]['metrics'][metric] for row in records) for metric in ('slots','eligible_slots','unavailable_slots','truth_known','truth_ambiguous','truth_unknown')} for key in ('b0','mapping_v1','mapping_v2')}")
replace("fid='WP11-F03-degraded-v0'","fid='WP13-F04-conflict-v0'")
replace("'full_diagnostics_equal':a['diagnostic']==b['diagnostic']","'full_policy_scores_equal':a['policy_scores']==b['policy_scores']")
replace('score/diagnostic equality','score/policy equality')
replace("r['executing_head']+':qualification/coverage_v1'","r['executing_head']+':qualification/mapping_v2'")
replace("('qualification/baseline','comparator_tree'),('qualification/mapping_v1','mapping_v1_tree'),('qualification/q0/harness/q0harness','q0_core_tree')","('qualification/baseline','comparator_tree'),('qualification/mapping_v1','mapping_v1_tree'),('qualification/coverage_v1','coverage_v1_tree'),('qualification/q0/harness/q0harness','q0_core_tree')")
replace("'eld-coverage-v1-unseal/1'","'eld-mapping-v2-unseal/1'")
replace("    corpus=GitReader(r['corpus_commit']);fixtures=","    require(r['corpus_commit']==CORPUS and git('rev-parse',CORPUS+':evaluation/mapping_v2').decode().strip()==CORPUS_TREE,'Exact admitted corpus publication changed')\n    require(r['accepted_protocol_sha256']==p['accepted_protocol_sha256'] and r['accepted_catalog_sha256']==p['accepted_catalog_sha256'],'Accepted contract digests changed')\n    corpus=GitReader(r['corpus_commit']);fixtures=")
replace("p['publication_prefix']+artifact['sealed_relative_path']","safe(artifact['path'])")
replace("('expected','reference','annotations')","('expected','reference','policy')")
replace("records['expected'],records['reference'],records['annotations']","records['expected'],records['reference'],records['policy']")
replace("('docs/evidence/WP-0011/','docs/reviews/WP-0011/')","('docs/evidence/WP-0013/','docs/reviews/WP-0013/')")
replace('Only immutable WP-0011 published evidence accepted','Only immutable WP-0013 published evidence accepted')
replace("'HEAD:qualification/coverage_v1'","'HEAD:qualification/mapping_v2'")
replace("'qualification/coverage_v1/protocol.json'","'qualification/mapping_v2/runtime_protocol.json'")
# Bind all executed-source metadata, but do not consult or rerender actual results during preparation.
replace("    p=protocol();out=[]","    p=protocol();out=[]\n    require(git('rev-parse','HEAD:evaluation/mapping_v2').decode().strip()==CORPUS_TREE,'Published corpus tree changed')\n    for path,key in [('qualification/mapping_v2/protocol/catalog.json','accepted_catalog_sha256'),('qualification/mapping_v2/protocol/protocol.json','accepted_protocol_sha256')]:\n        require(sha((ROOT/path).read_bytes())==p[key],'Accepted contract digest changed')")
with (OWN/'compare_published.py').open('x',encoding='utf-8',newline='\n') as f:f.write(text)
print('Created reviewer-owned comparison adapter from immutable WP11 helper')
