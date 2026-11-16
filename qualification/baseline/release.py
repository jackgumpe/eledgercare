"""Exact coordinator release binding and finite schedule; no runtime imports."""
import datetime,json,re,subprocess,os
from pathlib import Path
from corpus import ROOT,load_json,sha
HERE=Path(__file__).resolve().parent
REVIEW_PATH='docs/agent-reports/eld-baseline-reviewer/WP-0007/003_2026-11-16_review_eld-baseline-reviewer.md'

def git(*args):return subprocess.check_output([os.environ.get('Q0_GIT_EXECUTABLE','git'),*args],cwd=ROOT)
def protocol():return load_json(HERE/'protocol.json')
def source_tree(revision='HEAD'):return git('rev-parse',revision+':qualification/baseline').decode().strip()
def schedule(p,split,sentinels=None):
    if split not in ('dev','eval_holdout'):raise ValueError('Unknown split')
    measured=[f for f in p['fixtures'] if f['split']==split]
    if sentinels is not None:measured=[f for f in measured if f['fixture_id'] in sentinels]
    return [{'fixture_id':f,'kind':'warmup','excluded':True} for f in p['warmups']]+[{'fixture_id':f['fixture_id'],'kind':'measured','excluded':False} for f in measured]

def validate_release(r,p,split,owner,*,tree,now=None):
    now=now or datetime.datetime.now(datetime.timezone.utc)
    required={'schema','owner','source_commit','executing_head','source_tree','protocol_sha256','mapping_sha256','lock_sha256','accepted_review_commit','accepted_review_path','split','runtime_root','lease_id','gpu_uuid','expires_utc','allow_test_content','sentinels','observed_gpu_state','torchvision_local_sha256_TOFU_accepted'}
    if not required<=r.keys():raise PermissionError('Incomplete coordinator release')
    for k in ('source_commit','executing_head','source_tree','accepted_review_commit'):
        if not re.fullmatch('[0-9a-f]{40}',r[k]):raise PermissionError('Invalid revision '+k)
    if r['accepted_review_path']!=REVIEW_PATH:raise PermissionError('Wrong independent review report')
    if r['schema']!='eld-baseline-release/1' or owner not in ('author','reviewer') or r['owner']!=owner or r['split']!=split:raise PermissionError('Release owner/split mismatch')
    if r['source_tree']!=tree:raise PermissionError('Source tree mismatch')
    for k,path in [('protocol_sha256',HERE/'protocol.json'),('mapping_sha256',HERE/'mapping.json'),('lock_sha256',ROOT/p['dependency_lock_path'])]:
        if r[k]!=sha(path.read_bytes()):raise PermissionError('Release digest mismatch '+k)
    if r['runtime_root']!=p['runtime_roots'][owner] or r['gpu_uuid']!=p['gpu']['uuid'] or not r['lease_id'] or not r['observed_gpu_state']:raise PermissionError('Resource/lease binding missing')
    if r['torchvision_local_sha256_TOFU_accepted'] is not True:raise PermissionError('TOFU exception not accepted')
    expiry=datetime.datetime.fromisoformat(r['expires_utc'].replace('Z','+00:00'))
    if expiry.tzinfo is None or expiry<=now:raise PermissionError('Expired release')
    if split=='eval_holdout' and r['allow_test_content'] is not True:raise PermissionError('Test access held')
    ids={f['fixture_id']:f for f in p['fixtures']};sent=r['sentinels']
    if len(sent)!=len(set(sent)) or not all(x in ids for x in sent):raise PermissionError('Bad sentinel IDs')
    chosen=[ids[x] for x in sent]
    if not (any(f['page_count']==1 for f in chosen) and any(f['page_count']==3 for f in chosen) and any(f['variant_kind'] in ('v1_raster300','v2_skew','v3_hybrid') for f in chosen)):
        raise PermissionError('Reviewer sentinel categories missing')
    return r

def read_release(authority,path,split,owner):
    if not authority or not re.fullmatch('[0-9a-f]{40}',authority):raise PermissionError('Exact coordinator authority commit required')
    if not path or not path.startswith('docs/coordination/WP-0007/') or '..' in Path(path).parts:raise PermissionError('Coordinator-owned release path required')
    r=json.loads(git('show',authority+':'+path));p=protocol()
    validate_release(r,p,split,owner,tree=source_tree())
    if r['executing_head']!=git('rev-parse','HEAD').decode().strip():raise PermissionError('Executing HEAD mismatch')
    if p['q0_core_tree']!=git('rev-parse','HEAD:qualification/q0/harness/q0harness').decode().strip():raise PermissionError('Accepted Q0 primitives changed')
    if source_tree(r['source_commit'])!=r['source_tree']:raise PermissionError('Source commit/tree disagree')
    # Bind an actual immutable reviewer report object; acceptance is coordinator's reviewed assertion.
    review=git('show',r['accepted_review_commit']+':'+r['accepted_review_path'])
    if not review.strip():raise PermissionError('Empty review')
    for key,pathkey in [('q0_protocol_sha256','q0_protocol_path'),('dependency_lock_sha256','dependency_lock_path'),('model_manifest_sha256','model_manifest_path')]:
        if p[key]!=sha((ROOT/p[pathkey]).read_bytes()):raise PermissionError('Pinned Q0 artifact changed')
    if p['corpus_manifest_sha256']!=sha((ROOT/'evaluation/manifests/corpus-manifest.json').read_bytes()):raise PermissionError('Corpus manifest changed')
    if git('status','--porcelain').strip():raise PermissionError('Runtime requires clean source worktree')
    return r
