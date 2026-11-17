"""Independent author artifact audit and complete owned reviewer inventory."""
import argparse,collections,datetime,importlib.util,json,re,sys,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import review_checks as r
PUB='e4e57231563bb372016ec124c68fd6018a814a33';DEL='492a7184c833f1077c59d91312d3ea4b895599c6'
BASE='ad7309f2079ed11bc4a63e52567e6a1e5fba1868';PREFIX='docs/research/WP-0013/eld-mapping-author/005/'
AUTHOR=Path('C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/eld-vocabulary-author')
def tree(ref):
    d={}
    for row in r.git('ls-tree','-rz',ref).split(b'\0'):
        if row:
            ident,path=row.split(b'\t',1);d[path.decode()]=ident.decode().split()
    return d
def author(out):
    inv=json.loads(r.git('show',PUB+':'+PREFIX+'deliverable-inventory.json'));before=tree(BASE);after=tree(DEL)
    r.require(all(after.get(p)==v for p,v in before.items()),'Author base changed')
    r.require(set(after)-set(before)=={x['path'] for x in inv['files']},'Author inventory incomplete')
    entries=[]
    for item in inv['files']:
        p=item['path'];raw=r.git('show',DEL+':'+p);working=(r.ROOT/p).read_bytes();original=(AUTHOR/p).read_bytes()
        r.require(after[p][0]==item['mode'] and after[p][2]==item['git_blob'],'Author mode/blob differs')
        r.require(len(raw)==item['committed_bytes'] and r.sha(raw)==item['committed_sha256'],'Author Git bytes differ')
        r.require(len(original)==item['working_bytes'] and r.sha(original)==item['working_sha256'],'Author declared working bytes differ')
        r.require(working.replace(b'\r\n',b'\n')==raw.replace(b'\r\n',b'\n'),'Reviewer representation differs beyond newlines')
        if '/evidence/' in p:r.require(raw==original==working,'Evidence copies not exact')
        entries.append({**item,'reviewer_working_bytes':len(working),'reviewer_working_sha256':r.sha(working),'reviewer_bytes_equal_git':working==raw})
    inputs=r.load(PREFIX+'evidence/attempt-1/inputs.json')
    for item in inputs['files']:
        p=item['path'];r.require(not p.startswith('evaluation/mapping_v2/'),'Private/fresh input unexpectedly declared')
        raw=(AUTHOR/p).read_bytes()
        r.require(len(raw)==item['bytes'] and r.sha(raw)==item['sha256'],'Original input bytes differ')
        r.require(r.git('hash-object','--',p).decode().strip()==item['git_blob'],'Input Git identity differs')
    for item in inputs['public_git_objects']:
        data=r.git('show',item['commit']+':'+item['path']);r.require(len(data)==item['bytes'] and r.sha(data)==item['sha256'],'Public object differs')
    captures=[]
    for item in inv['original_capture_copies']:
        original=(AUTHOR/item['original']).read_bytes();published=(r.ROOT/item['published']).read_bytes()
        r.require(original==published and r.sha(original)==item['sha256'] and len(original)==item['bytes'],'Original tool capture differs')
        captures.append(item)
    ledger=r.load(PREFIX+'evidence/loss-ledger.json');hist=r.load('docs/reviews/WP-0013/eld-mapping-reviewer/source-review/attempt-1/history/result.json')
    expected=[x for x in hist['changed_slots'] if x['direction']=='loss' and x['metric'] in ('fields','expected_absences')]
    r.require(len(expected)==len(ledger['losses'])==38,'Loss inventory incomplete')
    reasons=collections.Counter()
    for loss in ledger['losses']:
        matches=[x for x in expected if x['fixture_id']==loss['fixture_id'] and x['metric']==loss['metric'] and x['before']==loss['before'] and x['after']==loss['after']]
        r.require(len(matches)==1 and loss['decision'] in matches[0]['v2_decisions'],'Loss not independently reproduced')
        r.require(loss['decision']['action']=='abstain','Loss was not withholding');reasons[(loss['metric'],loss['decision']['reason'])]+=1
    # Re-execute the immutable public /002 reference probes independently.
    oldpath=r.ROOT/'docs/reviews/WP-0013/eld-mapping-reviewer/protocol-review/review_checks.py'
    spec=importlib.util.spec_from_file_location('old_independent_reference_review',oldpath);old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    result={};old.probes(result);r.require(result['status']=='PASS' and len(result['checks'])==35,'Original reference probes failed')
    out['public_reference_probes']=result
    from qualification.mapping_v2.protocol.scoring import score_policy
    public=r.load(PREFIX+'evidence/attempt-1/actual-public-native-probes.json');pubrows=[]
    for item in public['examples']:
        family,case,version=item['fixture_id'].rsplit('-',2);e,ref,policy,_=r.example(case,family)
        r.require(item['raw']==policy['ideal_native'],'Tiny public example changed')
        comparison=r.scoring.paired(item['raw'],e,ref,'completed')
        scores=score_policy(comparison['predictions']['mapping_v2'],e,ref,policy)
        r.require(comparison==item['comparison'] and scores==item['policy_score'],'Tiny public full object differs')
        pubrows.append({'fixture_id':item['fixture_id'],'comparison_sha256':r.canonical(comparison),'policy_sha256':r.canonical(scores)})
    reportpath='docs/agent-reports/eld-mapping-author/WP-0013/005_2026-11-17_implementation_eld-mapping-author.md'
    r.require(r.git('diff-tree','--no-commit-id','--name-only','-r',PUB).decode().splitlines()==[reportpath],'Author final commit not report-only')
    text=r.git('show',PUB+':'+reportpath).decode();links=re.findall(r'\]\(([^)]+)\)',text);local=[x for x in links if not x.startswith('https://')]
    r.require(all((r.ROOT/reportpath).parent.joinpath(x).resolve().is_file() for x in local),'Broken author report link')
    out.update(status='PASS',publication=PUB,deliverable=DEL,artifacts=entries,unchanged_base_paths=len(before),input_count=len(inputs['files']),public_object_count=len(inputs['public_git_objects']),capture_copies=captures,report_links=len(local),loss_reasons=[{'metric':k[0],'reason':k[1],'count':v} for k,v in reasons.items()],actual_public_native_cases=pubrows)
def own(out,candidate,base):
    r.require(not r.git('status','--porcelain').strip(),'Inventory requires clean candidate')
    r.require(r.git('rev-parse','HEAD').decode().strip()==candidate,'Wrong own candidate')
    before=tree(base);after=tree(candidate);prefix=r.OWN.relative_to(r.ROOT).as_posix()+'/'
    protected={p:v for p,v in before.items() if not p.startswith(prefix)}
    r.require(all(after.get(p)==v for p,v in protected.items()),'Merged review input changed')
    r.require(all(p.startswith(prefix) for p in set(after)-set(before)),'Unowned reviewer addition')
    rows=[]
    for p in sorted(x for x in after if x.startswith(prefix)):
        data=r.git('cat-file','blob',after[p][2]);r.require(data==(r.ROOT/p).read_bytes(),'Owned working/Git bytes differ')
        rows.append({'path':p,'mode':after[p][0],'git_blob':after[p][2],'bytes':len(data),'sha256':r.sha(data)})
    out.update(status='PASS',candidate=candidate,base=base,unchanged_input_paths=len(protected),files=rows,file_count=len(rows),total_bytes=sum(x['bytes'] for x in rows),exclusions=['this later complete inventory','its later actual tool receipt','later canonical report'])
def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['author','own']);p.add_argument('--candidate');p.add_argument('--base');p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    out={'schema':'eld-wp13-independent-source-publication-audit/1','status':'FAIL','mode':a.mode,'helper_head':r.git('rev-parse','HEAD').decode().strip(),'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    try:
        if a.mode=='author':r.pin(out);author(out)
        else:own(out,a.candidate,a.base)
    except BaseException:out['failure']=traceback.format_exc()
    out['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();r.write(a.out,out)
    print(json.dumps({k:out[k] for k in ('status','file_count','unchanged_input_paths','input_count','report_links','failure') if k in out}));return int(out['status']!='PASS')
if __name__=='__main__':raise SystemExit(main())
