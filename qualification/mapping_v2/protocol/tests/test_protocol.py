"""Tiny public synthetic reference/scoring counterexamples, not a v2 mapper."""
import copy
import unittest
from qualification.mapping_v1.common import parse_native, score_document
from qualification.mapping_v2.protocol.common import catalog, catalog_sha, load, HERE
from qualification.mapping_v2.protocol.contract import validate, validate_family, validate_catalog, FAMILIES
from qualification.mapping_v2.protocol.scoring import score_policy, summarize_policy, original_comparison


def fixture(case='supported', family='WP13-F01'):
    profile = next(p for p in catalog()['profiles'] if p['profile'] == FAMILIES[family])
    field = profile['fields'][0]; table = profile['tables'][0]
    identity = family + '-' + case + '-v0'
    def truth(value, kind='text'):
        return {'printed_text': value, 'normalized_value': value, 'value_type': kind}
    def evidence(label, value, offset=0):
        return {'label_printed': label, 'value_printed': value,
                'label_bbox_pt': [1, 1 + offset, 20, 5 + offset], 'value_bbox_pt': [21, 1 + offset, 40, 5 + offset]}
    ft = truth('0002', 'identifier')
    values = ['0007'] + ['public-value-' + str(i) for i in range(1, len(table['columns']))]
    cells = {col: truth(values[i]) for i, col in enumerate(table['columns'])}
    expected = {'fixture_id': identity, 'family_id': family, 'doc_kind': profile['doc_kind'], 'split': 'vocabulary_eval',
                'variant_kind': case, 'page_count': 1, 'expected_fields': [dict(field_id=field['field_id'], page_number=1,
                    label_printed=field['aliases'][0], **ft)],
                'expected_tables': [{'table_id': table['table_id'], 'column_ids': table['columns'],
                    'rows': [{'row_id': 'public-row', 'page_number': 1, 'cells': cells}]}],
                'expected_absences': [], 'page_sentinels': [], 'expected_adjacent_page_pairs': [], 'cross_page_links': []}
    raw = '<PAGE><BLOCK>text[1,1,100,10]<FORK>Public synthetic witness'
    raw += '<BLOCK>table[1,20,100,90]<FORK><table><tr>'
    raw += ''.join('<td>' + h + '</td>' for h in table['canonical_headers']) + '</tr><tr>'
    raw += ''.join('<td>' + value + '</td>' for value in values) + '</tr></table>'
    reference = {'pages': ['Public synthetic witness'], 'coverage': {}}
    slots = [{'kind': 'field', 'page_number': 1, 'field_id': field['field_id'], 'truth_status': 'known',
              'truth': ft, 'action': 'assign', 'reason': 'supported', 'evidence': [evidence(field['aliases'][0], '0002')]}]
    for index, col in enumerate(table['columns']):
        slots.append({'kind': 'cell', 'page_number': 1, 'table_id': table['table_id'], 'row_ordinal': 0,
                      'row_id': 'public-row', 'column_id': col, 'truth_status': 'known', 'truth': cells[col],
                      'action': 'assign', 'reason': 'supported', 'evidence': [evidence(table['alias_headers'][index], values[index]) ]})
    if case == 'conflict':
        slots[0].update(action='abstain', reason='duplicate_equal')
        slots[0]['evidence'].append(evidence(field['aliases'][0], '0002', 10))
    if case == 'unsupported':
        slots[0].update(action='abstain', reason='unsupported_vocabulary')
        slots[0]['evidence'][0]['label_printed'] = 'Public outside dictionary'
        expected['expected_fields'][0]['label_printed'] = 'Public outside dictionary'
    policy = {'schema': 'eld-mapping-v2-policy/1', 'fixture_id': identity, 'family_id': family, 'case': case,
              'profile': profile['profile'], 'page_count': 1, 'catalog_sha256': catalog_sha(), 'ideal_native': raw,
              'tables': [{'table_id': table['table_id'], 'column_ids': table['columns'], 'row_ids': ['public-row']}], 'slots': slots}
    prediction = {'schema': 'eld-baseline-prediction/1', 'fields': [{'field_id': field['field_id'], 'page': 1, 'value': '0002', 'location': [0]}],
                  'tables': [{'table_id': table['table_id'], 'columns': table['columns'], 'page': 1, 'block': 1,
                              'rows': [{'values': values, 'physical_values': values, 'native_row': 1, 'mapping_status': 'mapped'}]}],
                  'pages': parse_native(raw)['pages'], 'parse_errors': [], 'anchors': [], 'unmapped': []}
    return expected, reference, policy, prediction


class ContractTests(unittest.TestCase):
    def test_catalog_exact_finite_and_sourced(self):
        c = validate_catalog()
        self.assertEqual(26, sum(len(f['aliases']) for p in c['profiles'] for f in p['fields']))
        self.assertEqual(17, sum(len(t['alias_headers']) for p in c['profiles'] for t in p['tables']))

    def test_catalog_rejects_field_and_header_collisions(self):
        for kind in ('field', 'header'):
            c = catalog(); profile = c['profiles'][0]
            if kind == 'field': profile['fields'][1]['aliases'] = profile['fields'][0]['aliases']
            else: profile['tables'][0]['alias_headers'][1] = profile['tables'][0]['alias_headers'][0]
            with self.subTest(kind=kind), self.assertRaises(ValueError): validate_catalog(c)

    def test_all_public_profile_case_schemas(self):
        for family in FAMILIES:
            for case in ('supported', 'conflict', 'unsupported'):
                e, r, p, _ = fixture(case, family)
                self.assertEqual(len(p['slots']), validate(e, r, p)['known'])

    def test_matched_family_preserves_semantics(self):
        records = [fixture(c)[:3] for c in ('supported', 'conflict', 'unsupported')]
        self.assertEqual(3, len(validate_family(records)))

    def test_quantity_presence_and_value_bound(self):
        for change in ('different', 'missing'):
            records = [fixture(c)[:3] for c in ('supported', 'conflict', 'unsupported')]
            for e, _, p in records:
                e['expected_fields'][0]['quantity_unit'] = 'EA'; p['slots'][0]['truth']['quantity_unit'] = 'EA'
            e, _, p = records[-1]
            if change == 'different':
                e['expected_fields'][0]['quantity_unit'] = 'HR'; p['slots'][0]['truth']['quantity_unit'] = 'HR'
            else:
                del e['expected_fields'][0]['quantity_unit']; del p['slots'][0]['truth']['quantity_unit']
            with self.subTest(change=change), self.assertRaises(ValueError): validate_family(records)

    def test_unit_metadata_empty_rejected(self):
        e, r, p, _ = fixture(); e['expected_fields'][0]['quantity_unit'] = ''; p['slots'][0]['truth']['quantity_unit'] = ''
        with self.assertRaises(ValueError): validate(e, r, p)

    def test_label_truth_and_catalog_binding(self):
        for change in ('label', 'truth', 'catalog'):
            e, r, p, _ = fixture()
            if change == 'label': e['expected_fields'][0]['label_printed'] = 'Wrong'
            elif change == 'truth': e['expected_fields'][0]['normalized_value'] = 'Wrong'
            else: p['catalog_sha256'] = '0' * 64
            with self.subTest(change=change), self.assertRaises(ValueError): validate(e, r, p)

    def test_header_colon_is_not_field_colon_normalization(self):
        e, r, p, _ = fixture()
        p['slots'][0]['evidence'][0]['label_printed'] += ':'
        e['expected_fields'][0]['label_printed'] += ':'
        validate(e, r, p)
        p['slots'][1]['evidence'][0]['label_printed'] += ':'
        with self.assertRaises(ValueError): validate(e, r, p)

    def test_ambiguous_truth_has_no_fabricated_expected_value(self):
        e, r, p, _ = fixture('conflict'); s = p['slots'][0]
        s.update(truth_status='ambiguous', truth=None, reason='conflicting_values'); s['evidence'][1]['value_printed'] = '0003'
        with self.assertRaises(ValueError): validate(e, r, p)
        e['expected_fields'] = []
        self.assertEqual(1, validate(e, r, p)['ambiguous'])

    def test_known_row_key_and_nonempty_expected_rows_required(self):
        for empty in (False, True):
            e, r, p, _ = fixture('conflict')
            row = e['expected_tables'][0]['rows'][0]
            columns = list(row['cells']) if empty else [next(iter(row['cells']))]
            for col in columns:
                del row['cells'][col]
                slot = next(s for s in p['slots'] if s.get('column_id') == col)
                slot.update(truth_status='unknown', truth=None, action='abstain', reason='missing_structure')
            with self.subTest(empty=empty), self.assertRaises(ValueError): validate(e, r, p)

    def test_complete_policy_universe_and_ordinal_binding(self):
        for change in ('missing', 'duplicate', 'ordinal', 'row_id'):
            e, r, p, _ = fixture()
            if change == 'missing': p['slots'].pop()
            elif change == 'duplicate': p['slots'].append(copy.deepcopy(p['slots'][1]))
            elif change == 'ordinal': p['slots'][1]['row_ordinal'] = 1
            else: p['slots'][1]['row_id'] = 'wrong'
            with self.subTest(change=change), self.assertRaises(ValueError): validate(e, r, p)

    def test_absence_state_and_label_are_explicit(self):
        e, r, p, pred = fixture(); rule = catalog()['profiles'][0]['fields'][-1]
        slot = {'kind': 'absence', 'page_number': 1, 'field_id': rule['field_id'], 'truth_status': 'known',
                'truth': {'printed_text': '', 'expected_state': 'absent_blank'}, 'action': 'assign', 'reason': 'supported',
                'evidence': [{'label_printed': rule['aliases'][0], 'value_printed': '', 'label_bbox_pt': [1,1,2,2], 'value_bbox_pt': [3,1,4,2]}]}
        p['slots'].append(slot); e['expected_absences'].append({'field_id': rule['field_id'], 'page_number': 1,
            'label_printed': rule['aliases'][0], 'expected_state': 'absent_blank'})
        validate(e, r, p)
        e['expected_absences'][0]['expected_state'] = 'unknown'
        with self.assertRaises(ValueError): validate(e, r, p)

    def test_schedule_scope_and_no_model_entrypoint(self):
        p = load(HERE / 'protocol.json')
        self.assertEqual(p['author_calls'], len(p['families']) * len(p['cases']) + len(p['historical_warmups']))
        self.assertEqual(3, p['reviewer_calls']); self.assertEqual('WP13-F04-conflict-v0', p['sentinel'])
        self.assertFalse(p['retry_allowed']); self.assertEqual('specified_only_until_005', p['runtime_preparation']['implementation'])


class ScoringTests(unittest.TestCase):
    def test_exact_and_incorrect_assignments(self):
        e, r, p, pred = fixture(); result = score_policy(pred, e, r, p)
        self.assertEqual(len(p['slots']), result['metrics']['strict_correct_known_slots'])
        pred['fields'][0]['value'] = 'wrong'; result = score_policy(pred, e, r, p)
        self.assertEqual(1, result['metrics']['incorrect_assignments'])

    def test_duplicate_equal_not_hidden_by_original_first_candidate_credit(self):
        e, r, p, pred = fixture('conflict'); pred['fields'].append(copy.deepcopy(pred['fields'][0]))
        self.assertEqual(1, score_document(pred, e, r)['fields']['correct'])
        result = score_policy(pred, e, r, p)
        self.assertEqual(1, result['metrics']['required_abstention_violations'])
        self.assertEqual(1, result['metrics']['surplus_candidates_within_slots'])
        self.assertFalse(result['slots'][0]['strict_correct_known'])

    def test_conflicting_and_canonical_alias_candidates_both_count(self):
        e, r, p, pred = fixture('conflict'); other = copy.deepcopy(pred['fields'][0]); other['value'] = '0003'
        pred['fields'][0]['label'] = 'Work Order ID'; other['label'] = 'Repair record'; pred['fields'].append(other)
        result = score_policy(pred, e, r, p)
        self.assertEqual(2, result['slots'][0]['candidate_count']); self.assertEqual(1, result['metrics']['incorrect_assignments'])

    def test_required_abstention_has_no_exact_value_credit(self):
        e, r, p, pred = fixture('conflict'); pred['fields'] = []; result = score_policy(pred, e, r, p)
        self.assertEqual(1, result['metrics']['required_abstention_observed'])
        self.assertEqual(0, score_document(pred, e, r)['fields']['correct'])
        self.assertFalse(result['slots'][0]['strict_correct_known'])

    def test_ambiguous_and_unknown_truth_assignments_are_unjudged(self):
        for status in ('ambiguous', 'unknown'):
            e, r, p, pred = fixture('conflict'); e['expected_fields'] = []
            p['slots'][0].update(truth_status=status, truth=None)
            result = score_policy(pred, e, r, p)
            self.assertEqual(1, result['metrics'][status + '_truth_assignments'])
            self.assertIsNone(result['slots'][0]['strict_correct_known'])
            pred['fields'] = []; result = score_policy(pred, e, r, p)
            self.assertEqual(1, result['metrics']['required_abstention_observed_truth_' + status])
            self.assertIsNone(result['slots'][0]['strict_correct_known'])

    def test_blank_candidate_is_not_abstention(self):
        e, r, p, pred = fixture('conflict'); pred['fields'][0]['value'] = ''
        result = score_policy(pred, e, r, p)
        self.assertEqual(1, result['metrics']['required_abstention_violations']); self.assertFalse(result['slots'][0]['abstained'])

    def test_failure_missing_native_parse_and_visibility_unavailable(self):
        for reason in ('failed', 'not_run_after_failure', 'parse', 'missing', 'visibility'):
            e, r, p, pred = fixture('conflict'); pred['fields'] = []
            completion = reason if reason in ('failed', 'not_run_after_failure') else 'completed'
            if reason == 'parse': pred['parse_errors'] = ['public synthetic parse failure']
            if reason == 'missing': pred['pages'] = []
            if reason == 'visibility': pred['pages'][0]['blocks'][0]['text'] = '<unknown>visible?</unknown>'
            result = score_policy(pred, e, r, p, completion)
            self.assertEqual(len(p['slots']), result['metrics']['unavailable_slots'])
            self.assertEqual(0, result['metrics']['required_abstention_observed'])
            self.assertIsNone(result['rates']['coverage_eligible']['rate'])

    def test_duplicate_tables_and_columns_remain_candidates(self):
        for kind in ('table', 'column'):
            e, r, p, pred = fixture()
            if kind == 'table': pred['tables'].append(copy.deepcopy(pred['tables'][0]))
            else:
                pred['tables'][0]['columns'] = list(pred['tables'][0]['columns'])
                pred['tables'][0]['columns'][1] = pred['tables'][0]['columns'][0]
            result = score_policy(pred, e, r, p)
            self.assertEqual(2, result['slots'][1]['candidate_count'])
            self.assertFalse(result['slots'][1]['strict_correct_known'])

    def test_surplus_universe_assignments_not_dropped(self):
        e, r, p, pred = fixture(); pred['fields'].append({'field_id': 'outside', 'page': 1, 'value': 'extra'})
        pred['tables'][0]['rows'][0]['values'].append('extra-column')
        result = score_policy(pred, e, r, p)
        self.assertEqual(2, result['metrics']['surplus_output_candidates'])

    def test_partial_row_original_extra_cells_are_not_policy_surplus(self):
        e, r, p, pred = fixture('conflict'); slot = p['slots'][2]; col = slot['column_id']
        del e['expected_tables'][0]['rows'][0]['cells'][col]
        slot.update(truth_status='ambiguous', truth=None, action='abstain', reason='header_collision')
        original = score_document(pred, e, r); result = score_policy(pred, e, r, p)
        self.assertEqual(1, original['rows']['correct']); self.assertEqual(1, original['cells']['extra_cells'])
        self.assertEqual(0, result['metrics']['surplus_output_candidates']); self.assertEqual(1, result['row_truth'][0]['ambiguous'])

    def test_leading_zero_identifier_is_not_repaired(self):
        e, r, p, pred = fixture(); pred['fields'][0]['value'] = '2'
        result = score_policy(pred, e, r, p)
        self.assertEqual(1, result['metrics']['incorrect_assignments'])

    def test_same_original_scorer_for_supplied_candidate(self):
        e, r, p, pred = fixture(); out = original_comparison(p['ideal_native'], e, r, 'completed', pred)
        self.assertEqual(score_document(pred, e, r, 'completed'), out['scores']['mapping_v2'])
        omitted = original_comparison(p['ideal_native'], e, r, 'completed')
        self.assertEqual('not_implemented', omitted['v2_status']); self.assertNotIn('mapping_v2', omitted['scores'])

    def test_full_frame_and_null_conditional_denominators(self):
        rows = []
        for family in FAMILIES:
            for case in ('supported', 'conflict', 'unsupported'):
                e, r, p, pred = fixture(case, family)
                rows.append(score_policy(pred, e, r, p, 'not_run_after_failure'))
        result = summarize_policy(rows)
        self.assertEqual(12, result['all']['documents']); self.assertEqual(4, len(result['families']))
        self.assertEqual(0, result['equal_family_means']['strict_known_exact']['families_with_denominator'])
        self.assertIsNone(result['equal_family_means']['strict_known_exact']['mean'])
        with self.assertRaises(ValueError): summarize_policy(rows[:-1])
        with self.assertRaises(ValueError): summarize_policy(rows[:-1] + [rows[0]])


if __name__ == '__main__':
    unittest.main()
