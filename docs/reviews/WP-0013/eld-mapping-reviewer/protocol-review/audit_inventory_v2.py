"""Independent Git-object publication audit and reviewer-owned complete inventory."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import traceback

ROOT=Path(__file__).resolve().parents[5];OWN=Path(__file__).resolve().parent
BASE='dc69bbabfb233cb021b3edd5ddb7264119ca081c'
AUTHOR='9b90528f4dbd0ea1ff61c86d0d4040decf178a0a'
DELIVERABLE='a887615dbc609f245683a46f9333bbd22b66f360'
SOURCE='6207daf1dc9cbdd141d083ca2d8d1e7507c63b09'
AUTHOR_BASE='47fbc7612e4a08cf1960ad7ac01bd2843ae645e5'
PREFIX='docs/research/WP-0013/eld-mapping-author/001/'
AUTHOR_WORKTREE=ROOT.parent/'eld-vocabulary-author'
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def sha(data):return hashlib.sha256(data).hexdigest()
def require(value,message):
    if not value:raise AssertionError(message)
def tree(ref):
    result={}
    for row in git('ls-tree','-rz',ref).split(b'\0'):
        if row:
            ident,path=row.split(b'\t',1);result[path.decode()]=ident.decode().split()
    return result
def write(path,data):
    path.resolve().relative_to(OWN);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8',newline='\n') as stream:json.dump(data,stream,indent=2);stream.write('\n')
def object_json(ref,path):return json.loads(git('show',ref+':'+path))
def author_audit(out):
    before=tree(AUTHOR_BASE);after=tree(DELIVERABLE);published=tree(AUTHOR)
    for path,identity in before.items():require(after.get(path)==identity,'Protected author base changed: '+path)
    inv=object_json(AUTHOR,PREFIX+'deliverable-inventory.json');entries=inv['files']
    require(sorted(row['path'] for row in entries)==sorted(set(after)-set(before)),'Incomplete author inventory')
    verified=[]
    for row in entries:
        path=row['path'];data=git('show',DELIVERABLE+':'+path);working=(ROOT/path).read_bytes()
        require(after[path]==[row['mode'],row['type'],row['git_blob']]==published[path],'Published identity changed: '+path)
        require(len(data)==row['committed_bytes'] and sha(data)==row['committed_sha256'],'Inventory committed bytes mismatch: '+path)
        author_working=(AUTHOR_WORKTREE/path).read_bytes()
        require(len(author_working)==row['working_bytes'] and sha(author_working)==row['working_sha256'],'Inventory author working bytes mismatch: '+path)
        require(working==data or working.replace(b'\r\n',b'\n')==data.replace(b'\r\n',b'\n'),'Unexplained reviewer checkout representation: '+path)
        if '/evidence/' in path:require(working==data==author_working,'Evidence byte mismatch: '+path)
        verified.append({'path':path,'git_blob':row['git_blob'],'committed_bytes':len(data),'committed_sha256':sha(data),'author_working_bytes':len(author_working),'author_working_sha256':sha(author_working),'reviewer_working_bytes':len(working),'reviewer_working_sha256':sha(working),'reviewer_equals_committed':data==working,'author_equals_committed':data==author_working})
    require(len(entries)==33 and len(before)==3615,'Unexpected author inventory scope')
    expected_metadata={PREFIX+'deliverable-inventory.json','docs/agent-reports/eld-mapping-author/WP-0013/001_2026-11-17_research_eld-mapping-author.md'}
    require(set(published)-set(after)==expected_metadata,'Unexpected publication additions')
    for path,ident in after.items():require(published.get(path)==ident,'Report publication changes deliverable: '+path)
    out.update(unchanged_author_base_files=len(before),author_deliverable_entries=verified,publication_additions=sorted(expected_metadata))
    attempts=[]
    for name,source,tests in [('attempt-1','66204677ee7c84a13c98bf1702d03640e603745f',25),('attempt-2',SOURCE,26)]:
        pre=PREFIX+'evidence/'+name+'/';summary=object_json(AUTHOR,pre+'summary.json');receipt=object_json(AUTHOR,pre+'execution.json')
        require(summary['source_commit']==source and summary['tests']==tests and summary['result']=='PASS' and summary['historical_documents']==12,'Author summary mismatch')
        require(receipt['source']==source and receipt['exit_code']==0,'Author execution attribution mismatch')
        sources=[]
        for item in object_json(AUTHOR,pre+'source-inventory.json'):
            path=item['path'];data=git('show',source+':'+path)
            require(git('rev-parse',source+':'+path).decode().strip()==item['git_blob'],'Tested source blob mismatch')
            possibilities=[('git',data),('checkout_crlf',data.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n'))]
            matches=[kind for kind,value in possibilities if len(value)==item['bytes'] and sha(value)==item['sha256']]
            require(matches,'Unexplained tested source representation: '+path)
            sources.append({**item,'matching_representations':matches,'git_sha256':sha(data)})
        inputs=[]
        for item in object_json(AUTHOR,pre+'inputs.json'):
            data=(ROOT/item['path']).read_bytes();require(len(data)==item['bytes'] and sha(data)==item['sha256'],'Exposed source input changed')
            inputs.append(item)
        captures=[]
        for name2 in ('execution.json','stdout.txt','stderr.txt'):
            original=AUTHOR_WORKTREE/'.scratch/wp0013-protocol'/name/name2
            data=original.read_bytes();published_data=git('show',AUTHOR+':'+pre+name2)
            require(data==published_data,'Author original capture differs: '+str(original))
            captures.append({'original_absolute':str(original),'published':pre+name2,'bytes':len(data),'sha256':sha(data),'exact_original_bytes':True})
        attempts.append({'attempt':name,'source':source,'summary':summary,'execution_receipt':receipt,'source_inventory':sources,'input_inventory':inputs,'capture_copies':captures})
    out['attempts']=attempts
    delta=git('diff','--name-only','66204677ee7c84a13c98bf1702d03640e603745f',SOURCE,'--','qualification/mapping_v2').decode().splitlines()
    require(delta==['qualification/mapping_v2/protocol/contract.py','qualification/mapping_v2/protocol/tests/test_protocol.py'],'Unexpected correction delta')
    out['early_to_final_source_delta']=delta
    report='docs/agent-reports/eld-mapping-author/WP-0013/001_2026-11-17_research_eld-mapping-author.md'
    links=[]
    for target in re.findall(r'\]\(([^)]+)\)',git('show',AUTHOR+':'+report).decode()):
        if '://' in target:continue
        relative=(ROOT/report).parent.joinpath(target.split('#')[0]).resolve().relative_to(ROOT).as_posix()
        require(relative in published,'Broken author report link: '+relative);links.append(relative)
    out.update(report_links=links,status='PASS',limits='Author capture bytes and receipts are audited; this does not transform author executions into reviewer executions. Independent reviewer phases are separate.')
def own_inventory(out,deliverable):
    require(not git('status','--porcelain').strip(),'Own inventory requires clean committed deliverable')
    before=tree(BASE);after=tree(deliverable)
    for path,ident in before.items():require(after.get(path)==ident,'Preserved review-base path changed: '+path)
    rows=[]
    for path in sorted(set(after)-set(before)):
        require(path.startswith(OWN.relative_to(ROOT).as_posix()+'/'),'Unowned addition: '+path)
        data=git('show',deliverable+':'+path);working=(ROOT/path).read_bytes()
        require(data==working,'Reviewer artifact bytes changed by Git: '+path)
        rows.append({'path':path,'mode':after[path][0],'type':after[path][1],'git_blob':after[path][2],'bytes':len(data),'sha256':sha(data)})
    out.update(status='PASS',base=BASE,deliverable=deliverable,unchanged_base_paths=len(before),added_files=len(rows),files=rows)
def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['author','own']);p.add_argument('--out',type=Path,required=True);p.add_argument('--deliverable');a=p.parse_args()
    out={'schema':'eld-wp13-independent-inventory/1','status':'FAILED','mode':a.mode,'helper_head':git('rev-parse','HEAD').decode().strip(),'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    try:
        if a.mode=='author':author_audit(out)
        else:own_inventory(out,a.deliverable)
    except Exception:out['error']=traceback.format_exc()
    out['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();write(a.out,out)
    print(json.dumps({k:v for k,v in out.items() if k in ('status','mode','unchanged_base_paths','added_files','error')}));return 0 if out['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
