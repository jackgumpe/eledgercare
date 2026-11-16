"""Read-only Git-object inventory and preservation audit for the reviewer publication."""
import argparse,hashlib,json,subprocess
from pathlib import Path

OWN=Path(__file__).resolve().parent
ROOT=OWN.parents[4]
BASE='8228bfbebddc132ba5d26b98300f3dc5dda99b5a'
SOURCE='f807e0ac737df4e9e0aeeb96f716afec57f58ff6'
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def object_id(rev,path):return git('rev-parse',rev+':'+path).decode().strip()
def classify(path):
    if path.startswith('docs/reviews/WP-0007/eld-baseline-reviewer/'):return 'reviewer-authored evidence/helper'
    if path.startswith('qualification/baseline/') or path.startswith('docs/evidence/WP-0007/eld-rd-astra/') or path.startswith('docs/agent-reports/eld-rd-astra/WP-0007/'):return 'imported baseline author publication'
    return 'imported coordinator or other attributed publication'
def main():
    p=argparse.ArgumentParser();p.add_argument('--revision',required=True);p.add_argument('--output',required=True);args=p.parse_args()
    # Resolve by tree entries and blob IDs; git show rev:long/path can hit Windows stat limits.
    blobs={}
    for row in git('ls-tree','-rz',args.revision).split(b'\0'):
        if row:
            meta,name=row.split(b'\t',1);blobs[name.decode()]=meta.decode().split()[2]
    entries=[];mismatches=[]
    for line in git('diff','--no-renames','--name-status',BASE,args.revision).decode().splitlines():
        action,path=line.split('\t');data=git('cat-file','blob',blobs[path])
        entries.append({'action':action,'path':path,'attribution':classify(path),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'git_blob':blobs[path]})
        if data!=(ROOT/path).read_bytes():mismatches.append(path)
    evidence=[]
    for manifest in [OWN/'evidence-inventory.json',OWN/'reconciliation/8e227abc-050110/inventory.json']:
        for item in json.loads(manifest.read_text())['entries']:
            data=git('cat-file','blob',blobs[item['path']])
            ok=len(data)==item['bytes'] and hashlib.sha256(data).hexdigest()==item['sha256']
            evidence.append({'path':item['path'],'matches_manifest':ok})
    preserved=[]
    for path in ('qualification/q0','evaluation','research','src','web','workers'):
        preserved.append({'path':path,'base_tree':object_id(BASE,path),'publication_tree':object_id(args.revision,path),'unchanged':object_id(BASE,path)==object_id(args.revision,path)})
    source_tree=object_id(args.revision,'qualification/baseline')
    passed=not mismatches and all(x['matches_manifest'] for x in evidence) and all(x['unchanged'] for x in preserved) and source_tree==object_id(SOURCE,'qualification/baseline')
    result={'base':BASE,'review_evidence_revision':args.revision,'accepted_source':SOURCE,'baseline_tree':source_tree,'passed':passed,'working_tree_mismatches':mismatches,'protected_trees':preserved,'evidence_manifest_checks':evidence,'complete_base_to_evidence_inventory':entries,'post_evidence_metadata':'This audit JSON and the later canonical /003 are excluded from the pinned revision by construction.'}
    with Path(args.output).open('x',encoding='utf-8',newline='\n') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({'passed':passed,'changed_paths':len(entries),'reviewer_paths':sum(x['attribution'].startswith('reviewer') for x in entries),'manifest_entries_checked':len(evidence),'protected_trees':len(preserved)}))
    return int(not passed)
if __name__=='__main__':raise SystemExit(main())
