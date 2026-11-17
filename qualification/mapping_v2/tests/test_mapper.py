"""Public tiny native layouts only; no reference/fixture routes enter extraction."""
import copy
import unittest
from qualification.mapping_v1.common import parse_native, mapping
from qualification.mapping_v1.mapper import extract_prediction as v1
from qualification.mapping_v2.mapper import extract_prediction
from qualification.mapping_v2.protocol.common import catalog


def block(text, box=(1, 1, 100, 10), kind='text'):
    return '<BLOCK>' + kind + '[' + ','.join(map(str, box)) + ']<FORK>' + text


def table(rows, box=(10, 100, 900, 900)):
    def cell(value):
        if isinstance(value, tuple): return '<td colspan="' + str(value[1]) + '">' + value[0] + '</td>'
        return '<td>' + value + '</td>'
    return block('<table>' + ''.join('<tr>' + ''.join(cell(v) for v in row) + '</tr>' for row in rows) + '</table>', box, 'table')


def schema(profile=0, aliases=True, rows=None, order=None):
    rule = catalog()['profiles'][profile]['tables'][0]
    headers = rule['alias_headers'] if aliases else rule['canonical_headers']
    values = ['0007'] + ['v' + str(i) for i in range(1, len(headers))]
    rows = [values] if rows is None else rows
    if order is not None:
        headers = [headers[i] for i in order]; rows = [[row[i] for i in order] for row in rows]
    return table([headers, *rows])


def predicted(*blocks):
    return extract_prediction(parse_native('<PAGE>' + ''.join(blocks)))


def values(pred, fid='work_order_id'):
    return [f['value'] for f in pred['fields'] if f['field_id'] == fid]


class MapperTests(unittest.TestCase):
    def test_alias_inline_and_exact_table_bijection(self):
        pred = predicted(block('Repair record: 0002'), schema())
        self.assertEqual(['0002'], values(pred)); self.assertEqual(1, len(pred['tables']))
        self.assertEqual(['part_sku', 'part_desc', 'bin_loc', 'qty_used'], pred['tables'][0]['columns'])

    def test_mixed_headers_and_permuted_columns_keep_native_order(self):
        rule = catalog()['profiles'][0]['tables'][0]
        headers = [rule['alias_headers'][2], rule['canonical_headers'][0], rule['alias_headers'][3], rule['canonical_headers'][1]]
        pred = predicted(block('Repair record 0002'), table([headers, ['B', '0007', '2', 'part']]))
        self.assertEqual(['0002'], values(pred)); self.assertEqual(['bin_loc', 'part_sku', 'qty_used', 'part_desc'], pred['tables'][0]['columns'])
        self.assertEqual(['B', '0007', '2', 'part'], pred['tables'][0]['rows'][0]['values'])

    def test_all_three_catalog_profiles(self):
        for profile in range(3):
            entry = catalog()['profiles'][profile]['fields'][0]
            pred = predicted(block(entry['aliases'][0] + ': 0002'), schema(profile))
            self.assertEqual(['0002'], values(pred, entry['field_id']))

    def test_immediate_right_and_uniform_vertical(self):
        right = table([['Repair record', '0002'], ['Premises name', 'Public building']])
        vertical = table([['Repair record', 'Premises name'], ['0002', 'Public building']])
        for body in (right, vertical):
            pred = predicted(body, schema())
            self.assertEqual(['0002'], values(pred)); self.assertEqual(['Public building'], values(pred, 'property_name'))

    def test_unique_geometry_and_ambiguous_geometry(self):
        label = block('Repair record', (10, 10, 100, 20))
        right = block('0002', (110, 10, 160, 20)); below = block('0003', (10, 25, 100, 35))
        self.assertEqual(['0002'], values(predicted(label, right, schema())))
        self.assertEqual([], values(predicted(label, right, below, schema())))

    def test_duplicate_equal_conflicting_and_canonical_alias_all_abstain(self):
        for second in ('Repair record: 0002', 'Repair record: 0003', 'Work Order ID: 0002', 'Ticket Number: 0002'):
            pred = predicted(block('Repair record: 0002'), block(second), schema())
            self.assertEqual([], values(pred))
            decision = next(d for d in pred['mapping_v2_decisions'] if d.get('field_id') == 'work_order_id')
            self.assertEqual('duplicate_label', decision['reason'])

    def test_duplicate_scope_is_page_wide_but_not_cross_page(self):
        first = block('Repair record: 0002') + schema()
        parsed = parse_native('<PAGE>' + first + '<PAGE>' + first)
        self.assertEqual(['0002', '0002'], values(extract_prediction(parsed)))
        self.assertEqual([], values(predicted(block('Repair record: 0002'), block('Prose mentions Repair record elsewhere'), schema())))

    def test_right_rejection_cannot_escape_to_legacy_below(self):
        field = table([['Work Order ID', '0002'], ['wrong-below', 'other']])
        parsed = parse_native('<PAGE>' + field + schema())
        self.assertEqual(['wrong-below'], values(v1(parsed, mapping())))
        self.assertEqual([], values(extract_prediction(parsed)))

    def test_additional_plain_cell_and_label_containing_neighbor(self):
        for row in (['Repair record', '0002', 'another'], ['Repair record', 'Property extra'], ['Repair record', 'Unknown label: value']):
            self.assertEqual([], values(predicted(table([row]), schema())))
        pred = predicted(block('Repair record: Property extra'), schema())
        self.assertEqual([], values(pred)); self.assertEqual([], values(pred, 'property_name'))

    def test_empty_explicit_cell_only_no_implicit_absence(self):
        self.assertEqual([''], values(predicted(table([['Occupant callback', '']]), schema()), 'resident_contact'))
        self.assertEqual([], values(predicted(block('Occupant callback'), schema()), 'resident_contact'))
        self.assertEqual([], values(predicted(table([['Occupant callback', ''], ['another', 'x']]), schema()), 'resident_contact'))

    def test_no_profile_multiple_profiles_and_duplicate_schema(self):
        alias = block('Repair record: 0002')
        for bodies in ((alias,), (alias, schema(), schema(1)), (alias, schema(), schema())):
            pred = predicted(*bodies)
            self.assertEqual([], values(pred)); self.assertEqual([], pred['tables'])

    def test_alias_other_profile_is_not_routed_by_shared_target(self):
        self.assertEqual([], values(predicted(block('Inspection record: 0002'), schema(0))))

    def test_header_collision_unknown_punctuation_case_and_spans(self):
        rule = catalog()['profiles'][0]['tables'][0]; base = rule['alias_headers']
        for changed in ([base[0], base[0], *base[2:]], [base[0], 'Outside', *base[2:]],
                        [base[0] + ':', *base[1:]], [base[0].lower(), *base[1:]], [(base[0], 2), *base[1:]]):
            pred = predicted(block('Repair record: 0002'), table([changed, ['0007', 'part', 'B', '2']]))
            self.assertEqual([], pred['tables']); self.assertEqual([], values(pred))

    def test_canonical_table_guards_remove_legacy_rows(self):
        for rows in ([['0007', 'part', 'B']], [['0007', 'part', 'B', '2', 'extra']],
                     [['', 'part', 'B', '2']], [['0007', 'part', 'B', '2'], ['0007', 'part', 'B', '2']],
                     [['0007', 'part', 'B', '2'], ['0007', 'other', 'B', '3']], [[('0007', 2), 'part', 'B', '2']]):
            parsed = parse_native('<PAGE>' + schema(aliases=False, rows=rows))
            self.assertEqual(1, len(v1(parsed, mapping())['tables']))
            self.assertEqual([], extract_prediction(parsed)['tables'])

    def test_repeated_header_abstains_entire_table(self):
        rule = catalog()['profiles'][0]['tables'][0]
        for headers in (rule['canonical_headers'], rule['alias_headers'], list(reversed(rule['alias_headers']))):
            pred = predicted(schema(rows=[['0007', 'part', 'B', '2'], headers]))
            self.assertEqual([], pred['tables'])

    def test_bad_data_does_not_erase_valid_native_profile(self):
        pred = predicted(block('Repair record: 0002'), schema(rows=[['0007', 'short']]))
        self.assertEqual(['0002'], values(pred)); self.assertEqual([], pred['tables'])

    def test_exact_boundaries_case_space_and_colon(self):
        for text in ('xRepair record: 0002', 'Repair records: 0002', 'repair record: 0002', 'Repair  record: 0002', 'Repair record:: 0002'):
            self.assertEqual([], values(predicted(block(text), schema())))
        self.assertEqual(['0002'], values(predicted(block('Repair record\t0002'), schema())))

    def test_untouched_v1_fields_tables_and_native_data_preserved(self):
        raw = '<PAGE>' + block('Contract ID: PUBLIC-1') + schema()
        parsed = parse_native(raw); baseline = v1(parsed, mapping()); new = extract_prediction(parsed)
        self.assertEqual([x for x in baseline['fields'] if x['field_id'] == 'contract_id'], [x for x in new['fields'] if x['field_id'] == 'contract_id'])
        self.assertEqual(baseline['pages'], new['pages']); self.assertEqual(baseline['unmapped'], new['unmapped'])
        untouched = '<PAGE>' + table([mapping()['tables'][0]['headers'], ['1', 'T', '2026-01-01', '1', '2', '1', 'A']])
        parsed = parse_native(untouched)
        self.assertEqual(v1(parsed, mapping())['tables'], extract_prediction(parsed)['tables'])

    def test_parse_error_never_introduces_aliases(self):
        parsed = parse_native('<PAGE>' + block('Repair record: 0002') + schema()); parsed['errors'].append('synthetic error')
        before = v1(parsed, mapping()); after = extract_prediction(parsed)
        self.assertEqual(before['fields'], after['fields']); self.assertEqual(before['tables'], after['tables'])

    def test_non_table_markup_not_used_as_field_values(self):
        self.assertEqual([], values(predicted(block('<span title="Repair record: 0002">text</span>'), schema())))


if __name__ == '__main__': unittest.main()
