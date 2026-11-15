import ast,datetime,hashlib,json,pathlib,urllib.request
root=pathlib.Path('qualification/q0/preflight')
now=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
refs={'transformers':'945727948c1143a10ac6f7d811aa58bb0d126b5b','torch':'cf30153c4c131c8164ee7798e5022d810682e2cb'}
files=[('torch','RELEASE.md',['architectures supported for Linux x86 and Windows','13.0.2']),('transformers','src/transformers/dynamic_module_utils.py',['if isinstance(node, ast.Try)','modules_needed = check_imports','if submodule == os.path.basename','get_cached_module_file(']),('transformers','src/transformers/modeling_attn_mask_utils.py',['def _prepare_4d_causal_attention_mask']),('transformers','src/transformers/pytorch_utils.py',['ALL_LAYERNORM_LAYERS','is_torch_greater_or_equal_than_1_13']),('transformers','src/transformers/models/llama/modeling_llama.py',['def apply_rotary_pos_emb','def repeat_kv','class LlamaAttention','class LlamaRotaryEmbedding']),('transformers','src/transformers/cache_utils.py',['class Cache','class DynamicCache','def update','def get_usable_length']),('transformers','src/transformers/utils/import_utils.py',['def is_torch_fx_available','def is_flash_attn_2_available','def is_flash_attn_greater_or_equal_2_10'])]
out=[]
for project,path,patterns in files:
    repo='pytorch/pytorch' if project=='torch' else 'huggingface/transformers'
    url=f'https://raw.githubusercontent.com/{repo}/{refs[project]}/{path}'
    with urllib.request.urlopen(url,timeout=30) as r: data=r.read(2_000_001)
    if len(data)>2_000_000: raise ValueError('too large')
    text=data.decode();lines=text.splitlines();hits=[]
    for pattern in patterns:
        hits.append({'pattern':pattern,'matches':[{'line':i+1,'excerpt':'\n'.join(lines[max(0,i-1):i+8])} for i,l in enumerate(lines) if pattern in l]})
    if path.endswith('.py'): ast.parse(text)
    out.append({'url':url,'revision':refs[project],'retrieved_utc':now(),'size':len(data),'sha256':hashlib.sha256(data).hexdigest(),'git_blob':hashlib.sha1(f'blob {len(data)}\0'.encode()+data).hexdigest(),'selected_source_excerpts':hits})
(root/'source-audit.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print('Retrieved and text-parsed 7 pinned primary sources; no upstream code executed.')
