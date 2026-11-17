"""Reference-side validation only. No alias extraction or native association."""
import math
from qualification.mapping_v1.common import norm, parse_native
from .common import catalog, catalog_sha, load, ROOT, sha, require

CASES = ('supported', 'conflict', 'unsupported')
FAMILIES = {'WP13-F01': 'work_order', 'WP13-F02': 'service_invoice',
            'WP13-F03': 'inspection', 'WP13-F04': 'work_order'}
REASONS = {'supported', 'duplicate_equal', 'conflicting_values', 'header_collision',
           'unsupported_vocabulary', 'missing_structure', 'ambiguous_profile'}
TRUTH = ('known', 'ambiguous', 'unknown')


def target(slot):
    if slot['kind'] == 'cell':
        return ('cell', slot['page_number'], slot['table_id'], slot['row_ordinal'], slot['column_id'])
    return ('field', slot['page_number'], slot['field_id'])


def value_truth(value):
    keys = ('printed_text', 'normalized_value', 'value_type', 'quantity_unit')
    return {key: value[key] for key in keys if key in value}


def box(value):
    return (isinstance(value, list) and len(value) == 4
            and all(type(v) in (int, float) and math.isfinite(v) and v >= 0 for v in value)
            and value[0] < value[2] and value[1] < value[3])


def validate_catalog(value=None):
    c = catalog() if value is None else value
    require(c['schema'] == 'eld-mapping-v2-catalog/1', 'Catalog schema')
    require([p['profile'] for p in c['profiles']] == ['work_order', 'service_invoice', 'inspection'], 'Finite profiles')
    baseline = load(ROOT / 'qualification/baseline/mapping.json')
    for profile in c['profiles']:
        ids = set(); labels = {}
        for field in profile['fields']:
            fid = field['field_id']
            require(fid not in ids, 'Duplicate catalog field'); ids.add(fid)
            require(field['canonical_labels'] == [x['label'] for x in baseline['labels'] if x['field_id'] == fid], 'Canonical labels changed')
            require(field['aliases'] and len(set(field['aliases'])) == len(field['aliases']), 'Finite unique field aliases')
            for label in field['canonical_labels'] + field['aliases']:
                require(isinstance(label, str) and bool(label) and norm(label) == label and not label.endswith(':'), 'Exact label form')
                require(label not in labels, 'Label collision'); labels[label] = fid
        require(len(profile['tables']) == 1, 'One schema per profile')
        for table in profile['tables']:
            old = next(t for t in baseline['tables'] if t['table_id'] == table['table_id'])
            require(table['columns'] == old['columns'] and table['canonical_headers'] == old['headers'], 'Canonical table changed')
            require(len(table['alias_headers']) == len(table['columns']), 'Header alias width')
            require(table['row_key_column'] in table['columns'], 'Row key column')
            headers = {}
            for index, column in enumerate(table['columns']):
                for text in (table['canonical_headers'][index], table['alias_headers'][index]):
                    require(isinstance(text, str) and bool(text) and norm(text) == text, 'Exact header form')
                    require(text not in headers or headers[text] == column, 'Header collision'); headers[text] = column
    for source in c['inputs']:
        data = (ROOT / source['path']).read_bytes()
        require(len(data) == source['bytes'] and sha(data) == source['sha256'], 'Exposed catalog input changed')
    return c


def expected_slots(expected):
    slots = {}
    def add(key, kind, truth, label=None):
        require(key not in slots, 'Duplicate expected opportunity')
        slots[key] = {'kind': kind, 'truth': truth, 'label': label}
    for field in expected['expected_fields']:
        add(('field', field['page_number'], field['field_id']), 'field', value_truth(field), field['label_printed'])
    for field in expected['expected_absences']:
        require(field.get('expected_state') == 'absent_blank', 'Explicit absence meaning')
        add(('field', field['page_number'], field['field_id']), 'absence',
            {'printed_text': '', 'expected_state': 'absent_blank'}, field['label_printed'])
    tables = set()
    for table in expected['expected_tables']:
        require(table['table_id'] not in tables, 'Duplicate expected table'); tables.add(table['table_id'])
        for index, row in enumerate(table['rows']):
            for column, cell in row['cells'].items():
                add(('cell', row['page_number'], table['table_id'], index, column), 'cell', value_truth(cell))
    return slots


def validate(expected, reference, policy):
    c = catalog(); p = policy; e = expected
    require(p['schema'] == 'eld-mapping-v2-policy/1' and p['catalog_sha256'] == catalog_sha(), 'Policy/catalog binding')
    require(p['family_id'] in FAMILIES and p['case'] in CASES, 'Finite family/case')
    require(p['fixture_id'] == p['family_id'] + '-' + p['case'] + '-v0', 'Fixture identity')
    require(p['profile'] == FAMILIES[p['family_id']], 'Reference profile metadata')
    profile = next(x for x in c['profiles'] if x['profile'] == p['profile'])
    require(e['fixture_id'] == p['fixture_id'] and e['family_id'] == p['family_id'], 'Expected identity')
    require(e['doc_kind'] == profile['doc_kind'] and e['split'] == 'vocabulary_eval' and e['variant_kind'] == p['case'], 'Expected metadata')
    require(type(p['page_count']) is int and type(e['page_count']) is int and p['page_count'] == e['page_count'] == 1, 'One page')
    for key in ('expected_fields', 'expected_tables', 'expected_absences', 'page_sentinels', 'expected_adjacent_page_pairs', 'cross_page_links'):
        require(isinstance(e[key], list), 'Expected list ' + key)
    require(not e['page_sentinels'] and not e['expected_adjacent_page_pairs'] and not e['cross_page_links'], 'One-page anchor/link scope')
    require(isinstance(reference['pages'], list) and len(reference['pages']) == 1 and isinstance(reference['pages'][0], str)
            and isinstance(reference['coverage'], dict), 'Reference interface')
    require(isinstance(p['ideal_native'], str) and p['ideal_native'], 'Ideal witness')
    parsed = parse_native(p['ideal_native'])
    require(not parsed['errors'] and len(parsed['pages']) == 1, 'Ideal witness parse')
    require(isinstance(p['tables'], list) and isinstance(p['slots'], list) and p['slots'], 'Policy lists')
    tables = {}; table_rules = {x['table_id']: x for x in profile['tables']}
    expected_tables = {t['table_id']: t for t in e['expected_tables']}
    for table in p['tables']:
        tid = table['table_id']; ids = table['row_ids']
        require(tid in table_rules and tid not in tables, 'Policy table identity')
        require(table['column_ids'] == table_rules[tid]['columns'], 'Canonical policy columns')
        require(isinstance(ids, list) and ids and all(isinstance(v, str) and v for v in ids) and len(set(ids)) == len(ids), 'Unique row IDs')
        require(tid in expected_tables, 'Expected table missing')
        et = expected_tables[tid]
        require(et['column_ids'] == table['column_ids'] and [r['row_id'] for r in et['rows']] == ids, 'Expected row order/columns')
        require(all(r['page_number'] == 1 and set(r['cells']) <= set(table['column_ids']) for r in et['rows']), 'Expected row cells')
        require(all(table_rules[tid]['row_key_column'] in r['cells'] for r in et['rows']), 'Every expected row requires known row-key truth')
        tables[tid] = table
    require(set(expected_tables) == set(tables), 'Complete declared tables')
    known = expected_slots(e); seen = set(); known_seen = set(); cell_seen = set()
    field_rules = {f['field_id']: f for f in profile['fields']}
    for slot in p['slots']:
        require(slot['kind'] in ('field', 'cell', 'absence') and type(slot['page_number']) is int and slot['page_number'] == 1, 'Slot kind/page')
        key = target(slot); require(key not in seen, 'Duplicate policy opportunity'); seen.add(key)
        require(slot['truth_status'] in TRUTH and slot['action'] in ('assign', 'abstain') and slot['reason'] in REASONS, 'Policy enums')
        require((slot['action'] == 'assign') == (slot['reason'] == 'supported'), 'Action/reason disagreement')
        require(slot['action'] != 'assign' or slot['truth_status'] == 'known', 'Assign needs known truth')
        if slot['kind'] == 'cell':
            tid = slot['table_id']; index = slot['row_ordinal']; col = slot['column_id']
            require(tid in tables and type(index) is int and 0 <= index < len(tables[tid]['row_ids']), 'Cell row identity')
            require(slot['row_id'] == tables[tid]['row_ids'][index] and col in tables[tid]['column_ids'], 'Cell row/column identity')
            cell_seen.add(key); rule = table_rules[tid]; ci = rule['columns'].index(col)
            labels = [rule['canonical_headers'][ci], rule['alias_headers'][ci]]
        else:
            require(slot['field_id'] in field_rules, 'Field outside profile catalog')
            rule = field_rules[slot['field_id']]; labels = rule['canonical_labels'] + rule['aliases']
        evidence = slot['evidence']
        require(isinstance(evidence, list) and evidence, 'Source evidence required')
        for item in evidence:
            require(isinstance(item['label_printed'], str) and bool(item['label_printed']) and box(item['label_bbox_pt']), 'Printed label/source box')
            require(item['value_printed'] is None or isinstance(item['value_printed'], str), 'Printed value type')
            require(item['value_bbox_pt'] is None or box(item['value_bbox_pt']), 'Value source box')
        if slot['action'] == 'assign':
            require(all(norm(x['label_printed']).removesuffix(':') in labels for x in evidence), 'Supported label outside catalog')
        if slot['truth_status'] == 'known':
            require(key in known and known[key]['kind'] == slot['kind'] and known[key]['truth'] == slot['truth'], 'Known truth/expected mismatch')
            truth = slot['truth']; require(isinstance(truth['printed_text'], str), 'Printed truth string')
            if slot['kind'] != 'absence':
                require(set(truth) <= {'printed_text', 'normalized_value', 'value_type', 'quantity_unit'} and
                        all(isinstance(truth[k], str) for k in ('printed_text', 'normalized_value', 'value_type')), 'Typed truth structure')
                require('quantity_unit' not in truth or isinstance(truth['quantity_unit'], str) and bool(truth['quantity_unit']), 'Explicit unit metadata')
            if known[key]['label'] is not None:
                require(known[key]['label'] in [x['label_printed'] for x in evidence], 'Expected printed label/evidence mismatch')
            require(truth['printed_text'] in [x['value_printed'] for x in evidence], 'Known value has no source occurrence')
            known_seen.add(key)
        else:
            require(slot['truth'] is None and key not in known, 'Unresolved truth must not invent expected value')
        if slot['reason'] == 'duplicate_equal':
            require(len(evidence) >= 2 and all(isinstance(x['value_printed'], str) for x in evidence)
                    and len({norm(x['value_printed']) for x in evidence}) == 1, 'Duplicate-equal evidence')
        if slot['reason'] == 'conflicting_values':
            require(len({norm(x['value_printed']) for x in evidence if isinstance(x['value_printed'], str)}) >= 2, 'Conflicting-value evidence')
    require(known_seen == set(known), 'All known expected slots must remain in policy')
    all_cells = {('cell', 1, t['table_id'], ri, col) for t in p['tables'] for ri in range(len(t['row_ids'])) for col in t['column_ids']}
    require(cell_seen == all_cells, 'All declared table opportunities required')
    if p['case'] == 'supported':
        require(all(s['action'] == 'assign' for s in p['slots']), 'Supported case policy')
    elif p['case'] == 'conflict':
        require(any(s['reason'] in {'duplicate_equal', 'conflicting_values', 'header_collision'} for s in p['slots']), 'Conflict opportunity required')
    else:
        require(any(s['reason'] == 'unsupported_vocabulary' for s in p['slots']), 'Unsupported opportunity required')
    return {'fixture_id': p['fixture_id'], 'slots': len(p['slots']), 'known': len(known),
            'ambiguous': sum(s['truth_status'] == 'ambiguous' for s in p['slots']),
            'unknown': sum(s['truth_status'] == 'unknown' for s in p['slots']),
            'required_abstentions': sum(s['action'] == 'abstain' for s in p['slots'])}


def validate_family(records):
    require(len(records) == 3, 'Three cases required')
    reports = [validate(*row) for row in records]
    policies = [row[2] for row in records]
    require(len({p['family_id'] for p in policies}) == 1 and {p['case'] for p in policies} == set(CASES), 'Matched family cases')
    require(all(p['tables'] == policies[0]['tables'] for p in policies), 'Family table/row identity changed')
    maps = [{target(s): s for s in p['slots']} for p in policies]
    require(all(set(m) == set(maps[0]) for m in maps), 'Family opportunity universe changed')
    for key in maps[0]:
        rows = [m[key] for m in maps]
        require(len({r['kind'] for r in rows}) == 1, 'Family slot kind changed')
        truths = [r['truth'] for r in rows if r['truth_status'] == 'known']
        require(all(t == truths[0] for t in truths), 'Known family semantics/unit/absence changed')
    return reports
