"""Immutable final013 publication audit; no live author scratch or model reads."""
import datetime,hashlib,json,posixpath,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[6]
PUB='10a635d2b9292944a54221e72f4c82566bcb464b';PREFIX='docs/research/WP-0013/eld-mapping-author/013/'
CACHE={}
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def sha(data):return hashlib.sha256(data).hexdigest()
def tree(rev):
    if rev not in CACHE:CACHE[rev]={r.split(b'\t',1)[1].decode():r.split(b'\t',1)[0].decode() for r in git('ls-tree','-r','-z',rev).split(b'\0') if r}
    return CACHE[rev]
def blob(rev,path):return git('cat-file','blob',tree(rev)[path].split()[2])
def main():
    out=ROOT/'.scratch/wp0013-reviewer-011-final/publication-attempt-1';out.mkdir(parents=True,exist_ok=False)
    inv=json.loads(blob(PUB,PREFIX+'deliverable-inventory.json'));a,b,p=tree(inv['base']),tree(inv['deliverable']),tree(PUB)
    diff={x for x in set(a)|set(b) if a.get(x)!=b.get(x)};assert diff=={r['path'] for r in inv['files']}
    changed_existing={x for x in diff if x in a}
    assert changed_existing=={'qualification/mapping_v2/runtime.py','qualification/mapping_v2/tests/test_runtime.py'}
    assert all(x.startswith(PREFIX) or x=='qualification/mapping_v2/runtime_git.py' for x in diff-changed_existing)
    for row in inv['files']:
        data=blob(inv['deliverable'],row['path']);assert len(data)==row['bytes_git'] and sha(data)==row['sha256_git']
        assert b[row['path']].split()[2]==row['git_blob'] and p[row['path']]==b[row['path']]
    manifest=json.loads(blob(PUB,PREFIX+'evidence/copy-manifest.json'))
    for row in manifest['copied_files']:
        data=blob(PUB,row['published_path']);assert len(data)==row['bytes'] and sha(data)==row['sha256']
    for row in manifest['input_files']:
        data=blob(row['revision'],row['path']);assert len(data)==row['bytes_git'] and sha(data)==row['sha256_git']
        assert tree(row['revision'])[row['path']].split()[2]==row['git_blob']
    for row in manifest['proof_and_original_source_inputs']:
        data=blob(row['revision'],row['path']);assert len(data)==row['bytes'] and sha(data)==row['sha256']
        assert tree(row['revision'])[row['path']].split()[2]==row['git_blob']
    for row in manifest['external_executables']:
        data=Path(row['path']).read_bytes();assert len(data)==row['bytes'] and sha(data)==row['sha256']
    report='docs/agent-reports/eld-mapping-author/WP-0013/013_2026-11-17_implementation_eld-mapping-author.md'
    links=[];cross_publication=[]
    for target in re.findall(r'\]\(([^)]+)\)',blob(PUB,report).decode()):
        if '://' in target:continue
        relative=posixpath.normpath(posixpath.join(posixpath.dirname(report),target))
        assert (ROOT/relative).is_file(),relative;links.append(relative)
        if relative not in p:
            assert relative=='docs/reviews/WP-0013/eld-mapping-reviewer/011/findings/F011-01.md'
            assert relative in tree('64a456db726080c124e0188e11b3445c02a1d754');cross_publication.append(relative)
    cases=json.loads(blob(PUB,PREFIX+'evidence/attempt-1/results.json'));units=json.loads(blob(PUB,PREFIX+'evidence/attempt-1/unit-tests.json'))
    value={'result':'PASS','publication':PUB,'source':inv['source'],'source_tree':inv['source_tree'],'deliverable':inv['deliverable'],
        'files_verified':len(diff),'protected_prior_paths':len(a)-len(changed_existing),'copies_verified':len(manifest['copied_files']),
        'input_descriptors_verified':len(manifest['input_files']),'proof_objects_verified':len(manifest['proof_and_original_source_inputs']),
        'executable_hashes_verified':len(manifest['external_executables']),'report_links_verified_in_integrated_worktree':len(links),
        'cross_publication_finding_links':cross_publication,'author_child_count':cases['restricted_children'],
        'author_unit_receipt':units,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'limits':'Author tests are inspected/authenticated, not relabeled reviewer runs. Original-copy claims matched to Git; live author scratch not reread. Independent20 children and3 affected unit methods recorded separately.'}
    with (out/'result.json').open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in value.items() if k!='author_unit_receipt'}))
if __name__=='__main__':main()
