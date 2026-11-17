"""Frozen /009 Git-object inventory; prior /001 and imported authority stay unchanged."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[5]
BASE='b3d4da6f9e49e7ebd0e7eb71bb91ff0deb079806'
SOURCE='253519e07e7d45cf1f5ecb3e03053582f7f7d4cc'
MODIFIED={'qualification/coverage_v1/'+x for x in ('README.md','diagnostics.py','protocol.json','runtime.py','scoring.py',
    'tests/test_diagnostics.py','tests/test_release.py','tests/test_runtime.py')}
PREFIX='docs/research/WP-0011/eld-mapping-author/009/'

def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def digest(data):return hashlib.sha256(data).hexdigest()
def entries(rev):
    result={}
    for line in git('ls-tree','-r','-z',rev).split(b'\0'):
        if line:
            meta,path=line.split(b'\t',1);result[path.decode()]=tuple(meta.decode().split())
    return result
def item(rev,path):
    blob=git('rev-parse',rev+':'+path).decode().strip();data=git('cat-file','blob',blob)
    return {'path':path,'git_blob':blob,'bytes_git':len(data),'sha256_git':digest(data)}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--deliverable',required=True);parser.add_argument('--out',required=True);args=parser.parse_args()
    out=(ROOT/args.out).resolve();out.relative_to(ROOT/PREFIX)
    assert not out.exists() and not git('status','--porcelain').strip()
    assert git('rev-parse','HEAD').decode().strip()==args.deliverable
    base,current=entries(BASE),entries(args.deliverable)
    changed={path for path in base if current.get(path)!=base[path]};added=set(current)-set(base)
    assert changed==MODIFIED and all(path.startswith(PREFIX) for path in added)
    tree=git('rev-parse',SOURCE+':qualification/coverage_v1').decode().strip()
    assert tree==git('rev-parse',args.deliverable+':qualification/coverage_v1').decode().strip()
    files=[]
    for path in sorted(changed|added):
        record=item(args.deliverable,path);record['action']='modified' if path in changed else 'added'
        if path in changed:record['before']=item(BASE,path)
        files.append(record)
    inputs=[]
    for commit,path in [('7a99cee83b6077c1e155ebf0cbfb6b3ebb3ad203','docs/kickoffs/WP-0011-eld-mapping-author-correction.md'),
        ('bb7d3df4d2d46af2c7116268254176b1ad1dde26','docs/reviews/WP-0011/eld-mapping-reviewer/source/findings-initial.md'),
        ('bb7d3df4d2d46af2c7116268254176b1ad1dde26','docs/reviews/WP-0011/eld-mapping-reviewer/source/attempt-2/probes.json'),
        ('c23a2f0cff3621f05fe1caa77b170167a2406876','docs/reviews/WP-0011/eld-mapping-reviewer/source/probes_v2.py')]:
        inputs.append({'commit':commit,**item(commit,path)})
    result={'schema':'eld-coverage-correction-inventory/1','pre_edit_base':BASE,'source_commit':SOURCE,'coverage_tree':tree,
        'deliverable_commit':args.deliverable,'helper_frozen_commit':args.deliverable,'modified_paths':len(changed),'added_paths':len(added),
        'unchanged_base_paths':len(base)-len(changed),'files':files,'additional_public_inputs':inputs,
        'historical_inputs':['attempt-1/author-suite/input-inventory.json','attempt-2/author-suite/input-inventory.json'],
        'notes':['All other pre-edit mode/type/blob entries are unchanged, including /001, prior source/corpus/reports and merged authority/reviewer evidence.',
                 'Committed-byte hashes; initial independent failures and both author correction attempts retained.','No fresh content/live observer/model/service activity.']}
    out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('files','additional_public_inputs')},indent=2))

if __name__=='__main__':main()
