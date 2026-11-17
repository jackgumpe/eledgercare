"""CPU-only access to immutable original scoring and read-only public metadata."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BASE = '47fbc7612e4a08cf1960ad7ac01bd2843ae645e5'
PINS = {'qualification/baseline': 'deae8e826f4770e880374c68e6a56c8c65b6f8a3',
        'qualification/mapping_v1': '59f66d0d3d9be145a43efcc9258eb260d3ef2f00',
        'qualification/coverage_v1': '6bdab544c9fe26cbf093cc765212db2a2e7a97a5',
        'qualification/q0': '5ca1507d0fb3f5905c9af1cb358642972e9c15dc'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write('\n')


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def catalog():
    return load(HERE / 'catalog.json')


def catalog_sha():
    return sha((HERE / 'catalog.json').read_bytes())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify_pins():
    for path, expected in PINS.items():
        require(git('rev-parse', 'HEAD:' + path).decode().strip() == expected, 'Protected tree changed: ' + path)
        require(not git('diff', 'HEAD', '--', path).strip(), 'Protected working source changed: ' + path)
    return PINS
