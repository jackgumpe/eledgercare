"""Portable normal scorer for an unlabeled pair of flat evidence maps."""
import argparse
import json
from pathlib import Path

PHASE = {
    'L.image': 'launch', 'I.image': 'image', 'E.launcher': 'launch',
    'E.parent': 'edge', 'E.order': 'edge', 'E.instance': 'edge', 'E.job': 'edge',
    'A.script': 'command', 'A.args': 'command',
    **{'C.' + key: 'configuration' for key in
       ['pyvenv', 'include_system', 'pth', 'sitecustomize', 'PYTHONHOME', 'PYTHONPATH',
        'PYTHONSAFEPATH', 'CUBLAS_WORKSPACE_CONFIG', 'CUDA_VISIBLE_DEVICES', 'prefix', 'modules']},
    'B.writer': 'writer', 'B.seal': 'seal', 'B.protection': 'acquisition',
    'B.direct': 'acquisition', 'B.origin': 'acquisition', 'B.members': 'seal',
    'content.bytes': 'score'
}
COORDS = 'LIEACB'
ORDER = 'launch image edge command configuration writer seal acquisition score'.split()


def encoded(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def detail(key, missing):
    if missing:
        return 'unresolved'
    return {'B.origin': 'wrong_origin', 'B.seal': 'integrity', 'B.members': 'integrity',
            'B.writer': 'unauthorized_writer', 'content.bytes': 'content_mismatch'}.get(key, 'mismatch')


def score(record):
    reference = record['expected']
    observed = record['observed']
    if set(reference) != PHASE.keys() or set(observed) - PHASE.keys():
        raise ValueError('incomplete reference or unknown key')
    values = {}
    diagnostics = []
    for key in PHASE:
        present = key in observed
        values[key] = ('P' if encoded(reference[key]) == encoded(observed[key]) else 'M') if present else 'U'
        if values[key] != 'P':
            src = record.get('sources', {}).get(key)
            phase = (src.get('phase') if isinstance(src, dict) else None) or PHASE[key]
            diagnostics.append(dict(key=key, state=values[key], subtype=detail(key, not present),
                                    phase=phase, source=src))
    coords = {c: min((values[k] for k in PHASE if k.startswith(c+'.')), key='MUP'.index) for c in COORDS}
    custody = min((coords[c] for c in 'LIEAB'), key='MUP'.index)
    phases = [d['phase'] for d in diagnostics]
    # Declared phase order applies to these single-stream capsules. Never sort incomparable clocks.
    earliest = [p for p in phases if p not in ORDER]
    ordered = [p for p in phases if p in ORDER]
    if ordered:
        earliest.append(min(ordered, key=ORDER.index))
    return dict(coordinates=coords, custody=custody, joint=min(custody, coords['C'], key='MUP'.index),
                content=values['content.bytes'], conflict=sorted(k for k,v in values.items() if v=='M'),
                missing=sorted(k for k,v in values.items() if v=='U'), diagnostics=diagnostics,
                earliest=sorted(set(earliest)), atomic=values)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('input', type=Path)
    ns = p.parse_args()
    print(encoded(score(json.loads(ns.input.read_text(encoding='utf-8-sig')))))
