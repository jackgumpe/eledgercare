"""Finite exact alias/schema treatment. Prediction input is native evidence only.

Derives untouched output from accepted mapping_v1; affected identities are removed
before conservative resolution. No expected/reference/policy/fixture input exists.
"""
from collections import Counter, defaultdict
import copy
import re
from qualification.mapping_v1.mapper import extract_prediction as v1_prediction
from qualification.mapping_v1.common import norm, mapping
from .protocol.common import catalog


def extract_prediction(parsed, rules=None, alias_catalog=None):
    rules = mapping() if rules is None else rules
    alias_catalog = catalog() if alias_catalog is None else alias_catalog
    old = v1_prediction(parsed, rules)
    result = copy.deepcopy(old)
    decisions = []; omitted_decisions = 0

    def trace(**record):
        nonlocal omitted_decisions
        if len(decisions) < 10000:
            decisions.append(record)
        else:
            omitted_decisions += 1

    # Conservative matching uses exact decoded table cells or plain native text.
    # Markup inside non-table payload is not a field/value association surface.
    markup = re.compile(r'<[/!?A-Za-z]')
    labels = {x['label']: x['field_id'] for x in rules['labels']}
    aliases = {}
    profiles = {}; schemas = []
    for profile in alias_catalog['profiles']:
        profiles[profile['profile']] = profile
        for field in profile['fields']:
            for label in field['aliases']:
                labels[label] = field['field_id']; aliases[label] = field['field_id']
        for table in profile['tables']:
            headers = {}
            for ci, column in enumerate(table['columns']):
                for name in (table['canonical_headers'][ci], table['alias_headers'][ci]):
                    headers[name] = column
            schemas.append({**table, 'profile': profile['profile'], 'header_map': headers,
                            'alias_set': set(table['alias_headers'])})
    pattern = re.compile('|'.join(re.escape(label) for label in sorted(labels, key=lambda x: (-len(x), x))))

    def hits(text):
        return [m for m in pattern.finditer(text)
                if (m.start() == 0 or not (text[m.start()-1].isalnum() or text[m.start()-1] == '_'))
                and (m.end() == len(text) or text[m.end()] == ':' or text[m.end()].isspace())]

    def exact_label(text):
        value = norm(text)
        if value.endswith(':'): value = value[:-1]
        return value if value in labels else None

    def unsafe(text):
        return bool(markup.search(text) or hits(text) or text.rstrip().endswith(':')
                    or re.search(r'(?:^|\s)[^\W\d_][^:\n]{0,99}:\s*', text))

    def unit(row):
        return all(cell.get('colspan', 1) == cell.get('rowspan', 1) == 1 for cell in row)

    def resolve_header(row, schema):
        values = [norm(cell['text']) for cell in row]
        resolved = [schema['header_map'].get(value) for value in values]
        collisions = any(count > 1 for key, count in Counter(resolved).items() if key is not None)
        bijection = (len(values) == len(schema['columns']) and None not in resolved
                     and len(set(resolved)) == len(resolved) and set(resolved) == set(schema['columns']))
        return {'values': values, 'columns': resolved, 'collision': collisions,
                'alias_seen': any(value in schema['alias_set'] for value in values),
                'valid': bijection and unit(row), 'bijection': bijection}

    # A parse error does not create a new inferred structure. Original ineligible
    # output remains for honest comparison; no v2 aliases can be added.
    if parsed.get('errors'):
        trace(kind='document', action='unchanged_ineligible', reason='native_parse_error')
        result['mapping_v2_decisions'] = decisions
        result['mapping_v2_decisions_omitted'] = omitted_decisions
        return result

    for page in parsed['pages']:
        pn = page['page']; blocks = page['blocks']; table_candidates = []
        for bi, block in enumerate(blocks):
            if block['kind'] != 'table' or not block['rows']: continue
            first = next((ri for ri, row in enumerate(block['rows']) if any(norm(c['text']) for c in row)), None)
            if first is None: continue
            for schema in schemas:
                header = resolve_header(block['rows'][first], schema)
                if header['valid'] or header['alias_seen'] or header['collision'] or header['bijection']:
                    table_candidates.append({'block': bi, 'header_row': first, 'schema': schema, **header})
        valid = [x for x in table_candidates if x['valid']]
        profile_names = {x['schema']['profile'] for x in valid}
        active = None; context_reason = 'missing_profile'
        if len(profile_names) > 1:
            context_reason = 'multiple_profiles'
        elif len(profile_names) == 1:
            name = next(iter(profile_names))
            candidates_for_profile = [x for x in table_candidates if x['schema']['profile'] == name]
            if len(candidates_for_profile) == 1:
                active = profiles[name]; context_reason = 'unique_native_profile'
            else:
                context_reason = 'duplicate_schema_candidates'
        trace(kind='profile', page=pn, action='active' if active else 'abstain', reason=context_reason,
              profile=None if active is None else active['profile'], native_table_blocks=[x['block'] for x in valid])

        affected_tables = {x['schema']['table_id'] for x in table_candidates
                           if x['alias_seen'] or x['collision'] or x['bijection']}
        if active:
            affected_tables.update(t['table_id'] for t in active['tables'])
        if context_reason in ('multiple_profiles', 'duplicate_schema_candidates'):
            affected_tables.update(x['schema']['table_id'] for x in table_candidates)
        removed_tables = [t for t in result['tables'] if t['page'] == pn and t['table_id'] in affected_tables]
        result['tables'] = [t for t in result['tables'] if not (t['page'] == pn and t['table_id'] in affected_tables)]
        for item in table_candidates:
            schema = item['schema']; tid = schema['table_id']; bi = item['block']; reason = None
            if not active or schema['profile'] != active['profile']: reason = context_reason
            elif not item['valid']: reason = 'header_collision' if item['collision'] else 'unsupported_header_or_span'
            rows = blocks[bi]['rows'][item['header_row'] + 1:]
            emitted = []; keys = set()
            if reason is None:
                key_index = item['columns'].index(schema['row_key_column'])
                for ri, row in enumerate(rows, item['header_row'] + 1):
                    values = [norm(c['text']) for c in row]
                    if resolve_header(row, schema)['bijection']:
                        reason = 'repeated_header'; break
                    if not unit(row): reason = 'unsupported_span'; break
                    if len(row) != len(item['columns']): reason = 'row_width'; break
                    key = values[key_index]
                    if not key: reason = 'empty_row_key'; break
                    if key in keys: reason = 'duplicate_row_key'; break
                    keys.add(key)
                    emitted.append({'values': values, 'physical_values': values, 'cells': copy.deepcopy(row),
                                    'native_row': ri, 'mapping_status': 'mapped'})
            if reason is None:
                result['tables'].append({'table_id': tid, 'columns': item['columns'], 'page': pn,
                                         'rows': emitted, 'block': bi})
            trace(kind='table', page=pn, block=bi, table_id=tid, action='emit' if reason is None else 'abstain',
                  reason=reason or 'unique_header_rows_and_keys', columns=item['columns'],
                  removed_legacy_tables=sum(t['table_id'] == tid for t in removed_tables))

        # All recognized data tables, including untouched non-catalog B0 schemas,
        # are excluded from field association while still contributing label counts.
        data_blocks = {x['block'] for x in table_candidates}
        data_blocks.update(t['block'] for t in old['tables'] if t['page'] == pn and 'block' in t)
        occurrences = defaultdict(list); alias_targets = set()
        for bi, block in enumerate(blocks):
            surfaces = [(c['text'], [bi, ri, ci]) for ri, row in enumerate(block['rows']) for ci, c in enumerate(row)] if block['rows'] else [(block['text'], [bi])]
            for text, location in surfaces:
                for match in hits(text):
                    label = match[0]; fid = labels[label]
                    occurrences[fid].append({'label': label, 'text': text, 'location': location,
                                             'start': match.start(), 'end': match.end()})
                    if label in aliases: alias_targets.add(fid)
        affected_fields = set(alias_targets)
        if active: affected_fields.update(f['field_id'] for f in active['fields'])
        removed_fields = [f for f in result['fields'] if f['page'] == pn and f['field_id'] in affected_fields]
        result['fields'] = [f for f in result['fields'] if not (f['page'] == pn and f['field_id'] in affected_fields)]
        active_rules = {} if active is None else {f['field_id']: f for f in active['fields']}
        for fid in sorted(affected_fields):
            found = occurrences[fid]; reason = None; choices = []; unsafe_choices = []
            if active is None: reason = context_reason
            elif fid not in active_rules: reason = 'outside_active_profile'
            elif len(found) != 1: reason = 'duplicate_label' if found else 'missing_label'
            else:
                hit = found[0]; permitted = active_rules[fid]['canonical_labels'] + active_rules[fid]['aliases']
                if hit['label'] not in permitted: reason = 'outside_active_profile_label'
                location = hit['location']; bi = location[0]; block = blocks[bi]; text = hit['text']
                if bi in data_blocks: reason = reason or 'label_inside_data_table'
                if markup.search(text): reason = reason or 'unsupported_text_markup'
                if len(hits(text)) > 1: reason = reason or 'ambiguous_inline_labels'
                if text[hit['end']:].startswith('::'): reason = reason or 'multiple_label_colons'
                def candidate(value, value_location, association):
                    value = norm(value)
                    if exact_label(value): return  # A complete label is not a value orientation.
                    item = {'value': value, 'value_location': value_location, 'association': association}
                    if unsafe(value): unsafe_choices.append(item)
                    else: choices.append(item)
                if reason is None:
                    tail = text[hit['end']:]
                    if tail.startswith(':'): tail = tail[1:]
                    if norm(tail):
                        candidate(tail, location, 'inline')
                    elif exact_label(text) == hit['label']:
                        if len(location) == 3:
                            _, ri, ci = location; row = block['rows'][ri]
                            if not unit(row): reason = 'unsupported_span'
                            else:
                                if ci + 1 < len(row): candidate(row[ci+1]['text'], [bi, ri, ci+1], 'immediate_right')
                                if ci + 2 < len(row) and norm(row[ci+2]['text']) and not exact_label(row[ci+2]['text']):
                                    reason = 'additional_plain_cell'
                                if ri + 1 < len(block['rows']) and len(block['rows'][ri+1]) == len(row):
                                    below = block['rows'][ri+1]
                                    if not unit(below): reason = reason or 'unsupported_span'
                                    else: candidate(below[ci]['text'], [bi, ri+1, ci], 'direct_below')
                        elif block.get('bbox'):
                            x, y, x2, y2 = block['bbox']
                            for j, value_block in enumerate(blocks):
                                if j == bi or not value_block.get('bbox') or value_block['kind'] in ('table', 'footer'): continue
                                a, v, a2, v2 = value_block['bbox']
                                if a >= x2 and abs(v-y) <= 5: candidate(value_block['text'], [j], 'native_right_block')
                                if 0 <= v-y2 <= 25 and abs(a-x) <= 12: candidate(value_block['text'], [j], 'native_below_block')
                    else:
                        reason = 'missing_structural_payload'
            if reason is None and unsafe_choices: reason = 'label_or_markup_in_value'
            if reason is None and len(choices) != 1: reason = 'ambiguous_value_candidates' if choices else 'missing_value_candidate'
            if reason is None and not choices[0]['value'] and choices[0]['association'] not in ('immediate_right', 'direct_below'):
                reason = 'implicit_empty_value'
            if reason is None:
                result['fields'].append({'field_id': fid, 'label': found[0]['label'], 'page': pn,
                                         'value': choices[0]['value'], 'location': found[0]['location'],
                                         'value_location': choices[0]['value_location'], 'association': choices[0]['association']})
            trace(kind='field', page=pn, field_id=fid, action='emit' if reason is None else 'abstain',
                  reason=reason or ('explicit_empty_cell' if not choices[0]['value'] else 'unique_structural_candidate'),
                  label_occurrences=len(found), candidates=len(choices), unsafe_candidates=len(unsafe_choices),
                  label_locations=[x['location'] for x in found[:20]],
                  removed_legacy_candidates=sum(f['field_id'] == fid for f in removed_fields))
    result['mapping_v2_decisions'] = decisions
    result['mapping_v2_decisions_omitted'] = omitted_decisions
    return result
