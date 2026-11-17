"""Correct two reviewer-only expected target IDs; preserve the original frozen probe/results."""
import argparse
import datetime
import json
from pathlib import Path
import sys
import traceback
sys.path.insert(0,str(Path(__file__).resolve().parent))
import probe_boundaries as prior

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);a=p.parse_args()
    report={'schema':'eld-wp13-reviewer-invoice-target-recheck/1','status':'FAILED',
            'helper_commit':prior.git('rev-parse','HEAD').decode().strip(),
            'helper_sha256':prior.sha(Path(__file__).read_bytes()),
            'original_helper_sha256':prior.sha(Path(prior.__file__).read_bytes()),
            'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'correction':'Original two fallback probes used expected invoice_no instead of canonical invoice_number. Structural assertions passed; their unrelated unmatched-target scores are not evidence of canonical invoice accuracy. Only the corrected records below are used for those slot metrics.',
            'checks':[]}
    try:
        report['legacy_inputs']=prior.identities()
        for name,rows,value in [('duplicate_guard_falls_back',[['Invoice No:','PUB-0042'],['Invoice No:','PUB-9999']],'Invoice No:'),
                                ('ambiguous_orientation_falls_back',[['Invoice No:','PUB-0042'],['OTHER','MORE']],'OTHER')]:
            result=prior.pair(prior.table(rows),prior.expected('invoice_number'))
            row={'name':name,'evidence':prior.compact(result),'status':'FAIL'};report['checks'].append(row)
            for pred in result['predictions'].values():
                prior.require(len(pred['fields'])==1 and pred['fields'][0]['field_id']=='invoice_number' and pred['fields'][0]['value']==value,'Canonical fallback identity/value changed')
            for score in result['scores'].values():
                prior.require(score['fields']['total']==1 and score['fields']['correct']==0 and score['fields']['unmatched_candidates']==0,'Correct canonical denominator/candidate accounting')
            prior.require(result['predictions']['mapping_v1']['fields'][0].get('association')!='immediate_right_neighbor','Expected guarded-path rejection')
            row['status']='PASS'
        report['status']='PASS'
    except Exception:report['error']=traceback.format_exc()
    report['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();prior.write(a.out,report)
    print(json.dumps({'status':report['status'],'checks':len(report['checks'])}));return 0 if report['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
