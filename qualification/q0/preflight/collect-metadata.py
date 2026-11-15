"""Read only small official metadata/text; never fetch a wheel or execute model code."""
import datetime, hashlib, html, json, pathlib, re, urllib.parse, urllib.request
ROOT = pathlib.Path('qualification/q0/preflight')
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def fetch(url, method='GET'):
    req=urllib.request.Request(url, method=method, headers={'User-Agent':'eLedgerCare-Q0-source-preflight'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        headers=dict(resp.headers)
        body=b'' if method=='HEAD' else resp.read(2_000_001)
        if len(body)>2_000_000: raise ValueError('Source/metadata response exceeds 2 MB limit')
        return body, headers, resp.url
records=[]
for package, version in [('torch','2.13.0'),('torchvision','0.28.0')]:
    index='https://download.pytorch.org/whl/cu130/'+package+'/'
    data,_,_=fetch(index)
    wanted=f'{package}-{version}+cu130-cp312-cp312-win_amd64.whl'
    links=[line for line in data.decode().splitlines() if wanted in html.unescape(line)]
    if len(links)!=1: raise ValueError((wanted,len(links)))
    line=links[0]
    href=html.unescape(re.search(r'href="([^"]+)"',line).group(1))
    url,fragment=urllib.parse.urldefrag(href)
    mh=re.search(r'data-core-metadata="sha256=([0-9a-f]+)"',line)
    body,_,_=fetch(url+'.metadata')
    actual=hashlib.sha256(body).hexdigest()
    if mh and actual!=mh.group(1): raise ValueError('Metadata digest mismatch')
    record={'package':package,'version':version+'+cu130','filename':wanted,'index':index,'retrieved_utc':now(),'index_entry':line.strip(),'url':url,'published_wheel_sha256':fragment.removeprefix('sha256=') or None,'metadata_url':url+'.metadata','metadata_sha256':actual,'metadata_hash_matches_index':bool(mh and actual==mh.group(1)),'metadata_text':body.decode()}
    try:
        _,headers,_=fetch(url,'HEAD')
        record['wheel_head']={k:v for k,v in headers.items() if k.lower() in ('content-length','etag','digest','x-amz-meta-sha256','last-modified')}
    except Exception as e: record['head_error']=str(e)
    records.append(record)
(ROOT/'cuda-wheel-metadata.json').write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8')
# Main runtime pins are explicit proposals. Versions and published filenames/digests are validated here.
pins={'transformers':'4.52.1','huggingface-hub':'0.36.0','tokenizers':'0.21.4','safetensors':'0.6.2','pillow':'13.0.0','numpy':'2.2.6','requests':'2.32.5','tqdm':'4.67.1','addict':'2.4.0','einops':'0.8.2','easydict':'1.13','pypdfium2':'5.15.2','psutil':'7.1.3'}
packages=[]
for package,version in pins.items():
    url=f'https://pypi.org/pypi/{package}/{version}/json'
    try:
        data,_,_=fetch(url); obj=json.loads(data)
        files=[]
        for f in obj['urls']:
            name=f['filename']
            if not name.endswith('.whl'): continue
            if ('win_amd64' in name and ('cp312' in name or 'abi3' in name or 'py3-none' in name)) or name.endswith('none-any.whl'):
                files.append({k:f[k] for k in ['filename','url','size','digests','requires_python','yanked']})
        packages.append({'name':package,'version':version,'url':url,'retrieved_utc':now(),'requires_python':obj['info']['requires_python'],'requires_dist':obj['info']['requires_dist'],'license':obj['info']['license'],'license_expression':obj['info'].get('license_expression'),'candidate_wheels':files})
    except Exception as e: packages.append({'name':package,'version':version,'url':url,'error':str(e)})
(ROOT/'package-proposal-metadata.json').write_text(json.dumps(packages,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'cuda_wheels':[{'name':r['filename'],'published_sha256':r['published_wheel_sha256'],'head':r.get('wheel_head'),'head_error':r.get('head_error'),'metadata_hash_matches':r['metadata_hash_matches_index']} for r in records],'packages':[{'name':p['name'],'version':p['version'],'wheels':len(p.get('candidate_wheels',[])),'error':p.get('error')} for p in packages]},indent=2))
