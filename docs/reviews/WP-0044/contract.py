import hashlib
import importlib.util
import json
import os
from pathlib import Path
import site
import sys
import sysconfig
import ctypes

HERE=Path(__file__).resolve().parent
ENV_KEYS='PYTHONHOME PYTHONPATH PYTHONSAFEPATH CUBLAS_WORKSPACE_CONFIG CUDA_VISIBLE_DEVICES'.split()

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def write(path, obj):
    Path(path).write_text(json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False)+'\n', encoding='utf-8', newline='\n')

def module_id(name):
    spec=sys.modules[name].__spec__
    if spec.origin in ('built-in','frozen'):
        return [name,spec.origin]
    path=Path(spec.origin).resolve()
    return [name, str(path), sha(path)]

def projection(prefix, paths, custom, env):
    cfg=prefix/'pyvenv.cfg'
    section=dict((key.strip().lower(),val.strip()) for key,val in
                 (line.split('=',1) for line in cfg.read_text(encoding='utf-8').splitlines() if '=' in line))
    result={'C.pyvenv':sha(cfg), 'C.include_system':section['include-system-site-packages'],
            'C.prefix':str(prefix),
            'C.pth':sorted([[str(p.resolve()),sha(p)] for root in paths for p in root.glob('*.pth')]),
            'C.sitecustomize':custom,
            'C.modules':[module_id(x) for x in ['ctypes','os','sys']]}
    for key in ENV_KEYS:
        result['C.'+key]=env.get(key)
    return result

def worker_config():
    spec=importlib.util.find_spec('sitecustomize')
    custom=None if spec is None else [spec.origin,sha(spec.origin)]
    roots=[Path(p) for p in site.getsitepackages() if p in sys.path]
    return projection(Path(sys.prefix), roots, custom, os.environ)
