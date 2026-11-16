"""CPU/Git-only correction inventory; never opens fresh artifacts or runtime roots."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[5]
BASE='213bd0d509a8db3518946d64293e7d183dc06d40'
SOURCE='23e023045b335540d830ce01b75be247552a63f1'
OLD_SOURCE='b95c12d2fd8d71598a1e9c523182cd1a2f3ee121'
OLD_REPORT='8942eb843c635ef381da11d9d5ce95524eeb979e'
AUTHORITY='35c095943e71f76b8bfe4f9d6a76e38dd55182e0'
FINDING='93dd59606c39f2cd7dca77c7773ffac0b2eb0e81'
EVIDENCE='docs/evidence/WP-0009/eld-mapping-author/011/attempt-1/'
DOSSIER='docs/research/WP-0009/eld-mapping-author/correction-011/'
SOURCE_PATHS={'qualification/mapping_v1/protocol.json','qualification/mapping_v1/tests/test_release.py'}


def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def obj(rev,path):
    return git('show',rev+':'+path)


def identity(rev,path):
    return git('rev-parse',rev+':'+path).decode().strip()


def blobs(rev):
    result={}
    for row in git('ls-tree','-r',rev).decode().splitlines():
        metadata,path=row.split('\t');result[path]=metadata.split()[2]
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--deliverable',required=True);parser.add_argument('--out',required=True)
    args=parser.parse_args();deliverable=args.deliverable
    assert re.fullmatch('[0-9a-f]{40}',deliverable)
    out=(ROOT/args.out).resolve();out.relative_to(ROOT/DOSSIER)
    assert not out.exists(),'Retain previous verification evidence'
    assert not git('status','--porcelain').strip(),'Freeze deliverable/helper first'
    assert git('rev-parse','HEAD').decode().strip()==deliverable
    for ancestor in (OLD_REPORT,AUTHORITY,SOURCE):git('merge-base','--is-ancestor',ancestor,deliverable)
    source_changes=set(git('diff','--name-only',BASE,SOURCE).decode().splitlines())
    assert source_changes==SOURCE_PATHS
    assert identity(SOURCE,'qualification/mapping_v1')==identity(deliverable,'qualification/mapping_v1')
    before=json.loads(obj(OLD_SOURCE,'qualification/mapping_v1/protocol.json'))
    after=json.loads(obj(SOURCE,'qualification/mapping_v1/protocol.json'))
    old_policy=before.pop('sentinel_policy');new_policy=after.pop('sentinel_policy')
    assert before==after,'Protocol outside sentinel policy changed'
    assert new_policy['required_categories']==['multi_page']
    assert new_policy['measured_document_count']==1 and new_policy['page_counts']==[3]
    assert new_policy['content_scope']=='clean_digital_only'
    assert new_policy['not_covered_categories']==['single_page','raster_or_hybrid']
    before_blobs=blobs(BASE);after_blobs=blobs(deliverable)
    protected=[p for p in before_blobs if p not in SOURCE_PATHS]
    protected_records=[]
    for path in protected:
        before_blob=before_blobs[path];after_blob=after_blobs[path]
        assert before_blob==after_blob,path
        protected_records.append({'path':path,'git_blob':after_blob})
    for name in ('mapper.py','scoring.py','runtime.py','release.py','run_checks.py'):
        path='qualification/mapping_v1/'+name
        assert identity(OLD_SOURCE,path)==identity(SOURCE,path)
    previous=json.loads(obj(OLD_REPORT,'docs/evidence/WP-0009/eld-mapping-author/005/attempt-2/comparison.json'))
    current=json.loads(obj(deliverable,EVIDENCE+'comparison.json'))
    for payload in (previous,current):
        payload.pop('source_commit');payload.pop('source_tree')
    assert previous==current,'Regression differs from /005 beyond source identity'
    tests=json.loads(obj(deliverable,EVIDENCE+'tests.json'))
    assert tests=={'executing_head':SOURCE,'tests_run':23,'failures':0,'errors':0,'skipped':0}
    inputs=json.loads(obj(deliverable,EVIDENCE+'input-inventory.json'))
    assert inputs['source_commit']==SOURCE and len(inputs['files'])==123
    for entry in inputs['files']:
        data=(ROOT/entry['path']).read_bytes()
        assert len(data)==entry['bytes'] and digest(data)==entry['sha256'],entry['path']
        assert identity(SOURCE,entry['path'])==entry['git_blob'],entry['path']
    changes=[]
    for line in git('diff','--name-status',BASE,deliverable).decode().splitlines():
        action,path=line.split('\t')
        assert (action=='M' and path in SOURCE_PATHS) or (action=='A' and (path.startswith(EVIDENCE) or path.startswith(DOSSIER))),line
        published=obj(deliverable,path);worktree=(ROOT/path).read_bytes()
        changes.append({'action':action,'path':path,'git_blob':identity(deliverable,path),
                        'published_bytes':len(published),'published_sha256':digest(published),
                        'worktree_bytes':len(worktree),'worktree_sha256':digest(worktree)})
    assert len(changes)==11
    result={'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'initial_005':OLD_REPORT,'authority':AUTHORITY,'work_base':BASE,'finding':FINDING,
            'source_helper':SOURCE,'source_tree':identity(SOURCE,'qualification/mapping_v1'),
            'protocol_sha256':digest(obj(SOURCE,'qualification/mapping_v1/protocol.json')),
            'deliverable':deliverable,'verification_helper_commit':deliverable,
            'old_sentinel_policy':old_policy,'corrected_sentinel_policy':new_policy,
            'checks':{'only_two_source_paths_changed':True,'all_other_protocol_content_identical':True,
                      'all_other_work_base_files_identical':True,'protected_path_count':len(protected),
                      'critical_005_source_blobs_identical':True,'entire_005_comparison_identical_except_source_identity':True,
                      'tests':tests,'input_hashes_verified':123,'changed_file_count':len(changes)},
            'changed_files':changes,'protected_files':protected_records}
    out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({'deliverable':deliverable,'checks':result['checks']},indent=2))


if __name__=='__main__':main()
