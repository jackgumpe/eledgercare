"""WP-0005 /007 author-only bounded source/metadata collector. No wheel bodies/imports.
Uses already-installed pip's vendored packaging solely for metadata/tag evaluation.
All outputs go under this helper's directory; original /001 evidence stays unchanged.
"""
import ast, datetime, email, hashlib, html, importlib.metadata, json, pathlib, platform, re, subprocess, sys, urllib.parse, urllib.request
from pip._vendor import packaging
from pip._vendor.packaging.markers import default_environment
from pip._vendor.packaging.requirements import Requirement
from pip._vendor.packaging.specifiers import SpecifierSet
from pip._vendor.packaging.tags import sys_tags
from pip._vendor.packaging.utils import canonicalize_name, parse_wheel_filename
ROOT = pathlib.Path(__file__).resolve().parent
MODEL = '0480966938291445591f69f08a13b041c073a96a'
TF = '945727948c1143a10ac6f7d811aa58bb0d126b5b'
PINS = {
 'transformers':'4.52.1','huggingface-hub':'0.36.0','tokenizers':'0.21.4','safetensors':'0.6.2',
 'pillow':'13.0.0','numpy':'2.2.6','requests':'2.32.5','tqdm':'4.67.1','addict':'2.4.0',
 'einops':'0.8.2','easydict':'1.13','pypdfium2':'5.15.2','psutil':'7.1.3',
 'filelock':'3.20.0','typing-extensions':'4.15.0','setuptools':'80.9.0','sympy':'1.14.0',
 'mpmath':'1.3.0','networkx':'3.5','jinja2':'3.1.6','markupsafe':'3.0.3','fsspec':'2025.10.0',
 'packaging':'25.0','pyyaml':'6.0.3','regex':'2025.11.3','charset-normalizer':'3.4.4',
 'idna':'3.11','urllib3':'2.5.0','certifi':'2025.11.12','colorama':'0.4.6'}

def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def digest(data): return hashlib.sha256(data).hexdigest()
def blob(data): return hashlib.sha1(f'blob {len(data)}\0'.encode()+data).hexdigest()
def write(name, obj): (ROOT/name).write_text(json.dumps(obj, indent=2)+'\n', encoding='utf-8', newline='\n')
def fetch(url, method='GET', accept=None):
    # Fail closed if a future edit accidentally tries a wheel/weight payload GET.
    if method!='HEAD' and urllib.parse.urlparse(url).path.endswith(('.whl','.safetensors')): raise ValueError('Payload GET forbidden')
    headers={'User-Agent':'eLedgerCare-WP0005-007-author-source'}
    if accept: headers['Accept']=accept
    with urllib.request.urlopen(urllib.request.Request(url,method=method,headers=headers),timeout=30) as r:
        data=b'' if method=='HEAD' else r.read(2_000_001)
        if len(data)>2_000_000: raise ValueError('Response exceeds 2 MB source/metadata limit')
        receipt={'url':url,'final_url':r.url,'method':method,'retrieved_utc':now(),'size':len(data),'sha256':digest(data),'headers':dict(r.headers)}
    return data,receipt

def sources():
    tree=json.loads(pathlib.Path('research/astra/sources/hf-tree.json').read_text())
    entries={x['path']:x for x in tree}
    out=[]; (ROOT/'sources').mkdir(exist_ok=True)
    for name in ['configuration_deepseek_v2.py','conversation.py','packing_patch.py','tokenizer_config.json','special_tokens_map.json','README.md']:
        data,receipt=fetch(f'https://huggingface.co/baidu/Unlimited-OCR-2/resolve/{MODEL}/{name}')
        expected=entries[name]; assert len(data)==expected['size'] and blob(data)==expected['oid'], name
        target='sources/'+('model-card.md' if name=='README.md' else name)
        (ROOT/target).write_bytes(data)
        record={'path':name,'local_path':target,'revision':MODEL,'git_blob':blob(data),'expected_git_blob':expected['oid'],'receipt':receipt}
        if name.endswith('.py'):
            nodes=ast.walk(ast.parse(data.decode()))
            record['imports']=[{'line':n.lineno,'statement':ast.get_source_segment(data.decode(),n)} for n in nodes if isinstance(n,(ast.Import,ast.ImportFrom))]
        if name.endswith('.json'):
            obj=json.loads(data); record['class_keys']={key:obj.get(key) for key in ['tokenizer_class','auto_map','tokenizer_file','vocab_file','merges_file']}
        out.append(record)
    for name in ['models/auto/tokenization_auto.py','tokenization_utils_fast.py','models/llama/tokenization_llama_fast.py','convert_slow_tokenizer.py','tokenization_utils_base.py','integrations/ggml.py']:
        data,receipt=fetch(f'https://raw.githubusercontent.com/huggingface/transformers/{TF}/src/transformers/{name}')
        target='sources/transformers-'+pathlib.Path(name).name
        (ROOT/target).write_bytes(data); ast.parse(data.decode())
        out.append({'path':name,'local_path':target,'revision':TF,'git_blob':blob(data),'receipt':receipt})
    write('source-closure.json',out)

def cuda():
    out=[]
    for package,version in [('torch','2.13.0'),('torchvision','0.28.0')]:
        wanted=f'{package}-{version}+cu130-cp312-cp312-win_amd64.whl'
        index=f'https://download.pytorch.org/whl/cu130/{package}/'
        data,receipt=fetch(index)
        matches=[line for line in data.decode().splitlines() if wanted in html.unescape(urllib.parse.unquote(line))]
        assert len(matches)==1,(wanted,len(matches)); line=matches[0]
        href=html.unescape(re.search(r'href="([^"]+)"',line).group(1)); url,fragment=urllib.parse.urldefrag(href)
        body,meta_receipt=fetch(url+'.metadata'); msg=email.message_from_bytes(body)
        declared=re.search(r'data-(?:core|dist-info)-metadata="sha256=([0-9a-f]{64})"',line)
        assert declared and declared.group(1)==digest(body)
        _,head=fetch(url,'HEAD')
        out.append({'name':package,'version':version+'+cu130','filename':wanted,'url':url,'sha256':fragment.removeprefix('sha256=') or None,'size':int(head['headers']['Content-Length']),
          'index_entry':line.strip(),'index_receipt':receipt,'metadata_receipt':meta_receipt,'metadata_published_sha256':declared.group(1),'metadata_text':body.decode(),
          'requires_python':msg.get('Requires-Python'),'requires_dist':msg.get_all('Requires-Dist',[]),'head_receipt':head})
    write('cuda-metadata.json',out)
    alt=[]
    for index in ['https://download.pytorch.org/whl/torchvision/','https://download.pytorch.org/whl/cu130/torchvision/']:
        try:
            data,receipt=fetch(index,accept='application/vnd.pypi.simple.v1+json')
            content_type=receipt['headers'].get('Content-Type','')
            if 'json' in content_type:
                obj=json.loads(data); matches=[x for x in obj['files'] if x['filename']==out[1]['filename']]
            else:
                matches=[line.strip() for line in data.decode().splitlines() if out[1]['filename'] in html.unescape(urllib.parse.unquote(line))]
            alt.append({'receipt':receipt,'content_type':content_type,'matches':matches})
        except Exception as exc: alt.append({'index':index,'error':str(exc),'retrieved_utc':now()})
    write('torchvision-alternate-indexes.json',alt)

def packages():
    tags=list(sys_tags()); rank={tag:i for i,tag in enumerate(tags)}
    env=default_environment();env['extra']=''
    assert env['python_full_version']=='3.12.10' and env['platform_machine']=='AMD64' and env['sys_platform']=='win32',env
    records=[]
    for name,version in PINS.items():
        raw,receipt=fetch(f'https://pypi.org/pypi/{name}/{version}/json'); obj=json.loads(raw)
        assert canonicalize_name(obj['info']['name'])==name and obj['info']['version']==version
        assert SpecifierSet(obj['info']['requires_python'] or '').contains(env['python_full_version'])
        choices=[]
        for item in obj['urls']:
            if not item['filename'].endswith('.whl') or item['yanked']: continue
            _,wheelver,_,wtags=parse_wheel_filename(item['filename'])
            assert str(wheelver)==version
            compatible=wtags.intersection(rank)
            if compatible and SpecifierSet(item['requires_python'] or '').contains(env['python_full_version']):
                choices.append((min(rank[t] for t in compatible), item['filename'],item))
        assert choices, name
        item=sorted(choices)[0][2]
        records.append({'name':name,'version':version,'receipt':receipt,'requires_python':obj['info']['requires_python'],'requires_dist':obj['info']['requires_dist'] or [],
           'license_expression':obj['info'].get('license_expression'),'license':obj['info'].get('license'),
           'artifact':{k:item[k] for k in ['filename','url','size','digests','requires_python','yanked']}})
    write('pypi-metadata.json',records)
    cuda_records=json.loads((ROOT/'cuda-metadata.json').read_text()); all_records=records+cuda_records
    versions={canonicalize_name(r['name']):r['version'] for r in all_records}; edges=[];missing=[]
    for parent in all_records:
        for raw in parent['requires_dist']:
            req=Requirement(raw); active=not req.marker or req.marker.evaluate(environment=env)
            edge={'parent':parent['name'],'requirement':raw,'active':active}
            if active:
                assert not req.extras and not req.url, raw
                chosen=versions.get(canonicalize_name(req.name)); edge['selected_version']=chosen
                edge['satisfied']=chosen is not None and req.specifier.contains(chosen)
                if not edge['satisfied']:missing.append(edge)
            edges.append(edge)
    artifacts=[{'name':r['name'],'version':r['version'],'filename':r['artifact']['filename'],'url':r['artifact']['url'],'size':r['artifact']['size'],'sha256':r['artifact']['digests']['sha256'],'hash_kind':'publisher-declared'} for r in records]
    artifacts += [{k:r[k] for k in ['name','version','filename','url','size','sha256']} | {'hash_kind':'publisher-declared' if r['sha256'] else 'UNRESOLVED; future official-origin/local-SHA256 gate'} for r in cuda_records]
    write('metadata-lock.json',{'environment':env,'requested_extras':[],'evaluator':{'python':sys.version,'executable':sys.executable,'pip':importlib.metadata.version('pip'),'vendored_packaging':packaging.__version__},
        'status':'metadata-closure-complete; NOT-installable-until-torchvision-hash' if not missing else 'BLOCKED-metadata-closure',
        'artifacts':artifacts,'total_advertised_bytes':sum(r['size'] for r in artifacts),'edges':edges,'unresolved_edges':missing})
    assert not missing,missing

def main():
    start=now(); sources();cuda();packages()
    outputs=[]
    for path in sorted(ROOT.rglob('*')):
        if path.is_file() and (path.suffix=='.json' or path.parent.name=='sources') and path.name!='collection-receipt.json':
            data=path.read_bytes();outputs.append({'path':str(path.relative_to(ROOT)).replace('\\','/'),'size':len(data),'sha256':digest(data),'git_blob':blob(data)})
    write('collection-receipt.json',{'started_utc':start,'completed_utc':now(),'helper_sha256':digest(pathlib.Path(__file__).read_bytes()),'helper_git_blob':blob(pathlib.Path(__file__).read_bytes()),
      'frozen_helper_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'outputs':outputs,'provenance':'Direct Python UTF-8 JSON write; no PowerShell parse/serialize or manual record mutation. No runtime/model import or payload download.'})
    print('Collected source closure, CUDA/index metadata, 30 pinned PyPI records and exact Windows marker/requirement graph; no wheel/weight GET.')
if __name__=='__main__': main()
