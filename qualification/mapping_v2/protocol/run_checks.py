"""Freeze-before-check CPU protocol evidence; reads only exposed past material."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from qualification.mapping_v2.protocol.cli import NoModelImports
from qualification.mapping_v2.protocol.common import HERE, BASE, git, load, sha, write, verify_pins, catalog_sha
from qualification.mapping_v2.protocol.contract import validate_catalog
from qualification.mapping_v2.protocol.scoring import original_comparison


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--out', required=True); args = parser.parse_args()
    out = (ROOT / args.out).resolve(); out.relative_to(ROOT / 'docs/research/WP-0013/eld-mapping-author/001')
    if out.exists(): raise FileExistsError('Retain attempts; output must be new')
    if git('status', '--porcelain').strip(): raise RuntimeError('Commit frozen source/helpers before decisive checks')
    start = time.time(); head = git('rev-parse', 'HEAD').decode().strip(); pins = verify_pins()
    out.mkdir(parents=True)
    suite = unittest.defaultTestLoader.discover(str(HERE / 'tests'))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    tests = {'source_commit': head, 'tests': result.testsRun, 'failures': result.failures,
             'errors': result.errors, 'skipped': result.skipped}
    tests = {**tests, 'failures': [[str(t), detail] for t, detail in result.failures],
             'errors': [[str(t), detail] for t, detail in result.errors],
             'skipped': [[str(t), reason] for t, reason in result.skipped]}
    write(out / 'tests.json', tests)
    if not result.wasSuccessful(): return 1
    inputs = {}
    def read(relative):
        data = (ROOT / relative).read_bytes()
        inputs[relative] = {'path': relative, 'bytes': len(data), 'sha256': sha(data),
                            'git_blob': git('hash-object', '--', relative).decode().strip()}
        return data
    def source_json(relative): return json.loads(read(relative))
    c = validate_catalog()
    for source in c['inputs']: read(source['path'])
    builder = ROOT / 'docs/research/WP-0013/eld-mapping-author/001/build_catalog.py'
    spec = importlib.util.spec_from_file_location('public_catalog_builder', builder)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    if module.build() != c: raise AssertionError('Catalog does not reproduce from exposed source labels')
    packet_path = 'docs/evidence/WP-0011/eld-mapping-author/005/attempt-1/scores.json'
    previous = source_json(packet_path); rows = []
    for record in previous['records']:
        fid = record['fixture_id']; corpus = 'evaluation/coverage_v1/corpus/r1/'
        expected = source_json(corpus + 'expected/' + fid + '.json')
        reference = source_json(corpus + 'reference/' + fid + '.json')
        raw_path = 'docs/evidence/WP-0011/eld-mapping-author/005/attempt-1/run/evidence/' + fid + '.measured.raw.txt'
        raw = read(raw_path)
        if sha(raw) != record['raw_sha256']: raise AssertionError('Historical raw identity mismatch')
        current = original_comparison(raw.decode('utf-8'), expected, reference, record['completion'])
        for name in ('b0', 'mapping_v1'):
            if current['scores'][name] != record['scores'][name]: raise AssertionError('Original full score changed: ' + fid + '/' + name)
            if current['predictions'][name] != record['predictions'][name]: raise AssertionError('Original prediction changed: ' + fid + '/' + name)
        rows.append({'fixture_id': fid, 'raw_sha256': sha(raw), 'both_predictions_and_full_scores_equal': True,
                     'full_scores_canonical_json_sha256': sha(json.dumps(current['scores'], sort_keys=True).encode()),
                     'v2_status': current['v2_status']})
    write(out / 'historical-comparison.json', {'historical_packet': packet_path, 'documents': rows,
        'interpretation': 'Exact unchanged B0/v1 predictions and full original scores on all twelve exposed WP11 outcomes. No v2 implementation or performance claim.'})
    write(out / 'inputs.json', list(inputs.values()))
    source_paths = git('ls-files', 'qualification/mapping_v2', 'docs/research/WP-0013/eld-mapping-author/001/build_catalog.py').decode().splitlines()
    write(out / 'source-inventory.json', [{'path': path, 'bytes': len((ROOT / path).read_bytes()),
        'sha256': sha((ROOT / path).read_bytes()), 'git_blob': git('rev-parse', head + ':' + path).decode().strip()} for path in source_paths])
    write(out / 'summary.json', {'source_commit': head, 'base': BASE, 'pins': pins, 'catalog_sha256': catalog_sha(),
        'protocol_sha256': sha((HERE / 'protocol.json').read_bytes()), 'tests': result.testsRun,
        'historical_documents': len(rows), 'historical_mappers': ['b0', 'mapping_v1'],
        'input_files': len(inputs), 'source_files': len(source_paths), 'elapsed_seconds': time.time() - start,
        'v2_implementation': 'held', 'private_corpus_access': False, 'model_import_or_execution': False,
        'failures': 0, 'result': 'PASS'})
    print(json.dumps({'result': 'PASS', 'source_commit': head, 'tests': result.testsRun, 'historical_documents': len(rows), 'inputs': len(inputs)}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
