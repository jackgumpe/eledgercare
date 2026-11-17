"""Collect existing comparison captures and inventory; never rerun any scorer."""
from pathlib import Path
import argparse,datetime,hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[6]
OWN=Path(__file__).resolve().parent
BASE='5c24219c79803fffd3c2ccf51b1a602d473d2dea'
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def sha(data):return hashlib.sha256(data).hexdigest()
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2);f.write('\n')
def tree(rev):
    out={}
    for line in git('ls-tree','-rz',rev).split(b'\0'):
        if line:
            meta,path=line.split(b'\t',1);mode,typ,blob=meta.decode().split()
            out[path.decode()]={'mode':mode,'type':typ,'git_blob':blob}
    return out
def collect():
    copies=[]
    for folder,dest in [('combined-capture-1','execution'),('comparison-specs','bindings')]:
        for src in sorted((ROOT/'.scratch/wp0013-reviewer-sentinel'/folder).iterdir()):
            assert src.is_file();data=src.read_bytes();target=OWN/dest/src.name
            target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('xb') as f:f.write(data)
            copies.append({'original':str(src),'published_path':target.relative_to(ROOT).as_posix(),'bytes':len(data),'sha256':sha(data)})
    proofs=[];pub='0bd4ebc26228266fa6f365e7e9bbc6f8dd2845ec';entries=tree(pub)
    for path,name in [('docs/agent-reports/eld-mapping-author/WP-0013/012_2026-11-17_research_eld-mapping-author.md','author012-report.md'),('docs/research/WP-0013/eld-mapping-author/012/README.md','author012-dossier.md')]:
        data=git('cat-file','blob',entries[path]['git_blob']);target=OWN/'bindings'/name
        with target.open('xb') as f:f.write(data)
        proofs.append({'commit':pub,'path':path,'git_blob':entries[path]['git_blob'],'published_path':target.relative_to(ROOT).as_posix(),'bytes':len(data),'sha256':sha(data)})
    r=json.loads((OWN/'comparison.json').read_bytes());assert r['status']=='AUDITED'
    summary={'comparison_sha256':sha((OWN/'comparison.json').read_bytes()),'sentinel_comparison':r['sentinel_comparison'],'populations':{}}
    for owner in ('author','reviewer'):
        a=r[owner];s={'documents':len(a['records']),'completed':a['completed_primary'],'metadata_issues':a['metadata_issues'],'mappers':{},'transitions':{}}
        for mapper in ('b0','mapping_v1','mapping_v2'):
            s['mappers'][mapper]={'metrics':{k:{z:sum(v['scores'][mapper][k][z] for v in a['records']) for z in ('correct','total')} for k in ('fields','cells','rows','expected_absences','normalized_fields','normalized_cells','page_count')},
                'policy':{k:sum(v['policy_scores'][mapper]['metrics'][k] for v in a['records']) for k in a['records'][0]['policy_scores'][mapper]['metrics']},
                'equal_family_means':a['summary'][mapper]['vocabulary_eval']['family_macro']}
        for pair in ('b0_to_mapping_v1','b0_to_mapping_v2','mapping_v1_to_mapping_v2'):
            s['transitions'][pair]={}
            for metric in ('fields','cells','rows','expected_absences','normalized_fields','normalized_cells'):
                g=sum(len(c[pair][metric]['gains']) for c in a['per_item_changes'].values());l=sum(len(c[pair][metric]['losses']) for c in a['per_item_changes'].values())
                total=s['mappers']['b0']['metrics'][metric]['total']
                s['transitions'][pair][metric]={'gains':g,'losses':l,'neutral_credit':total-g-l,'total':total}
        calls=[c for c in a['calls'] if not c['excluded']];times=[c['timing']['external_synchronized_wall_s']['value'] for c in calls]
        s['descriptive_telemetry']={'primary_call_wall_s':times,'sum_s':sum(times),'mean_s':sum(times)/len(times),
            'max_cuda_allocated':max(c['cuda_memory']['max_allocated'] for c in calls),'max_cuda_reserved':max(c['cuda_memory']['max_reserved'] for c in calls),
            'sampled_host_private_peak_lower_bound':max(c['host_memory']['window_peak_private_bytes_lower_bound'] for c in calls),
            'sampled_host_working_set_peak_lower_bound':max(c['host_memory']['window_peak_working_set_lower_bound'] for c in calls)}
        summary['populations'][owner]=s
    write(OWN/'review-summary.json',summary)
    write(OWN/'collection.json',{'original_copies':copies,'git_proof_copies':proofs,'scope':'Copies and arithmetic over already reproduced comparison only; no scoring/model execution.'})
    print(json.dumps({'result':'COLLECTED','original_copies':len(copies),'proof_copies':len(proofs)}))
def inventory():
    assert not git('status','--porcelain').strip()
    end=git('rev-parse','HEAD').decode().strip();a,b=tree(BASE),tree(end)
    assert all(b.get(k)==v for k,v in a.items())
    rows=[]
    for path in sorted(set(b)-set(a)):
        assert path.startswith(OWN.relative_to(ROOT).as_posix()+'/')
        data=git('cat-file','blob',b[path]['git_blob']);assert data==(ROOT/path).read_bytes()
        rows.append({'path':path,**b[path],'bytes_git':len(data),'sha256_git':sha(data)})
    c=json.loads((OWN/'collection.json').read_bytes())
    for row in c['original_copies']+c['git_proof_copies']:
        data=Path(row['original']).read_bytes() if 'original' in row else git('cat-file','blob',row['git_blob'])
        assert sha(data)==row['sha256'] and len(data)==row['bytes']
        assert data==git('cat-file','blob',b[row['published_path']]['git_blob'])
    r=json.loads((OWN/'comparison.json').read_bytes());assert r['status']=='AUDITED'
    descriptors={}
    def visit(v):
        if isinstance(v,dict):
            if {'commit','path','sha256'}<=v.keys():descriptors[(v['commit'],v['path'],v['sha256'])]=v
            for child in v.values():visit(child)
        elif isinstance(v,list):
            for child in v:visit(child)
    visit(r);trees={};blobs={}
    for (rev,path,digest),row in descriptors.items():
        if rev not in trees:trees[rev]=tree(rev)
        entry=trees[rev][path];oid=entry['git_blob']
        if oid not in blobs:blobs[oid]=git('cat-file','blob',oid)
        data=blobs[oid];assert sha(data)==digest
        if 'bytes' in row:assert len(data)==row['bytes']
        if 'git_blob' in row:assert oid==row['git_blob']
    for row in r['source_inventory']:
        data=(ROOT/row['path']).read_bytes()
        if 'git_blob' in row:
            assert b[row['path']]['git_blob']==row['git_blob']
            committed=git('cat-file','blob',row['git_blob'])
            assert len(committed)==row['bytes_git'] and sha(committed)==row['sha256_git']
            assert len(data)==row['bytes_working'] and sha(data)==row['sha256_working']
        else:assert len(data)==row['bytes'] and sha(data)==row['sha256']
    value={'schema':'eld-review-publication-inventory/1','base_commit':BASE,'deliverable_commit':end,'files':rows,
        'protected_prior_paths':len(a),'all_prior_paths_unchanged':True,'comparison_inputs_verified':len(descriptors),
        'source_descriptors_verified':len(r['source_inventory']),'original_copies_verified':len(c['original_copies']),
        'git_proof_copies_verified':len(c['git_proof_copies']),'comparison_sha256':sha((OWN/'comparison.json').read_bytes()),
        'metadata_exclusions':['inventory.json','inventory-receipt.json','canonical008 report'],
        'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    write(OWN/'inventory.json',value)
    print(json.dumps({'result':'PASS','files':len(rows),'bytes':sum(x['bytes_git'] for x in rows),'protected_prior_paths':len(a),
        'comparison_inputs':len(descriptors),'source_descriptors':len(r['source_inventory']),'inventory_sha256':sha((OWN/'inventory.json').read_bytes())}))
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['collect','inventory']);args=ap.parse_args()
    collect() if args.mode=='collect' else inventory()
