"""Versioned final reconciliation; preserves the initial helper and all failed evidence."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess,sys

ROOT=Path(__file__).resolve().parents[5]
OWN=Path(__file__).resolve().parent
OLD='b95c12d2fd8d71598a1e9c523182cd1a2f3ee121'
NEW='23e023045b335540d830ce01b75be247552a63f1'
TREE='59f66d0d3d9be145a43efcc9258eb260d3ef2f00'
PROTOCOL='f54214cc42307eb955f44f4c6470311f01ff7cf93887ea21d024feaa08a63e42'

def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT).decode().strip()
def blob(revision,path):return subprocess.check_output(['git','show',revision+':'+path],cwd=ROOT)
def load(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(data):return hashlib.sha256(data).hexdigest()

def main():
    assert not git('status','--porcelain'),'Freeze reconciliation helper before execution'
    assert git('rev-parse','HEAD:qualification/mapping_v1')==git('rev-parse',NEW+':qualification/mapping_v1')==TREE
    assert sha((ROOT/'qualification/mapping_v1/protocol.json').read_bytes())==PROTOCOL
    changed=git('diff','--name-only',OLD,NEW,'--','qualification/mapping_v1').splitlines()
    assert changed==['qualification/mapping_v1/protocol.json','qualification/mapping_v1/tests/test_release.py']
    old=json.loads(blob(OLD,changed[0]));new=load(ROOT/changed[0])
    assert {k:v for k,v in old.items() if k!='sentinel_policy'}=={k:v for k,v in new.items() if k!='sentinel_policy'}
    assert new['sentinel_policy']=={'chosen_by':'independent reviewer before result access','required_categories':['multi_page'],'measured_document_count':1,'page_counts':[3],'content_scope':'clean_digital_only','not_covered_categories':['single_page','raster_or_hybrid'],'ids_bound_in_release':True}
    protected_source={}
    for path in git('ls-tree','-r','--name-only',OLD,'--','qualification/mapping_v1').splitlines():
        if path in changed:continue
        assert blob(OLD,path)==blob(NEW,path)==blob('HEAD',path),path
        protected_source[path]=git('rev-parse','HEAD:'+path)
    original_reports=['docs/agent-reports/eld-mapping-author/WP-0009/005_2026-11-16_implementation_eld-mapping-author.md','docs/agent-reports/eld-mapping-reviewer/WP-0009/002_2026-11-16_review_eld-mapping-reviewer.md','docs/agent-reports/eld-mapping-reviewer/WP-0009/004_2026-11-16_review_eld-mapping-reviewer.md']
    preserved=git('ls-tree','-r','--name-only','ee32e819b39918556af28de54d24ef586ea4a297','--','docs/reviews/WP-0009/eld-mapping-reviewer/006').splitlines()+original_reports
    for path in preserved:assert blob('ee32e819b39918556af28de54d24ef586ea4a297',path)==blob('HEAD',path),path
    author=ROOT/'docs/evidence/WP-0009/eld-mapping-author/011/attempt-1'
    previous=load(ROOT/'docs/evidence/WP-0009/eld-mapping-author/005/attempt-2/comparison.json');corrected=load(author/'comparison.json')
    differences=[k for k in previous if previous[k]!=corrected[k]]
    assert differences==['source_commit','source_tree']
    assert corrected['source_commit']==NEW and corrected['source_tree']==TREE
    inputs=load(author/'input-inventory.json')['files']
    for item in inputs:
        data=(ROOT/item['path']).read_bytes();assert len(data)==item['bytes'] and sha(data)==item['sha256'],item['path']
    assert len(inputs)==123
    spec=importlib.util.spec_from_file_location('source006_review',OWN/'review_checks.py');module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    sys.argv=[str(OWN/'review_checks.py'),'--source',NEW,'--out','reconciliation-results.json']
    code=module.main()
    results=load(OWN/'reconciliation-results.json')
    results['reconciliation']={'finding':'F006-01','status':'RESOLVED' if code==0 else 'FAILED','exact_changed_source_paths':changed,'unchanged_mapping_source_blobs':protected_source,'initial_review_and_original_reports_preserved':preserved,'protocol_unchanged_outside_sentinel_policy':True,'author011_comparison_differences':differences,'author011_consumed_inputs_verified':len(inputs),'corrected_author_publication':'50beea530079d9c9c4c6b26eae7ee624a5ad0a4e','initial_review_checkpoint':'ee32e819b39918556af28de54d24ef586ea4a297'}
    (OWN/'reconciliation-results.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps({'reconciliation':results['reconciliation'],'tests_run':results['tests']['run'],'status':results['status']},indent=2))
    return code

if __name__=='__main__':raise SystemExit(main())
