"""Finite WP-0009 release, admission/unseal and exact immutable source binding.

No filesystem mutation or runtime/model import. Only read_release grants fresh reads.
Root authors future release objects; none is provided or usable by this CPU candidate.
"""
import datetime
import json
import re
from .common import ROOT,HERE,BASELINE_TREE,git,tree,sha,load_json,protocol,safe_repo_path,verify_comparator

SHA1=re.compile(r'[0-9a-f]{40}')
SHA256=re.compile(r'[0-9a-f]{64}')


def require(condition,reason):
    if not condition:raise PermissionError(reason)


def schedule(p,owner):
    require(owner in ('author','reviewer'),'Unknown owner')
    fresh=p['fresh_fixtures']
    require(len(fresh)==4 and len({x['family_id'] for x in fresh})==4 and
            [x['page_count'] for x in fresh]==[1,1,1,3],'Finite reservation counts/order changed')
    require(p['warmups']==['SYN-WO-01-v0-clean','SYN-MP-01-v0-clean'],'Warmup order changed')
    require(p['reviewer_sentinel']==fresh[3]['fixture_id']=='WP09-F04-v0','Preselected sentinel changed')
    measured=fresh if owner=='author' else [fresh[3]]
    return ([{'fixture_id':fid,'kind':'warmup','excluded':True} for fid in p['warmups']]+
            [{'fixture_id':f['fixture_id'],'kind':'measured','excluded':False} for f in measured])


def validate_release(r,p,owner,*,head,source_tree,protocol_digest,clean,now=None,execution=True):
    """Pure envelope validation; object/file evidence is checked by read_release."""
    try:
        required={'schema','owner','source_commit','executing_head','source_tree','protocol_sha256',
                  'comparator_tree','q0_core_tree','reservation_sha256','corpus_commit','runtime_root',
                  'issued_utc','expires_utc','schedule','source_review','admission_review','unseal',
                  'lease','torchvision_local_sha256_TOFU_accepted'}
        require(isinstance(r,dict) and required<=r.keys(),'Incomplete coordinator release')
        require(r['schema']=='eld-mapping-v1-release/1' and owner in ('author','reviewer') and r['owner']==owner,'Release owner/schema mismatch')
        for key in ('source_commit','executing_head','source_tree','corpus_commit'):
            require(isinstance(r[key],str) and SHA1.fullmatch(r[key]),'Invalid full revision: '+key)
        require(r['source_tree']==source_tree and r['executing_head']==head and clean,'Exact clean executing source required')
        require(r['protocol_sha256']==protocol_digest,'Protocol digest mismatch')
        require(r['comparator_tree']==p['comparator_tree']==BASELINE_TREE,'Comparator changed')
        require(r['q0_core_tree']==p['q0_core_tree'],'Q0 changed')
        require(r['reservation_sha256']==p['public_reservation_sha256'],'Reservation changed')
        require(r['runtime_root']==p['runtime_roots'][owner],'Owned runtime root mismatch')
        require(r['schedule']==schedule(p,owner),'Finite schedule mismatch')
        require(r['torchvision_local_sha256_TOFU_accepted'] is True,'TOFU exception not acknowledged')
        for key,pathkey in [('source_review','source_review_path'),('admission_review','admission_review_path')]:
            require(r[key]['path']==p[pathkey],'Wrong independent report route')
        require(r['admission_review']['commit']==p['admission_review_commit'] and
                r['admission_review']['sha256']==p['admission_review_sha256'],'Accepted corpus admission changed')
        for binding in [r['source_review'],r['admission_review'],r['unseal'],*r['lease']['observations']]:
            require(SHA1.fullmatch(binding['commit']) and SHA256.fullmatch(binding['sha256']),'Invalid evidence binding')
            require(isinstance(binding['path'],str) and '\\' not in binding['path'] and '..' not in binding['path'].split('/'),'Invalid evidence path')
        require(r['unseal']['path'].startswith('docs/coordination/WP-0009/'),'Coordinator unseal required')
        lease=r['lease']
        require(lease['id'] and lease['owner']==owner and lease['gpu_uuid']==p['gpu']['uuid'] and
                lease['sole_lease'] is True and lease['scope']=='sole_model_job' and
                len(lease['observations'])>=1,'Sole model-job lease/evidence missing')
        now=now or datetime.datetime.now(datetime.timezone.utc)
        issued=datetime.datetime.fromisoformat(r['issued_utc'].replace('Z','+00:00'))
        expiry=datetime.datetime.fromisoformat(r['expires_utc'].replace('Z','+00:00'))
        require(issued.tzinfo and expiry.tzinfo and 0<(expiry-issued).total_seconds()<=p['guards']['timeouts_s']['session'],'Invalid bounded release lifetime')
        require(issued<=now and (not execution or now<expiry),'Missing, future or expired runtime release')
    except (KeyError,TypeError,ValueError,AttributeError) as exc:
        raise PermissionError('Malformed coordinator release') from exc
    return r


def bound_object(binding):
    data=git('show',binding['commit']+':'+binding['path'])
    require(data.strip() and sha(data)==binding['sha256'],'Immutable evidence digest mismatch')
    return data


def read_release(authority,path,owner,*,execution=True):
    require(isinstance(authority,str) and SHA1.fullmatch(authority),'Exact coordinator authority required')
    require(isinstance(path,str) and path.startswith('docs/coordination/WP-0009/releases/') and
            '\\' not in path and '..' not in path.split('/'),'Coordinator-owned release path required')
    r=json.loads(git('show',authority+':'+path));p=protocol()
    validate_release(r,p,owner,head=git('rev-parse','HEAD').decode().strip(),
                     source_tree=tree('HEAD','qualification/mapping_v1'),protocol_digest=sha((HERE/'protocol.json').read_bytes()),
                     clean=not git('status','--porcelain').strip(),execution=execution)
    verify_comparator()
    require(tree(r['source_commit'],'qualification/mapping_v1')==r['source_tree'],'Source commit/tree mismatch')
    require(tree('HEAD','qualification/q0/harness/q0harness')==p['q0_core_tree'],'Q0 primitives changed')
    for digest,pathkey in [('q0_protocol_sha256','q0_protocol_path'),('dependency_lock_sha256','dependency_lock_path'),('model_manifest_sha256','model_manifest_path')]:
        require(sha((ROOT/p[pathkey]).read_bytes())==p[digest],'Qualified artifact changed: '+pathkey)
    public=git('show',p['public_reservation_commit']+':'+p['public_reservation_path'])
    require(sha(public)==p['public_reservation_sha256'],'Public reservation object changed')
    require(json.loads(public)['fixtures']==p['fresh_fixtures'],'Protocol/reservation matrix mismatch')
    bound_object(r['source_review']);bound_object(r['admission_review'])
    unseal=json.loads(bound_object(r['unseal']))
    require(unseal.get('schema')=='eld-mapping-v1-unseal/1' and unseal.get('allow_content') is True and
            unseal.get('source_commit')==r['source_commit'] and
            unseal.get('source_review_commit')==r['source_review']['commit'] and
            unseal.get('reservation_sha256')==p['public_reservation_sha256'],'Unseal authorization mismatch')
    for observation in r['lease']['observations']:bound_object(observation)
    # Only after accepted source/admission and explicit unseal are authenticated may fresh files be opened.
    for fixture in p['fresh_fixtures']:
        for artifact in fixture['artifacts']:read_artifact(r,p,artifact)
    return r


def read_artifact(r,p,artifact):
    relative=p['publication_prefix']+artifact['sealed_relative_path']
    require(relative.startswith('evaluation/mapping_v1/'),'New corpus namespace required')
    data=safe_repo_path(relative).read_bytes()
    require(len(data)==artifact['bytes'] and sha(data)==artifact['sha256'],'Fresh artifact byte identity mismatch')
    published=git('show',r['corpus_commit']+':'+relative)
    require(published==data,'Published admitted artifact differs from worktree')
    return data


def fixture(p,fid):
    found=[f for f in p['historical_warmups']+p['fresh_fixtures'] if f['fixture_id']==fid]
    require(len(found)==1,'Unknown or duplicate fixture')
    return found[0]


def pdf_bytes(r,p,fx):
    if fx['fixture_id'] in p['warmups']:
        data=safe_repo_path(fx['file_path']).read_bytes()
        require(len(data)==fx['size_bytes'] and sha(data)==fx['sha256'],'Historical warmup PDF changed')
        return data
    return read_artifact(r,p,next(a for a in fx['artifacts'] if a['role']=='pdf'))
