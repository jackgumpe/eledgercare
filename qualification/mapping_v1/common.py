"""Explicit read-only access to unchanged B0 modules and repository identities."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASELINE = ROOT/'qualification/baseline'
BASELINE_SOURCE = '522f15f1f6e399c36b9c6c107fc08f51862f1fc1'
BASELINE_TREE = 'deae8e826f4770e880374c68e6a56c8c65b6f8a3'
for name in ('native','score','typed_values','corpus','release','runtime','winjob'):
    loaded = sys.modules.get(name)
    if loaded and Path(loaded.__file__).resolve() != BASELINE/(name+'.py'):
        raise ImportError('Conflicting B0 module: '+name)
sys.path.insert(0,str(BASELINE))
from native import norm, parse_native, extract_prediction as baseline_prediction
from score import score_document, summarize


def sha(data):return hashlib.sha256(data).hexdigest()
def load_json(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def git(*args):return subprocess.check_output([os.environ.get('Q0_GIT_EXECUTABLE','git'),*args],cwd=ROOT)
def tree(revision,path):return git('rev-parse',revision+':'+path).decode().strip()
def protocol():return load_json(HERE/'protocol.json')
def mapping():return load_json(BASELINE/'mapping.json')


def write(path,obj):
    with Path(path).open('x',encoding='utf-8',newline='\n') as f:
        json.dump(obj,f,indent=2,ensure_ascii=False);f.write('\n')


def verify_comparator():
    if tree('HEAD','qualification/baseline') != BASELINE_TREE:
        raise PermissionError('Immutable B0 comparator tree changed')
    for path in ('native.py','score.py','typed_values.py','mapping.json','corpus.py'):
        relative='qualification/baseline/'+path
        if git('hash-object','--',relative).decode().strip()!=tree(BASELINE_SOURCE,relative):
            raise PermissionError('B0 worktree source changed: '+path)


def safe_repo_path(relative):
    if not isinstance(relative,str) or not relative or '\\' in relative:
        raise PermissionError('Repository-relative slash path required')
    p=Path(relative)
    if p.is_absolute() or p.drive or any(x in ('..','.') for x in relative.split('/')):
        raise PermissionError('Unsafe repository path')
    target=(ROOT/p).resolve();target.relative_to(ROOT)
    for parent in (ROOT/p,*(ROOT/p).parents):
        if parent==ROOT.parent:break
        if parent.exists():
            info=parent.stat(follow_symlinks=False)
            if parent.is_symlink() or getattr(info,'st_file_attributes',0)&0x400:
                raise PermissionError('Reparse input path')
    return target
