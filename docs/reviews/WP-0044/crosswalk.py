"""Schema translation of sealed returns. This module accepts no expected-output input."""
import argparse
import json
from pathlib import Path
import subprocess

AUTHOR='f3c59b478d4b6ce19dc7dd32ae68ad663a8ee29c'
REVIEW='dae70e25d8d03896d7757fd55044c030bf221880'

def blob(ref,path):
    return json.loads(subprocess.check_output(['git','show',ref+':'+path]))

def write(path,obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')

def decimal(x):
    return format(x,'.15g')

SUB={'E.launcher':'anchor_mismatch','E.parent':'parent_mismatch','E.instance':'instance_mismatch',
     'E.order':'order_violation','E.job':'containment_escape','B.writer':'writer_conflict',
     'B.seal':'seal_invalid','B.origin':'other_run','B.members':'members_inconsistent',
     'A.script':'command_mismatch','A.args':'command_mismatch','I.image':'image_mismatch','L.image':'image_mismatch'}
UNKNOWN={'B.writer':'writer_unobserved','B.seal':'seal_unverified','B.direct':'direct_acquisition_unobserved',
         'B.origin':'origin_unbound','B.protection':'protection_gap','B.members':'members_unobserved'}

def diag(a):
    k=a['key']
    status=a.get('state',a.get('status'))
    label=a.get('subtype',a.get('reason'))
    source=a['source']
    if isinstance(source,dict):
        source=source.get('method',source)
    if source=='measurement absent at prescribed cut':
        source=None
    methods={'supervisor Popen process handle and GetProcessTimes matched to process-create event':'process_instance_key',
             'scorer opens submitted file, compares own volume/index against continuously held original':'scorer_handle_identity',
             'authenticated run and interpreter mapping joined to verified originally held member':'receipt_mapping',
             'authenticated protected-object registry joined by volume serial and file index':'receipt_mapping',
             'HMAC-SHA256 over canonical finalized supervisor receipt checked with independent scorer key access':'receipt_authentication',
             'HMAC-SHA256 verifier on reference receipt':'receipt_authentication'}
    if isinstance(source,str):
        source=methods.get(source,source)
    if status=='U' and label=='unresolved':
        typ='unobserved'
    elif status=='M' and label in ('mismatch','wrong_origin','unauthorized_writer','integrity'):
        typ='config_mismatch' if k.startswith('C.') else SUB.get(k,label)
        if k=='E.job' and source!='job_membership_query':
            typ='different_selected_job'
    else:
        typ=label
    return dict(key=k,coordinate=k.split('.')[0],phase=a['phase'],subtype=typ,source=source)

def provenance(route,k,row,arms,rev_events):
    author=route=='author'
    v=row['verdict'] if author else row
    atoms=[x for x in v['atoms'] if x['status']!='P'] if author else v['diagnostics']
    converted={x['key']:diag(x) for x in atoms}
    conflicts=v['conflicts' if author else 'conflict']
    missing=v['missing']
    c=set(conflicts); m=set(missing)
    bmiss=m & UNKNOWN.keys()
    if c & {'B.writer','B.seal','B.members','B.protection'}:
        cls='integrity'
    elif c & {'B.origin','B.direct'}:
        cls='wrong_origin'
    elif bmiss:
        cls='unresolved'
    else:
        cls='verified'
    # Preserve the frozen frontier. A phase-only tie expands to all same-phase diagnoses.
    keys=v['earliest'] if author else [x['key'] for x in atoms if x['phase'] in v['earliest']]
    kinds={'conflict' if x in c else 'missing' for x in keys}
    phases={converted[x]['phase'] for x in keys}
    first=None if not keys else dict(kind=next(iter(kinds)) if len(kinds)==1 else 'mixed',
                                    phase=next(iter(phases)) if len(phases)==1 else sorted(phases),keys=sorted(keys))
    extras={}
    if k in ('W1.A','W1.B'):
        if author:
            worker=arms[k=='W1.B']['process']['worker']
            distinct=worker['orig_argv0']!=worker['executable']
        else:
            role=rev_events[k[-1]]['image_roles']
            distinct=role['orig_argv0_is_base'] and role['reported_executable_is_venv']
        if distinct and v['coordinates']['L']==v['coordinates']['I']=='P':
            extras['executable_roles']='distinct_approved_launcher_and_interpreter'
    elif k=='W2.other':
        pairs=([a['process']['instances'] for a in arms] if author else
               [[a['anchor'],[a['process']['pid'],a['process']['birth']]] for a in rev_events.values()])
        extras['instance_pairs_retained']=len(pairs)
    elif k=='W4.denied':
        err=arms[0]['process']['denied']['winerror'] if author else row['denied']['error']
        if err==32:
            extras['competing_access']=dict(denied=True,filesystem_mutation=False)
    return dict(id=k,**{field:v[field] for field in ('coordinates','custody','joint','content')},
                origin={'class':cls,'unresolved':sorted(UNKNOWN[x] for x in bmiss)},
                conflicts=[converted[x] for x in conflicts],missing=[converted[x] for x in missing],
                earliest=first,extras=extras)

def archive(route,k,r):
    if k=='archive.gaps':
        return {'gaps':list(map(decimal,r)),'min_gap':decimal(min(r)),'min_gap_row':r.index(min(r)),
                'half_min_gap':decimal(min(r)/2)}
    if k=='archive.support':
        is_author=route=='author'
        sets=[v['excluded' if is_author else 'changed'] for v in r]
        size=[v['allowed' if is_author else 'size'] for v in r]
        out=dict(rows=len(r),excluded_ids_per_row=sets,only_eos_excluded_all_rows=all(v==[1] for v in sets))
        if len(set(size))==1:
            out.update(support_size=size[0],vocabulary=size[0]+len(sets[0]))
        if not is_author:
            out.update(c0_all_finite_all_rows=all(v['raw_finite'] for v in r),
                       c0_identical_c1_all_rows=all(v['repeat_identical'] for v in r))
            if all(v['page_eos_infinite'] for v in r):
                out.update(excluded_value='-inf',excluded_word_le='000080ff')
        return out
    if route=='author':
        return dict(verdict=r['joint'],argv_conflicts=r['argv0_conflicts'],
                    row_verdicts=r['row_verdicts'],scheduled_rows=r['scheduled_rows'],complete_rows=r['qualified_rows'],
                    qualified_rows=f"{r['qualified_rows']}/{r['scheduled_rows']}",
                    qualified_pairs=f"{r['qualified_pairs']}/{r['scheduled_pairs']}",
                    F07_target_pairs_matched='1/1' if r['target_document_equal'] else '0/1')
    # The full original score was emitted as bytes, hashed in the blind record.
    # Use the exact published byte-equivalent parsed verdict only if the freeze confirms it.
    old=blob(REVIEW,'docs/coordination/WP-0043/native-evidence.json')['offline_scorer']
    assert r['exact_record'] and r['exact_stdout'] and r['stdout']==old['stdout_sha256']
    score=old['verdict']; a=score['conflicts']; missing=score['missing']
    differences=[[i for i,(x,y) in enumerate(zip(v['expected'],v['observed'])) if x!=y] for v in a]
    return dict(verdict=score['verdict'],first_divergent_phase=score['first_divergent_phase'],
                conflict_keys=score['conflict_keys'],missing_keys=score['missing_keys'],argv_conflicts=len(a),
                argv_conflict_fields=sorted({v['field'] for v in a}),argv_differs_only_at_index=differences,
                argv_tails_equal=all(v['expected'][1:]==v['observed'][1:] for v in a),
                argv_workers=[v['observed'][-1] for v in a],
                expected_argv0_is_venv_scripts=all(v['expected'][0].replace('\\','/').endswith('/venv/Scripts/python.exe') for v in a),
                observed_argv0_is_base_python312=all(v['observed'][0].replace('\\','/').endswith('/Python312/python.exe') for v in a),
                missing_rows=[v['row'] for v in missing],missing_phase=sorted({v['phase'] for v in missing}),
                row_verdicts=[v['verdict'] for v in score['rows']],scheduled_rows=score['scheduled_rows'],
                complete_rows=score['complete_rows'],qualified_rows='/'.join(map(str,r['qualified'])),
                qualified_pairs='/'.join(map(str,r['pairs'])),public_verdict=score['public_verdict'])

def math_row(route,k,r):
    author=route=='author'
    if k=='math.linked':
        if author:
            f=r['first']
            stock=reset=[f,r['reset']]
            linked=[f,r['linked']]
            # Initial linked and reset states both use the exact same measured logits(0).
            m={'linked_scores':[[decimal(v) for v in r[n]] for n in ('reset_scores','linked_scores')]}
        else:
            stock,reset,linked=r['stock'],r['reset'],r['linked']
            m={}
        return dict(stock_tokens=stock,reset_tokens=reset,linked_tokens=linked,reset_pass=reset==stock,
                    linked_pass=linked==stock,first_linked_divergence_step=next((i for i,(x,y) in enumerate(zip(stock,linked)) if x!=y),None),**m)
    if k=='math.shift' and author:
        return [dict(winner_before=r['old'],winner_after=r['new'],winner_changed=r['old']!=r['new'],
                     omega=decimal(r['oscillation']),linf=decimal(r['linf']),gap=decimal(r['gap']))]
    if k=='math.shift':
        return [dict(winner_changed=not v['same_winner'],omega=decimal(v['oscillation']),linf=decimal(v['norm']),
                     gap=decimal(v['gap'])) for v in r]
    if k=='math.tie' and author:
        return [dict(winner_before=r[key]['before'],winner_after=r[key]['after'],unique_after=r['unique'],gap=decimal(r['gap']))
                for key in ('higher_id_competitor','lower_id_competitor')]
    if k=='math.tie':
        return [dict(winner_after=r[key],unique_after=r['unique'],gap=decimal(r['gap'])) for key in ('first','reverse')]
    # Only the single scalar pair was measured. Preserve its scope without adding reversed argmax observations.
    plus=r['positive' if author else 'plus']; minus=r['negative' if author else 'minus']
    return [dict(values=['0.0','-0.0'],sign_bits=[int.from_bytes(bytes.fromhex(v),'little')>>31 for v in (plus,minus)],
                 numerically_equal=r['equal'],bytes_equal=plus==minus)]

def main():
    p=argparse.ArgumentParser()
    p.add_argument('destination',type=Path)
    ns=p.parse_args()
    ns.destination.mkdir(exist_ok=True)
    author=blob(AUTHOR,'docs/research/WP-0044/blind-results.json')
    reviewer=blob(REVIEW,'docs/reviews/WP-0044/blind-results.json')
    events=blob(REVIEW,'docs/reviews/WP-0044/native-events.json')
    schedule=blob(REVIEW,'docs/coordination/WP-0044/schedule.json')['rows']
    for name,data in [('author',author['rows']),('reviewer',reviewer)]:
        rows=[]
        for item in schedule:
            k,interface=item['id'],item['interface']
            r=data[k]
            if interface in ('live','constructed'):
                row=provenance(name,k,r,author['arms'],events)
            else:
                val=r['value'] if name=='author' else r
                method=archive if interface=='archive' else math_row
                row={'id':k,'result':method(name,k,val)}
            rows.append(dict(interface=interface,**row))
        write(ns.destination/(name+'-observed.json'),{'rows':rows})
if __name__=='__main__':
    main()
