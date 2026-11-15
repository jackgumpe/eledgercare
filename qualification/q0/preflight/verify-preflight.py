"""Offline consistency checks only. Never import torch, Transformers or model code."""
import ast, hashlib, json, pathlib, re
root=pathlib.Path('qualification/q0/preflight')
read=lambda name:json.loads((root/name).read_text(encoding='utf-8-sig'))
p=read('package-proposal-metadata.json'); a=read('proposed-artifacts.json'); c=read('cuda-wheel-metadata.json'); m=read('model-files-proposal.json'); s=read('source-audit.json'); h=read('host-receipt.json')
assert len(p)==len(a)==13
for package in p:
    assert not package.get('error'), package
    assert len(package['candidate_wheels'])==1, package['name']
    w=package['candidate_wheels'][0]
    assert not w['yanked']
    assert re.fullmatch('[0-9a-f]{64}',w['digests']['sha256'])
    match=next(x for x in a if x['name']==package['name'])
    assert match['version']==package['version'] and match['filename']==w['filename'] and match['sha256']==w['digests']['sha256'] and match['size']==w['size']
assert next(x for x in p if x['name']=='pillow')['version']=='13.0.0'
assert len(c)==2
for wheel in c:
    assert hashlib.sha256(wheel['metadata_text'].encode()).hexdigest()==wheel['metadata_sha256']
    assert wheel['metadata_hash_matches_index']
    assert 'cp312-cp312-win_amd64.whl' in wheel['filename']
assert c[0]['published_wheel_sha256']=='2efab1e83604ca628c6d85b9e188c153690980498d1297081a9dad704919303c'
assert c[1]['published_wheel_sha256'] is None  # Preserve unknown; never invent a digest.
assert len(m['objects'])==18 and sum(x['size'] for x in m['objects'])==6699195181==m['total_size_bytes']
assert sum(x['size'] for x in m['objects'] if x['path'].endswith('.safetensors'))==6688305576
assert len(s)==7
assert all(hit['matches'] for src in s for hit in src['selected_source_excerpts'])
assert all(re.fullmatch('[0-9a-f]{64}',src['sha256']) for src in s)
primary_bytes=sum(x['size'] for x in a)+sum(int(x['wheel_head']['Content-Length']) for x in c)
assert primary_bytes==1963004322
assert h['drive']['available_bytes']==69064572928
assert h['drive']['available_bytes']-38*2**30>=20*2**30
assert not pathlib.Path(h['storage_root']).exists(), 'Reserved external storage unexpectedly exists; recheck ownership'
for file in root.glob('*.py'): ast.parse(file.read_text(encoding='utf-8-sig'))
print('PASS: 13 primary PyPI artifact records; 2 metadata payload digests; 18 model object sizes; 7 source audits; primary download sum; 38 GiB peak/20 GiB floor; external root absent; helper syntax. No runtime imports/GPU/wheel downloads.')
