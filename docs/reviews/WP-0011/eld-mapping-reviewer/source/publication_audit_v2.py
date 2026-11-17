"""Exact author publication audit and complete reviewer evidence inventory."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[5]
OWN='docs/reviews/WP-0011/eld-mapping-reviewer/source/'
AUTHOR='docs/research/WP-0011/eld-mapping-author/009/'
SOURCE='253519e07e7d45cf1f5ecb3e03053582f7f7d4cc'
DELIVERABLE='937a79c1e2544d864a03e266d557b34a32adebe6'
PUBLICATION='495e0885ba010c79321bbc1d7ff80c3e632e7eb1'
RECONCILIATION_START='89d9e42921cbc37153839eadb1802899e12b3518'
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def sha(data):return hashlib.sha256(data).hexdigest()
def listing(rev):
    return {x.split(b'\t',1)[1].decode():x.split(b'\t',1)[0].decode() for x in git('ls-tree','-r','-z',rev).split(b'\0') if x}
def obj(rev,path):return git('show',rev+':'+path)
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()

def audit():
    inv=json.loads(obj(PUBLICATION,AUTHOR+'deliverable-inventory.json'))
    assert inv['source_commit']==SOURCE and inv['deliverable_commit']==DELIVERABLE
    base=listing(inv['pre_edit_base']);after=listing(DELIVERABLE);now=listing('HEAD')
    modified={k for k,v in base.items() if after.get(k)!=v};added=set(after)-set(base)
    assert len(modified)==8 and len(added)==19 and set(x['path'] for x in inv['files'])==modified|added
    assert len(base)-len(modified)==inv['unchanged_base_paths']==2806
    representations=[]
    for f in inv['files']:
        data=obj(DELIVERABLE,f['path']);live=(ROOT/f['path']).read_bytes()
        assert len(data)==f['bytes_git'] and sha(data)==f['sha256_git'] and after[f['path']].split()[2]==f['git_blob']
        assert now[f['path']]==after[f['path']]
        if 'before' in f:
            before=obj(inv['pre_edit_base'],f['path']);b=f['before']
            assert len(before)==b['bytes_git'] and sha(before)==b['sha256_git'] and base[f['path']].split()[2]==b['git_blob']
        if data!=live:
            assert data==live.replace(b'\r\n',b'\n'),'Non-newline worktree difference: '+f['path']
            representations.append({'path':f['path'],'committed_sha256':sha(data),'committed_bytes':len(data),'working_sha256':sha(live),'working_bytes':len(live),'difference':'CRLF working / LF committed only; original raw-byte identity is not claimed'})
    for f in inv['additional_public_inputs']:
        data=obj(f['commit'],f['path']);assert len(data)==f['bytes_git'] and sha(data)==f['sha256_git']
    final_inputs=json.loads(obj(PUBLICATION,AUTHOR+'attempt-2/author-suite/input-inventory.json'))
    for f in final_inputs['files']:
        data=(ROOT/f['path']).read_bytes()
        assert len(data)==f['bytes'] and sha(data)==f['sha256'],f['path']
        assert git('hash-object','--',f['path']).decode().strip()==f['git_blob']
    for f in final_inputs['git_objects']:
        data=obj(f['commit'],f['path']);assert len(data)==f['bytes'] and sha(data)==f['sha256']
    initial=json.loads((ROOT/OWN/'initial-inventory.json').read_text(encoding='utf-8'))
    for f in initial['files']:
        data=(ROOT/f['path']).read_bytes();assert len(data)==f['bytes'] and sha(data)==f['sha256']
    final=json.loads(obj(PUBLICATION,AUTHOR+'attempt-2/author-suite/diagnostic-ledger.json'))
    preliminary=json.loads((ROOT/AUTHOR/'attempt-1/author-suite/diagnostic-ledger.json').read_text(encoding='utf-8'))
    for key in ('documents','supplement_separate','reused_reviewed_diagnosis','prior_quantity_counterfactual'):assert final[key]==preliminary[key]
    reproduction=json.loads((ROOT/OWN/'reconciliation-1/historical-reproduction.json').read_text(encoding='utf-8'))
    final_records=final['documents']+final['supplement_separate']
    by_key={(d['fixture_id'],d['anchors']['raw_path']):d for d in final_records}
    # Recovery shares a fixture ID with its original row, so match its separate population.
    for r in reproduction['records']:
        candidates=final['supplement_separate'] if r['population']=='recovery' else final['documents']
        d=next(x for x in candidates if x['fixture_id']==r['fixture_id'])
        assert sha(canonical(d))==r['full_diagnostic_sha256_canonical']
    for k,v in reproduction['summary'].items():assert final['summary'][k]==v
    tree=git('rev-parse','HEAD:qualification/coverage_v1').decode().strip()
    assert tree==inv['coverage_tree']=='6bdab544c9fe26cbf093cc765212db2a2e7a97a5'
    source_changes=git('diff','--name-only',SOURCE,PUBLICATION,'--','qualification/coverage_v1').decode().strip();assert not source_changes
    for path,pin in [('qualification/baseline','deae8e826f4770e880374c68e6a56c8c65b6f8a3'),('qualification/mapping_v1','59f66d0d3d9be145a43efcc9258eb260d3ef2f00'),('qualification/q0/harness/q0harness','fee7218eb233438cce7c583be1527b5c549930f0')]:
        assert git('rev-parse','HEAD:'+path).decode().strip()==pin
    report='docs/agent-reports/eld-mapping-author/WP-0011/009_2026-11-17_research_eld-mapping-author.md'
    assert git('diff','--name-only','0c41d751b163243d335668602cf30f85a128831b',PUBLICATION).decode().splitlines()==[report]
    protected=listing(RECONCILIATION_START);assert all(now.get(k)==v for k,v in protected.items())
    return {'status':'PASS','author_publication':PUBLICATION,'source_commit':SOURCE,'source_tree':tree,'author_deliverable':DELIVERABLE,
            'author_inventory_commit':'0c41d751b163243d335668602cf30f85a128831b','author_inventory_sha256_git':sha(obj(PUBLICATION,AUTHOR+'deliverable-inventory.json')),
            'modified_files':8,'added_deliverable_files':19,'protected_author_base_paths':2806,'author_input_files':len(final_inputs['files']),
            'author_public_input_objects':len(final_inputs['git_objects']),'additional_public_inputs':len(inv['additional_public_inputs']),
            'initial_reviewer_artifacts_preserved':len(initial['files']),'protected_reconciliation_start_paths':len(protected),
            'final_31_diagnostic_objects_equal_independent_reproduction':True,'all_reproduced_summary_fields_equal':True,
            'author_log_representations':representations,'canonical_author_report_sha256_git':sha(obj(PUBLICATION,report)),
            'author_report_only_publication':True,'no_source_change_after_test':True,
            'raw_log_limit':'Author inventory declares committed bytes. Working log CRLF and committed LF differ; no conflicting byte-identical raw-log publication assertion found in reviewed /009 report or execution receipts.'}

def inventory():
    head=git('rev-parse','HEAD').decode().strip();entries=listing(head);files=[]
    for path in sorted(k for k in entries if k.startswith(OWN)):
        data=obj(head,path);assert data==(ROOT/path).read_bytes()
        files.append({'path':path,'git_mode_type_blob':entries[path],'bytes':len(data),'sha256':sha(data),'working_bytes_equal_git':True})
    baseline=listing(RECONCILIATION_START);assert all(entries.get(k)==v for k,v in baseline.items())
    return {'schema':'eld-review-complete-source-evidence-inventory/1','deliverable_commit':head,'reconciliation_start':RECONCILIATION_START,
            'preserved_reconciliation_start_paths':len(baseline),'files':files,
            'scope':'Every committed source-review artifact, including all initial and corrected attempts; this new final inventory and later canonical /002 are subsequent metadata.'}

def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('audit','inventory'));p.add_argument('out');a=p.parse_args()
    assert not git('status','--porcelain').strip(),'Freeze before audit/inventory'
    out=(ROOT/a.out).resolve();out.relative_to(ROOT/OWN);assert not out.exists()
    value=audit() if a.mode=='audit' else inventory()
    with out.open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2);f.write('\n')
    print(json.dumps({'mode':a.mode,'status':'PASS','output':a.out,'sha256':sha(out.read_bytes()),'artifact_count':len(value.get('files',[]))}))
if __name__=='__main__':main()
