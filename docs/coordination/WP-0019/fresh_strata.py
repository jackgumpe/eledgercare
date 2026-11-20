"""Summarize fresh controls from the already fixed location labels after blind predictions return."""
import argparse
from collections import Counter
import json
from pathlib import Path


def read(p):return json.loads(p.read_bytes())


def summarize(keys, scored, families):
    output={}
    for fam in families:
        tags=read(keys/fam/'strata.json')['locations']
        fields=read(scored/(fam+'-AB')/'fields.json')
        names=('ordinary','confusable','legitimate_space')
        critical={r['at']:r for r in fields['critical']}
        if {t['at'] for t in tags if t['stratum'] in names}!=set(critical):raise ValueError('critical stratum coverage')
        literal={r['at']:r for kind in ('cells','lines') for r in fields[kind]}
        locations=[t['at'] for t in tags]
        if len(set(locations))!=len(locations):raise ValueError('duplicate stratum locations')
        events={}
        for tag in tags:
            kind,at=tag['stratum'],tag['at']
            row=(critical if kind in names else literal)[at]
            if kind=='legitimate_space' and ' ' not in row['expected']:raise ValueError('missing intended space')
            if kind=='blank' and row['expected']!='':raise ValueError('blank reference mismatch')
            events.setdefault(kind,[]).append(dict(at=at,expected=row['expected'],before=row['before'],after=row['after'],
                before_flag=row['before_flag'],after_flag=row['after_flag'],transition=row['transition'],
                before_correct=row['before_correct'],after_correct=row['after_correct']))
        summary={}
        for label,rows in events.items():
            summary[label]=dict(total=len(rows),control_correct=sum(r['before_correct'] for r in rows),
                treatment_correct=sum(r['after_correct'] for r in rows),transitions=dict(Counter(r['transition'] for r in rows)),
                observed_changes=[r['at'] for r in rows if r['before']!=r['after']],new_flags=[r['at'] for r in rows if r['after_flag'] and not r['before_flag']])
        output[fam]=dict(summary=summary,locations=events)
    return output


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--keys',type=Path,required=True);p.add_argument('--scored',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    result=summarize(args.keys,args.scored,('LIFT','VALVE'))
    with args.out.open('x',encoding='utf8',newline='\n') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps({f:v['summary'] for f,v in result.items()}))
