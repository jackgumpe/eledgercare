"""Pure reference-side policy counts. Never implements or repairs extraction."""
from collections import Counter, defaultdict
from qualification.mapping_v1.common import norm, score_document
from qualification.mapping_v1.scoring import paired
from qualification.coverage_v1.diagnostics import visible_units
from .common import require
from .contract import validate, target, TRUTH, FAMILIES, CASES


def candidates(prediction):
    """Count actual emitted assignments, retaining repeated fields/tables/columns."""
    result = defaultdict(list)
    for index, field in enumerate(prediction['fields']):
        require(isinstance(field['value'], str), 'Prediction value must be a string')
        result[('field', field['page'], field['field_id'])].append(
            {'value': field['value'], 'field_index': index, 'location': field.get('location')})
    for ti, table in enumerate(prediction['tables']):
        for ri, row in enumerate(table['rows']):
            for ci, value in enumerate(row['values']):
                require(isinstance(value, str), 'Prediction cell must be a string')
                column = table['columns'][ci] if ci < len(table['columns']) else '__surplus_column_' + str(ci)
                result[('cell', table['page'], table['table_id'], ri, column)].append(
                    {'value': value, 'table_index': ti, 'row_ordinal': ri, 'column_index': ci,
                     'block': table.get('block'), 'native_row': row.get('native_row')})
    return result


def original_comparison(raw, expected, reference, completion, v2_prediction=None):
    """Original scores stay byte-for-byte defined by the original scorer.

    v2_prediction is an independently produced prediction, never a reference-fed
    extraction. During /001 no v2 mapper exists; omission is explicit.
    """
    result = paired(raw, expected, reference, completion)
    if v2_prediction is not None:
        result['predictions']['mapping_v2'] = v2_prediction
        result['scores']['mapping_v2'] = score_document(v2_prediction, expected, reference, completion)
    result['v2_status'] = 'provided_prediction' if v2_prediction is not None else 'not_implemented'
    return result


def fraction(numerator, denominator):
    return {'numerator': numerator, 'denominator': denominator,
            'rate': numerator / denominator if denominator else None}


def score_policy(prediction, expected, reference, policy, completion='completed'):
    validate(expected, reference, policy)
    actual = candidates(prediction); problems = []
    visible_units(prediction, problems)
    eligible = (completion == 'completed' and not prediction['parse_errors'] and not problems
                and len(prediction['pages']) == 1 and prediction['pages'][0]['page'] == 1
                and bool(prediction['pages'][0]['blocks']))
    metrics = Counter({key: 0 for key in (
        'slots', 'eligible_slots', 'unavailable_slots', 'observed_candidates',
        'eligible_candidates', 'covered_slots', 'abstentions', 'correct_assignments',
        'incorrect_assignments', 'ambiguous_truth_assignments', 'unknown_truth_assignments',
        'strict_correct_known_slots', 'surplus_candidates_within_slots',
        'required_abstention_slots', 'eligible_required_abstentions',
        'unavailable_required_abstentions', 'required_abstention_violations',
        'required_abstention_observed', 'unexpected_abstentions', 'surplus_output_candidates')})
    for status in TRUTH:
        for prefix in ('truth_', 'eligible_truth_', 'unavailable_truth_', 'abstentions_truth_', 'required_abstention_observed_truth_'):
            metrics[prefix + status] = 0
    details = []; declared = set()
    for slot in policy['slots']:
        key = target(slot); declared.add(key); items = actual.get(key, []); status = slot['truth_status']
        metrics['slots'] += 1; metrics['observed_candidates'] += len(items); metrics['truth_' + status] += 1
        metrics['required_abstention_slots'] += slot['action'] == 'abstain'
        record = {'target': list(key), 'kind': slot['kind'], 'truth_status': status, 'action': slot['action'],
                  'reason': slot['reason'], 'eligible': eligible, 'candidate_count': len(items), 'candidates': items,
                  'strict_correct_known': None, 'required_abstention_violation': None, 'abstained': None}
        if not eligible:
            metrics['unavailable_slots'] += 1; metrics['unavailable_truth_' + status] += 1
            metrics['unavailable_required_abstentions'] += slot['action'] == 'abstain'
        else:
            metrics['eligible_slots'] += 1; metrics['eligible_truth_' + status] += 1
            metrics['eligible_candidates'] += len(items); metrics['covered_slots'] += bool(items)
            metrics['surplus_candidates_within_slots'] += max(0, len(items) - 1)
            record['abstained'] = not items
            metrics['abstentions'] += not items; metrics['abstentions_truth_' + status] += not items
            if status == 'known':
                matches = sum(norm(item['value']) == norm(slot['truth']['printed_text']) for item in items)
                metrics['correct_assignments'] += matches; metrics['incorrect_assignments'] += len(items) - matches
                record['strict_correct_known'] = len(items) == matches == 1
                metrics['strict_correct_known_slots'] += record['strict_correct_known']
            else:
                metrics[status + '_truth_assignments'] += len(items)
            if slot['action'] == 'abstain':
                metrics['eligible_required_abstentions'] += 1
                record['required_abstention_violation'] = bool(items)
                metrics['required_abstention_violations'] += bool(items)
                metrics['required_abstention_observed'] += not items
                metrics['required_abstention_observed_truth_' + status] += not items
            else:
                metrics['unexpected_abstentions'] += not items
        details.append(record)
    surplus = [{'target': list(key), 'candidates': value} for key, value in actual.items() if key not in declared]
    observed_surplus = sum(len(item['candidates']) for item in surplus)
    metrics['surplus_output_candidates'] = observed_surplus if eligible else 0
    metrics['observed_surplus_output_candidates'] = observed_surplus
    row_truth = []
    for table in policy['tables']:
        for ri, row_id in enumerate(table['row_ids']):
            statuses = Counter(s['truth_status'] for s in policy['slots'] if s['kind'] == 'cell'
                               and s['table_id'] == table['table_id'] and s['row_ordinal'] == ri)
            row_truth.append({'table_id': table['table_id'], 'row_ordinal': ri, 'row_id': row_id,
                              **{k: statuses[k] for k in TRUTH},
                              'original_row_credit_scope': 'declared_known_cells_only'})
    return {'schema': 'eld-mapping-v2-policy-score/1', 'fixture_id': policy['fixture_id'],
            'family_id': policy['family_id'], 'case': policy['case'], 'completion': completion,
            'document_denominator': 1, 'completed_documents': int(completion == 'completed'),
            'eligible': eligible, 'parse_errors': prediction['parse_errors'], 'visibility_problems': problems,
            'metrics': dict(metrics), 'rates': rates(metrics), 'slots': details, 'surplus_output': surplus,
            'row_truth': row_truth,
            'interpretation': 'Abstention observations are not exact-value credits. Original scores and every policy opportunity remain separate.'}


def rates(metrics):
    return {'coverage_all_slots': fraction(metrics['covered_slots'], metrics['slots']),
            'coverage_eligible': fraction(metrics['covered_slots'], metrics['eligible_slots']),
            'strict_known_exact': fraction(metrics['strict_correct_known_slots'], metrics['eligible_truth_known']),
            'required_abstention_violation': fraction(metrics['required_abstention_violations'], metrics['eligible_required_abstentions'])}


def summarize_policy(records):
    require(len(records) == 12 and {r['fixture_id'] for r in records} ==
            {family + '-' + case + '-v0' for family in FAMILIES for case in CASES}, 'Full twelve-document policy frame required')
    def group(rows):
        counter = Counter()
        for row in rows:
            counter.update(row['metrics'])
        return {'documents': len(rows), 'completed_documents': sum(r['completed_documents'] for r in rows),
                'eligible_documents': sum(r['eligible'] for r in rows), 'metrics': dict(counter), 'rates': rates(counter)}
    families = {f: group([r for r in records if r['family_id'] == f]) for f in FAMILIES}
    cases = {c: group([r for r in records if r['case'] == c]) for c in CASES}
    macro = {}
    for metric in ('coverage_all_slots', 'coverage_eligible', 'strict_known_exact', 'required_abstention_violation'):
        values = [f['rates'][metric]['rate'] for f in families.values() if f['rates'][metric]['rate'] is not None]
        macro[metric] = {'mean': sum(values) / len(values) if values else None, 'families_with_denominator': len(values), 'all_families': 4}
    return {'all': group(records), 'families': families, 'cases': cases, 'equal_family_means': macro}
