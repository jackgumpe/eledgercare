"""Run the locked scorer with no input to the OCR process and compare every reference location."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCORER = ROOT / 'docs/evaluation/WP-0015/score.py'
DIGEST = '1ceb36fe922ef63ea8cd9b2dc2ff55b48abe1193bb818430ddb1531f364f4bf7'
TRANSITIONS = ('wrong_to_right','right_to_wrong','wrong_to_wrong','right_to_right')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def save(path, obj):
    with path.open('x',encoding='utf8',newline='\n') as handle:
        json.dump(obj,handle,indent=2,ensure_ascii=True)
        handle.write('\n')


def classify(before, after):
    return ('right' if before else 'wrong')+'_to_'+('right' if after else 'wrong')


def keyed(result, kind):
    items = [(row['at'],row) for page in result['pages'] for row in page[kind]]
    if len(dict(items)) != len(items):
        raise ValueError('duplicate '+kind)
    return dict(items)


def run_pair(truth_path, original, treatment, out):
    out.mkdir(parents=True,exist_ok=False)
    if sha(SCORER) != DIGEST:
        raise ValueError('scorer bytes differ from freeze')
    arms={}
    for label,file in [('A',original),('B',treatment)]:
        scored = out/(label+'-score.json')
        command=[sys.executable,'-B',str(SCORER),str(truth_path),str(file),'--out',str(scored)]
        subprocess.run(command,check=True,stdout=subprocess.DEVNULL)
        record=read(scored)
        if not record['packet_complete']:
            raise ValueError(f'{label} incomplete: {record["faults"]}')
        arms[label]=dict(file=file,score=record,score_sha256=sha(scored))
    a,b=[arms[k]['score'] for k in ('A','B')]
    if (a['family'],a['source_sha256'],a['observed_order']) != (b['family'],b['source_sha256'],b['observed_order']):
        raise ValueError('unmatched arm identities')
    ledger={}
    counts={}
    for kind in ('critical','cells','lines'):
        before,after=keyed(a,kind),keyed(b,kind)
        if before.keys()!=after.keys():
            raise ValueError('scoring lost keys in '+kind)
        rows=[]
        for loc,x in before.items():
            y=after[loc]
            if x['expected']!=y['expected']:raise ValueError(loc)
            transition=classify(x['correct'],y['correct'])
            rows.append(dict(at=loc,expected=x['expected'],before=x['observed'],after=y['observed'],
                             before_correct=x['correct'],after_correct=y['correct'],before_flag=x.get('flagged'),
                             after_flag=y.get('flagged'),transition=transition))
        ledger[kind]=rows
        c=Counter(row['transition'] for row in rows)
        counts[kind]=dict(total=len(rows),before_correct=sum(row['before_correct'] for row in rows),
             after_correct=sum(row['after_correct'] for row in rows),**{k:c[k] for k in TRANSITIONS})
    crit=ledger['critical']
    blanks=[row for row in ledger['cells'] if row['expected']=='']
    wrongs=[row for row in crit if row['transition']=='right_to_wrong']
    result=dict(family=a['family'],source_sha256=a['source_sha256'],truth_sha256=sha(truth_path),scorer_sha256=DIGEST,
        arms={label:dict(prediction_sha256=sha(arm['file']),score_sha256=arm['score_sha256'],counts=arm['score']['counts'],
                         faults=arm['score']['faults']) for label,arm in arms.items()},
        transitions=counts,explicitBlankCells=dict(total=len(blanks),before_correct=sum(x['before_correct'] for x in blanks),
          after_correct=sum(x['after_correct'] for x in blanks),newly_wrong=[row['at'] for row in blanks if row['transition']=='right_to_wrong'],
          observations_changed=[row['at'] for row in blanks if row['before']!=row['after']]),
        critical_recoveries=[row['at'] for row in crit if row['transition']=='wrong_to_right'],critical_regressions=[row['at'] for row in wrongs],
        newly_wrong_unflagged=[row['at'] for row in wrongs if not row['after_flag']],
        unflagged_wrong_locations_new_to_set=[row['at'] for row in crit if not row['after_correct'] and not row['after_flag'] and (row['before_correct'] or row['before_flag'])])
    save(out/'fields.json',ledger)
    result['field_ledger_sha256']=sha(out/'fields.json')
    save(out/'summary.json',result)
    print(json.dumps({'family':a['family'],'critical':counts['critical'],'regressions':len(wrongs),'blanks':result['explicitBlankCells']}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('truth','control','treated','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args()
    run_pair(a.truth,a.control,a.treated,a.out)
