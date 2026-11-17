"""Build the public finite catalog from already exposed WP11 labels only."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
DEST = ROOT / 'qualification/mapping_v2/protocol/catalog.json'
PROFILES = [('WP11-F01', 'work_order'), ('WP11-F02', 'service_invoice'), ('WP11-F03', 'inspection')]


def build():
    baseline_path = 'qualification/baseline/mapping.json'
    baseline = json.loads((ROOT / baseline_path).read_text(encoding='utf-8'))
    inputs = [baseline_path]
    profiles = []
    for family, profile in PROFILES:
        prefix = 'evaluation/coverage_v1/corpus/r1/'
        ep = prefix + 'expected/' + family + '-vocabulary-v0.json'
        ap = prefix + 'annotations/' + family + '-vocabulary-v0.json'
        inputs.extend([ep, ap])
        expected = json.loads((ROOT / ep).read_text(encoding='utf-8'))
        annotations = json.loads((ROOT / ap).read_text(encoding='utf-8'))
        fields = []
        for source in expected['expected_fields'] + expected['expected_absences']:
            fid = source['field_id']
            fields.append({'field_id': fid, 'canonical_labels': [r['label'] for r in baseline['labels'] if r['field_id'] == fid],
                           'aliases': [source['label_printed']], 'provenance': ep,
                           'rationale': 'Exact exposed label for this canonical field; profile context and ambiguity guards remain mandatory.'})
        tables = []
        for source in annotations['tables']:
            old = next(t for t in baseline['tables'] if t['table_id'] == source['table_id'])
            tables.append({'table_id': source['table_id'], 'columns': old['columns'],
                           'canonical_headers': old['headers'], 'alias_headers': source['headers'],
                           'row_key_column': source['row_key_column'], 'provenance': ap,
                           'rationale': 'Exact exposed headers, resolved only as a complete unique schema; no global word replacement.'})
        profiles.append({'profile': profile, 'doc_kind': expected['doc_kind'], 'fields': fields, 'tables': tables})
    return {'schema': 'eld-mapping-v2-catalog/1', 'source': 'Exposed WP11 vocabulary cases; no fresh WP13 content.',
            'matching': {'unicode': 'NFC', 'outer_whitespace': 'strip', 'internal_whitespace': 'exact',
                         'case': 'sensitive', 'label_colon': 'one optional terminal colon; no header colon stripping'},
            'profiles': profiles,
            'inputs': [{'path': p, 'bytes': len((ROOT / p).read_bytes()),
                        'sha256': hashlib.sha256((ROOT / p).read_bytes()).hexdigest()} for p in inputs]}


if __name__ == '__main__':
    DEST.parent.mkdir(parents=True, exist_ok=True)
    with DEST.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(build(), stream, indent=2, ensure_ascii=False)
        stream.write('\n')
