import copy
import html
import unittest
from unittest.mock import patch
from qualification.mapping_v1.common import ROOT,load_json,score_document
from qualification.mapping_v1.scoring import paired
from qualification.mapping_v1.common import parse_native,baseline_prediction,mapping
from qualification.mapping_v1.mapper import extract_prediction


def table(rows):
    return '<PAGE><BLOCK>table[0,0,900,900]<FORK><table>'+''.join('<tr>'+''.join('<td>'+html.escape(v)+'</td>' for v in row)+'</tr>' for row in rows)+'</table>'


class MappingTests(unittest.TestCase):
    def predictions(self,raw):
        parsed=parse_native(raw);before=copy.deepcopy(parsed);rules=mapping();saved=copy.deepcopy(rules)
        old=baseline_prediction(parsed,rules);new=extract_prediction(parsed,rules)
        self.assertEqual(parsed,before);self.assertEqual(rules,saved)
        self.assertEqual(old['tables'],new['tables']);self.assertEqual(old['pages'],new['pages'])
        self.assertEqual(old['parse_errors'],new['parse_errors']);self.assertEqual(old['unmapped'],new['unmapped'])
        return old,new

    def unchanged(self,raw):
        old,new=self.predictions(raw);self.assertEqual(old,new)

    def test_immediate_value_has_single_emission_and_provenance(self):
        old,new=self.predictions(table([['Invoice No:','INV-TEST'],['Due Date:','2031-05-04']]))
        self.assertEqual(len(new['fields']),2)
        self.assertEqual([x['value'] for x in new['fields']],['INV-TEST','2031-05-04'])
        self.assertEqual(new['fields'][0]['location'],[0,0,0])
        self.assertEqual(new['fields'][0]['value_location'],[0,0,1])
        self.assertEqual(new['fields'][0]['association'],'immediate_right_neighbor')
        self.assertNotEqual(old['fields'],new['fields'])

    def test_column_header_and_vertical_layout_fallback(self):
        self.unchanged(table([['Invoice No:','Due Date:'],['INV-TEST','2031-05-04']]))
        self.unchanged(table([['Invoice No:'],['INV-TEST']]))

    def test_empty_missing_known_unknown_and_containing_labels(self):
        for cells in [['Invoice No:'],['Invoice No:',''],['Invoice No:','   '],
                      ['Invoice No:','Due Date:'],['Invoice No:','Unknown Label:'],
                      ['Invoice No:','note Due Date: someday']]:
            with self.subTest(cells=cells):self.unchanged(table([cells]))

    def test_all_label_row(self):
        self.unchanged(table([['Invoice No:','Due Date:','Terms:'],['INV-TEST','2031-05-04','Net 31']]))

    def test_multiple_plausible_right_or_below_values(self):
        self.unchanged(table([['Invoice No:','ONE','TWO']]))
        self.unchanged(table([['Invoice No:','ONE'],['TWO','THREE']]))

    def test_spans_anywhere_in_current_row(self):
        for fragment in [
            '<td colspan="2">Invoice No:</td><td>ONE</td>',
            '<td>Invoice No:</td><td colspan="2">ONE</td>',
            '<td>Invoice No:</td><td>ONE</td><td colspan="2">Due Date:</td>',
            '<td rowspan="2">Invoice No:</td><td>ONE</td>']:
            with self.subTest(fragment=fragment):self.unchanged('<PAGE><BLOCK>table[0,0,900,900]<FORK><table><tr>'+fragment+'</tr></table>')

    def test_duplicate_label_or_alias_is_page_scoped(self):
        self.unchanged(table([['Invoice No:','ONE'],['Invoice No:','TWO']]))
        first=table([['Work Order ID:','ONE']]);second=table([['Ticket Number:','TWO']]).replace('<PAGE>','')
        self.unchanged(first+second)
        first=table([['Invoice No:','ONE']]);second=table([['Invoice No:','TWO']]).replace('<PAGE>','')
        self.unchanged(first+second)
        self.unchanged(first+'<BLOCK>text[0,0,100,100]<FORK>Invoice No: TWO')

    def test_separate_pages_keep_occurrence_accounting(self):
        _,new=self.predictions(table([['Invoice No:','ONE']])+table([['Invoice No:','TWO']]))
        self.assertEqual([(x['page'],x['value']) for x in new['fields']],[(1,'ONE'),(2,'TWO')])

    def test_active_recognized_data_table_is_untouched(self):
        headers=mapping()['tables'][0]['headers']
        self.unchanged(table([headers,['Invoice No:','ONE','2031-05-04','09:00','10:00','1.00','TEST']]))

    def test_unknown_label_and_inline_blocks_are_untouched(self):
        self.unchanged(table([['Unseen Identifier:','ONE']]))
        self.unchanged('<PAGE><BLOCK>text[0,0,900,900]<FORK>Invoice No: ONE')

    def test_actual_parser_limit_retains_identical_ineligible_denominators(self):
        from baseline import prediction
        raw='<PAGE>'+('<BLOCK>text[0,0,10,10]<FORK>x'*10001)
        expected=load_json(ROOT/'evaluation/synthetic/expected/SYN-WO-01-v0-clean_expected.json')
        reference={'pages':['CPU test reference'],'coverage':{}}
        actual=paired(raw,expected,reference,'completed')
        original=score_document(prediction(raw,mapping()),expected,reference,'completed')
        self.assertEqual(actual['scores']['b0'],original);self.assertEqual(actual['scores']['mapping_v1'],original)
        self.assertEqual(original['parse_errors'],['block_limit']);self.assertFalse(original['eligible_for_exact_credit'])
        self.assertEqual(original['fields']['total'],15);self.assertEqual(original['cells']['total'],19)

    def test_candidate_exception_does_not_change_baseline_comparator(self):
        expected=load_json(ROOT/'evaluation/synthetic/expected/SYN-WO-01-v0-clean_expected.json')
        raw='<PAGE><BLOCK>text[0,0,900,900]<FORK>Work Order ID: '+expected['expected_fields'][0]['printed_text']
        with patch('qualification.mapping_v1.scoring.extract_prediction',side_effect=ValueError('CPU candidate fault')):
            actual=paired(raw,expected,{'pages':['CPU reference'],'coverage':{}},'completed')
        self.assertEqual(actual['scores']['b0']['fields']['correct'],1)
        self.assertEqual(actual['scores']['mapping_v1']['fields']['correct'],0)
        self.assertEqual(actual['scores']['mapping_v1']['fields']['total'],15)


if __name__=='__main__':unittest.main()
