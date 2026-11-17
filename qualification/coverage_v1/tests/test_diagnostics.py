"""Independent tiny public test data, unrelated to sealed fixtures."""
import copy
import unittest
from qualification.coverage_v1.common import mapping,paired
from qualification.coverage_v1.contract import validate,validate_family,support_control,semantic_signature,CONDITIONS
from qualification.coverage_v1.diagnostics import diagnose,presence,visible_units

def block(text,kind='text',box='0,0,900,30'):return f'<BLOCK>{kind}[{box}]<FORK>{text}'
def table(rows):return '<table>'+''.join('<tr>'+''.join('<td>'+v+'</td>' for v in row)+'</tr>' for row in rows)+'</table>'

def tiny(condition='control',family='WP11-F01',value='TEST-0042'):
    fid=family+'-'+condition+'-v0';label='Work Order ID';raw='<PAGE>'+block(label+': '+value)
    e={'fixture_id':fid,'family_id':family,'split':'diagnostic_eval','variant_kind':condition,'page_count':1,
       'expected_fields':[{'field_id':'work_order_id','page_number':1,'label_printed':label,'printed_text':value,'normalized_value':value,'value_type':'identifier'}],
       'expected_tables':[],'expected_absences':[],'page_sentinels':[],'expected_adjacent_page_pairs':[],'cross_page_links':[]}
    ref={'pages':[label+': '+value],'coverage':{'status':'test-only'}}
    a={'schema':'eld-coverage-annotations/1','fixture_id':fid,'family_id':family,'condition':condition,'control_fixture_id':family+'-control-v0','page_count':1,
       'fields':[{'field_id':'work_order_id','page_number':1,'label_printed':label,'label_bbox_pt':[1,1,2,2],'value_bbox_pt':[3,1,4,2]}],
       'tables':[],'absences':[],'ideal_native':raw}
    return e,ref,a

class DiagnosticTests(unittest.TestCase):
    def test_supported_control_requires_both_mappers_not_label_membership(self):
        e,r,a=tiny();self.assertEqual(support_control(e,r,a)['status'],'supported_by_both_frozen_mappers')
        a['ideal_native']='<PAGE>'+block(table([['Work Order ID','TEST-0042']]),'table')
        pair=paired(a['ideal_native'],e,r)
        self.assertEqual(pair['scores']['mapping_v1']['fields']['correct'],1)
        self.assertEqual(pair['scores']['b0']['fields']['correct'],0)
        with self.assertRaises(ValueError):support_control(e,r,a)

    def test_metadata_coordinates_and_html_attributes_are_not_presence(self):
        e,r,a=tiny(value='0042')
        raw='<PAGE>'+block('<span data-code="0042">OTHER</span>',box='42,42,142,142')
        d=diagnose(raw,e,r);self.assertEqual(d['slots'][0]['value_presence']['count'],0)
        self.assertEqual(d['slots'][0]['local_visible_payload_evidence_not_rate']['count'],0)

    def test_visible_entity_decoding_and_identifier_boundaries(self):
        e,r,a=tiny(value='X&Y');d=diagnose('<PAGE>'+block('Work Order ID: X&amp;Y'),e,r)
        self.assertEqual(d['slots'][0]['value_presence']['count'],1)
        self.assertEqual(d['historical_scores']['b0']['fields']['correct'],0)
        e,r,a=tiny(value='0042');d=diagnose('<PAGE>'+block('Work Order ID: 10042'),e,r)
        self.assertEqual(d['slots'][0]['value_presence']['count'],0)

    def test_duplicate_values_remain_ambiguous(self):
        e,r,a=tiny(value='DUP-01');e['expected_fields'].append({**e['expected_fields'][0],'field_id':'work_order_ref','label_printed':'Work Order Ref'})
        d=diagnose('<PAGE>'+block('Work Order ID: DUP-01')+block('Work Order Ref: DUP-01',box='0,60,900,90'),e,r)
        self.assertTrue(all(x['value_presence']['count']==2 and x['expected_same_page_value_multiplicity']==2 for x in d['slots']))
        self.assertEqual(d['stage_metrics']['field']['b0']['printed_correct_given_supported_exact_payload']['denominator'],0)

    def test_parse_invalid_retains_local_evidence_but_no_presence_rate(self):
        e,r,a=tiny();raw=a['ideal_native']+block('<table><tr><td rowspan="2">BAD</td></tr></table>','table',box='0,100,900,200')
        d=diagnose(raw,e,r)
        self.assertFalse(d['eligible_for_presence']);self.assertEqual(d['presence_denominator']['unavailable_slots'],1)
        self.assertEqual(d['slots'][0]['value_presence']['status'],'unavailable')
        self.assertEqual(d['slots'][0]['local_visible_payload_evidence_not_rate']['count'],1)
        self.assertEqual(d['page_structure'][0]['unparsed_or_rejected_blocks'],1)

    def test_unavailable_original_denominator_is_not_zero_error(self):
        e,r,a=tiny();d=diagnose(None,e,r,'not_run_after_failure')
        self.assertEqual(d['historical_scores']['b0']['fields']['total'],1)
        self.assertEqual(d['presence_denominator']['eligible_slots'],0)
        self.assertIsNone(d['stage_metrics']['field']['exact_visible_payload_presence']['rate'])
        self.assertEqual(d['slots'][0]['mappers']['b0']['evidence_flags_nonexclusive'],['unavailable_output_or_parse'])

    def test_original_numeric_quantity_credit_does_not_mean_unit_agreement(self):
        e,r,a=tiny();e['expected_fields']=[]
        t=next(t for t in mapping()['tables'] if t['table_id']=='line_items')
        values=['R1','S1','PART','2.00 HR','$1.00','0%','$0.00','T','$2.00']
        e['expected_tables']=[{'table_id':'line_items','column_ids':['qty_unit'],'rows':[{'row_id':'R1','page_number':1,'cells':{'qty_unit':{'printed_text':'2.00 EA','normalized_value':'2.00','value_type':'decimal_2','quantity_unit':'EA'}}}]}]
        d=diagnose('<PAGE>'+block(table([t['headers'],values]),'table'),e,r)
        slot=d['slots'][0]['mappers']['b0']
        self.assertTrue(slot['typed']['credited_exact']);self.assertFalse(slot['printed']['credited_exact'])
        self.assertEqual(slot['literal_unit']['status'],'different')

    def test_leading_zero_identifier_is_not_repaired(self):
        e,r,a=tiny(value='00042');d=diagnose('<PAGE>'+block('Work Order ID: 42'),e,r)
        self.assertFalse(d['slots'][0]['mappers']['b0']['identifier_printed_exact'])
        self.assertEqual(d['historical_scores']['b0']['normalized_fields']['correct'],0)

    def test_row_identity_prevents_other_rows_value_from_becoming_local_credit(self):
        e,r,a=tiny();e['expected_fields']=[];a['fields']=[]
        cols=['part_sku','part_desc','bin_loc','qty_used'];headers=['CODE','ITEM','SHELF','COUNT']
        def row(key,desc):return {'row_id':key,'page_number':1,'cells':{col:{'printed_text':v,'normalized_value':v,'value_type':'text'} for col,v in zip(cols,[key,desc,'B','2'])}}
        e['expected_tables']=[{'table_id':'stock_parts','column_ids':cols,'rows':[row('K1','ALPHA'),row('K2','BETA')]}]
        a['tables']=[{'table_id':'stock_parts','page_number':1,'headers':headers,'column_ids':cols,'row_key_column':'part_sku','header_bbox_pt':[1,1,5,2]}]
        raw='<PAGE>'+block(table([headers,['K1','BETA','B','2'],['K2','ALPHA','B','2']]),'table')
        d=diagnose(raw,e,r,annotations=a);s=next(x for x in d['slots'] if x['row_id']=='K1' and x['slot']=='part_desc')
        self.assertEqual(s['value_presence']['count'],1);self.assertEqual(s['local_binding']['status'],'one')
        self.assertFalse(s['local_binding']['cell']['observed_exact'])

    def test_pairing_preserves_units_values_and_explicit_absence_semantics(self):
        records=[tiny(c) for c in CONDITIONS];self.assertTrue(validate_family(records))
        for key,value in [('printed_text','OTHER'),('normalized_value','OTHER'),('value_type','text'),('quantity_unit','EA')]:
            changed=copy.deepcopy(records);changed[1][0]['expected_fields'][0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate_family(changed)
        e,r,a=tiny();e['expected_absences']=[{'field_id':'tenant_callback_notes','page_number':1,'label_printed':'Tenant Callback Notes','expected_state':'absent_blank'}]
        a['absences']=[{'field_id':'tenant_callback_notes','page_number':1,'label_printed':'Tenant Callback Notes','label_bbox_pt':[1,3,2,4]}]
        validate(e,r,a)
        changed=copy.deepcopy(e);changed['expected_absences'][0]['expected_state']='present'
        self.assertNotEqual(semantic_signature(e),semantic_signature(changed))
        with self.assertRaises(ValueError):validate(changed,r,a)
        changed=copy.deepcopy(e);changed['expected_absences'][0]['label_printed']='Changed'
        with self.assertRaises(ValueError):validate(changed,r,a)
        for bad in (None,''):
            changed=copy.deepcopy(e);changed['expected_fields'][0]['quantity_unit']=bad
            with self.assertRaises(ValueError):validate(changed,r,a)

    def test_degraded_is_bound_to_its_own_control(self):
        records=[tiny(c) for c in CONDITIONS];records[-1][1]['pages']=['Unrelated image']
        with self.assertRaises(ValueError):validate_family(records)

if __name__=='__main__':unittest.main()
