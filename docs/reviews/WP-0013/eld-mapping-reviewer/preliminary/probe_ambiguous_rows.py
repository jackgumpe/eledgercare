"""Public counterexample for proposal2202551 empty/partially-known original-score rows."""
import argparse
import datetime
import json
from pathlib import Path
import sys
import traceback
sys.path.insert(0,str(Path(__file__).resolve().parent))
import probe_boundaries as prior

PROPOSAL='220255145162c29e20fe1fe10634a0b36336fa80'
COLS=['part_sku','part_desc','bin_loc','qty_used']
VALUES=['PUB-0042','Generic item','A-01','2.00']
def expected(cells):
    e=prior.expected();e['expected_fields']=[]
    e['expected_tables']=[{'table_id':'stock_parts','column_ids':COLS,'rows':[{'row_id':'PUBLIC-ROW','page_number':1,'cells':cells}]}]
    return e
def cell(value,kind='text'):return {'printed_text':value,'normalized_value':value,'value_type':kind}
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);a=p.parse_args()
    report={'schema':'eld-wp13-proposal-row-counterexample/1','status':'FAILED','proposal':PROPOSAL,
            'helper_commit':prior.git('rev-parse','HEAD').decode().strip(),
            'helper_sha256':prior.sha(Path(__file__).read_bytes()),'prior_helper_sha256':prior.sha(Path(prior.__file__).read_bytes()),
            'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':[],
            'scope':'Original immutable score behavior, not a new scorer. Generic public values only; no corpus or mapper changes.'}
    try:
        report['inputs']=[]
        for name in ('catalog.json','INTERFACE.md','POLICY.md'):
            path='qualification/mapping_v2/protocol/'+name;data=prior.git('show',PROPOSAL+':'+path)
            report['inputs'].append({'commit':PROPOSAL,'path':path,'bytes':len(data),'sha256':prior.sha(data)})
        report['legacy_inputs']=prior.identities()
        header=['Part SKU','Part Description','Bin','Qty Used'];raw=prior.table([header,VALUES])
        cases=[('empty_truth_row_with_no_prediction',prior.text('Generic public note'),{},0,1),
               ('partially_known_row_means_known_subset',raw,{'part_sku':cell(VALUES[0],'identifier')},1,0),
               ('fully_known_row_positive_control',raw,{k:cell(v,'decimal_2' if k=='qty_used' else 'text') for k,v in zip(COLS,VALUES)},4,0)]
        for name,native,cells,total,missing in cases:
            result=prior.pair(native,expected(cells));row={'name':name,'evidence':prior.compact(result),
                'known_reference_cells':len(cells),'declared_schema_columns':len(COLS),'status':'FAIL'};report['checks'].append(row)
            for score in result['scores'].values():
                prior.require(score['rows']['correct']==score['rows']['total']==1,'Expected original row credit')
                prior.require(score['cells']['correct']==score['cells']['total']==total and score['cells']['missing_rows']==missing,'Known-cell/missing-row counts changed')
            row['original_rows']={k:v['rows'] for k,v in result['scores'].items()};row['status']='PASS'
        report['status']='PASS'
    except Exception:report['error']=traceback.format_exc()
    report['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();prior.write(a.out,report)
    print(json.dumps({'status':report['status'],'checks':len(report['checks'])}));return 0 if report['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
