"""Apply the preregistered rules to verified crossover results. Repeats contribute time, not new labels."""
import argparse
import json
from pathlib import Path


def read(path):
    return json.loads(path.read_bytes())


def decide(stage,root,verify,families):
    verified=read(verify)
    result={}
    all_time={arm:0.0 for arm in ('A','B')}
    for family in families:
        checks=verified[family]
        if [v['order'] for v in checks]!=['AB','BA']:raise ValueError('both orders required')
        scored=[read(root/(family+'-'+order)/'summary.json') for order in ('AB','BA')]
        if scored[0]!=scored[1]:raise ValueError(f'{family}: ordered score/fields differ')
        s=scored[0]
        crit=s['transitions']['critical']
        if stage==1 and crit['total']!={'H':19,'A':252}[family]:raise ValueError('incomplete exposed critical denominator')
        pages=checks[0]['pages']
        total={arm:sum(v['elapsed_s'][arm] for v in checks) for arm in ('A','B')}
        for arm in all_time:all_time[arm]+=total[arm]
        timing=dict(perOrder=[{key:v[key] for key in ('order','elapsed_s','pages_per_min','added_ms_per_page')} for v in checks],
                    perFamilyPooledSecondsPerPass={arm:secs/2 for arm,secs in total.items()},
                    pooledPagesPerMinute={arm:120*pages/secs for arm,secs in total.items()},
                    addedMsPerPage=1000*(total['B']-total['A'])/(2*pages))
        result[family]=dict(uniquePages=pages,critical=crit,gains=s['critical_recoveries'],regressions=s['critical_regressions'],
            newlyWrongUnflagged=s['newly_wrong_unflagged'],explicitBlankCells=s['explicitBlankCells'],
            cropComparisons=checks[0]['stats'],cropsPerPage=checks[0]['crops_per_page'],timing=timing)
    n=sum(v['uniquePages'] for v in result.values());g=sum(len(v['gains']) for v in result.values());l=sum(len(v['regressions']) for v in result.values())
    speed=120*n/all_time['B']; wrong_before=sum(v['critical']['total']-v['critical']['before_correct'] for v in result.values())
    blanks_ok=all(not row['explicitBlankCells']['observations_changed'] for row in result.values())
    qualifies=g-l>=1 and l==0
    if stage==1:outcome='GO_STAGE_2' if qualifies else 'NO_GO_CLOSE_AT_STAGE_1'
    elif wrong_before==0 and l==0:outcome='INCONCLUSIVE_FRESH_CONTROL_CEILING'
    else:outcome='RECOMMEND_LARGER_RESEARCH_TRIAL' if qualifies and blanks_ok and speed>=30 else 'FRESH_PROMOTION_CRITERIA_NOT_MET'
    return dict(stage=stage,decision=outcome,uniquePages=n,totalGains=g,totalRegressions=l,netCriticalRecovery=g-l,
                baselineWrongCritical=wrong_before,allExplicitBlankObservationsPreserved=blanks_ok,
                pooledTreatmentPagesPerMinute=speed,pooledAddedMsPerPage=1000*(all_time['B']-all_time['A'])/(2*n),
                timingMethod='Both timed orders. Throughput is the total number of measured treatment pages divided by the sum of their elapsed times. Count unique fields once.',
                families=result)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stage',type=int,choices=(1,2),required=True)
    p.add_argument('--scored',type=Path,required=True);p.add_argument('--verified',type=Path,required=True)
    p.add_argument('--families',nargs=2,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();v=decide(a.stage,a.scored,a.verified,a.families)
    with a.out.open('x',encoding='utf8',newline='\n') as dest:
        json.dump(v,dest,indent=2);dest.write('\n')
    print(json.dumps({k:v[k] for k in ('stage','decision','totalGains','totalRegressions','pooledTreatmentPagesPerMinute','pooledAddedMsPerPage')}))
