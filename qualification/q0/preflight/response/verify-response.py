"""Author-only offline checks for frozen /007 candidate; no host/root/network checks."""
import ast, email, hashlib, json, pathlib, subprocess
from pip._vendor.packaging.markers import default_environment
from pip._vendor.packaging.requirements import Requirement
from pip._vendor.packaging.specifiers import SpecifierSet
from pip._vendor.packaging.tags import sys_tags
from pip._vendor.packaging.utils import canonicalize_name, parse_wheel_filename
R=pathlib.Path(__file__).resolve().parent
read=lambda p:json.loads((R/p).read_text(encoding='utf-8'))
sha=lambda b:hashlib.sha256(b).hexdigest()
blob=lambda b:hashlib.sha1(f'blob {len(b)}\0'.encode()+b).hexdigest()
receipt=read('collection-receipt.json')
helper=(R/'collect-response.py').read_bytes()
assert sha(helper)==receipt['helper_sha256'] and blob(helper)==receipt['helper_git_blob']
committed=subprocess.check_output(['git','show',receipt['frozen_helper_commit']+':qualification/q0/preflight/response/collect-response.py'])
assert committed==helper, 'Helper bytes differ from frozen producer commit'
for rec in receipt['outputs']:
    data=(R/rec['path']).read_bytes()
    committed_output=subprocess.check_output(['git','show','HEAD:qualification/q0/preflight/response/'+rec['path']])
    assert committed_output==data, 'Committed output bytes differ: '+rec['path']
    assert len(data)==rec['size'] and sha(data)==rec['sha256'] and blob(data)==rec['git_blob'],rec['path']
sources=read('source-closure.json');assert len(sources)==12
for rec in sources:
    data=(R/rec['local_path']).read_bytes()
    assert len(data)==rec['receipt']['size'] and sha(data)==rec['receipt']['sha256'] and blob(data)==rec['git_blob']
    if 'expected_git_blob' in rec:assert rec['git_blob']==rec['expected_git_blob']
    if rec['path'].endswith('.py'):ast.parse(data.decode())
config=read('sources/tokenizer_config.json')
assert config['tokenizer_class']=='LlamaTokenizerFast' and 'auto_map' not in config
assert config['add_prefix_space'] is None and config.get('from_slow',False) is False
assert config.get('fast_tokenizer_files') is None and config['legacy'] is True
lock=read('metadata-lock.json');env=default_environment();env['extra']=''
assert lock['environment']==env and env['platform_machine']=='AMD64'
assert len(lock['artifacts'])==32 and not lock['unresolved_edges']
assert sum(a['size'] for a in lock['artifacts'])==1974477651==lock['total_advertised_bytes']
versions={a['name']:a['version'] for a in lock['artifacts']}
for edge in lock['edges']:
    req=Requirement(edge['requirement']);active=not req.marker or req.marker.evaluate(env)
    assert active==edge['active']
    if active:assert req.specifier.contains(versions[canonicalize_name(req.name)]) and edge['satisfied']
xet=[e for e in lock['edges'] if e['parent']=='huggingface-hub' and e['requirement'].startswith('hf-xet') and 'platform_machine' in e['requirement']]
assert len(xet)==1 and xet[0]['active'] is False
assert not {'hf-xet','triton','sentencepiece','protobuf','tiktoken','gguf'} & versions.keys()
for a in lock['artifacts']:
    assert parse_wheel_filename(a['filename'])[3].intersection(sys_tags())
    if a['name']=='torchvision':assert a['sha256'] is None
    else:assert len(a['sha256'])==64
prior=json.loads((R.parent/'proposed-artifacts.json').read_text())
for old in prior:
    new=next(a for a in lock['artifacts'] if a['name']==old['name'])
    assert all(new[k]==old[k] for k in ['version','filename','sha256','size']),old['name']
for rec in read('cuda-metadata.json'):
    body=rec['metadata_text'].encode();assert sha(body)==rec['metadata_published_sha256']==rec['metadata_receipt']['sha256']
    assert email.message_from_bytes(body).get_all('Requires-Dist',[])==rec['requires_dist']
for rec in read('pypi-metadata.json'):
    assert rec['receipt']['retrieved_utc'].endswith('+00:00')
    assert SpecifierSet(rec['requires_python'] or '').contains(env['python_full_version'])
for name in ['collect-response.py','verify-response.py']:ast.parse((R/name).read_text(encoding='utf-8-sig'))
print('PASS author-only: exact frozen producer/output bytes; 12 source identities; tokenizer flags; 32-artifact marker closure; hf-xet excluded on AMD64; prior 13 artifact identities unchanged; CUDA metadata hashes; no invented torchvision hash. No runtime/root/network/GPU checks.')
