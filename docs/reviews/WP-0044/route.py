"""Reviewer normal entry. Private output is append-only per invocation directory."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import secrets
import sys
import time
import uuid
from contract import HERE, projection, read, sha, write
from controls import archived_math, ARCH, ARCH_SHA
from custody import bind, submit
from observe import observe
from predicate import PHASE, score
import win

SPACE=Path.home()/'eLedgerCare-Speed/WP-0044/eld-rd-reviewer'
VENV=SPACE/'venv'
LAUNCH=VENV/'Scripts/python.exe'
BASE=Path(sys._base_executable)
SCHEDULE=HERE.parents[1]/'coordination/WP-0044/schedule.json'
SOURCES={'L.image':'launcher CREATE_PROCESS_DEBUG_INFO.hFile digest and file ID',
         'I.image':'interpreter CREATE_PROCESS_DEBUG_INFO.hFile digest and file ID',
         'E.launcher':'supervisor Popen process handle and GetProcessTimes matched to process-create event',
         'E.parent':'worker getppid has inherited parent PID; create-event source lacks creating caller',
         'E.order':'launch and interpreter create debug events before observed launcher exit on one dispatcher',
         'E.instance':'writer process GetProcessTimes/PID against process-create debug handle',
         'E.job':'IsProcessInJob during create events; job flags and admission before initial continuation',
         'A.script':'effective worker script read under study-held file protection',
         'A.args':'worker sys.orig_argv tail',
         'B.writer':'inert hashed sole writer opens CREATE_NEW noninheritable share READ; only duplicate is consented read-only export; write denied 32',
         'B.seal':'HMAC-SHA256 over canonical finalized supervisor receipt checked with independent scorer key access',
         'B.protection':'originating kernel file object held via read-view across writer close; sharing violation before/after',
         'B.direct':'scorer opens submitted file, compares own volume/index against continuously held original',
         'B.origin':'authenticated run and interpreter mapping joined to verified originally held member',
         'B.members':'schema 1 count and sorted unique single UTF-8 name with network-order lengths and full bytes',
         'content.bytes':'separate scorer ReadFile, exact four bytes'}
SOURCES.update({k:'in-worker configuration projection immediately before original creation' for k in PHASE if k.startswith('C.')})

def env():
    return {k:os.environ[k] for k in ('SYSTEMROOT','WINDIR','TEMP','TMP') if k in os.environ}

def img(path):
    h=win.file(path,win.READ,1)
    try:
        return dict(digest=win.digest(h), id=win.ident(h))
    finally:
        win.close(h)

def manifest():
    if sys.version_info[:3]!=(3,12,10):
        raise ValueError('CPython version differs')
    return dict(base=img(BASE),launcher=img(LAUNCH), version=sys.version,
                script=sha(HERE/'worker.py'), args=['-B',str(HERE/'worker.py')], schedule=sha(SCHEDULE),
                config=projection(VENV,[VENV/'Lib/site-packages'],None,env()),
                files={p.name:sha(p) for p in sorted(HERE.glob('*.py'))},
                archive=ARCH_SHA)

def process_maps(man,selected,actual):
    receipt=actual['receipt']
    creates=[e for e in actual['events'] if e['kind']=='create']
    launcher=next(e for e in creates if e['instance']==actual['anchor'])
    worker=next(e for e in creates if e['pid']==receipt['pid'] and e['instance'][1]==receipt['birth'])
    end=next(e for e in actual['events'] if e['kind']=='exit' and e['pid']==launcher['pid'])
    ref={'L.image':man['launcher'],'I.image':man['base'],'E.launcher':selected['anchor'],
         'E.instance':worker['instance'],'E.order':True,'E.job':True,'E.parent':actual['anchor'],
         'A.args':man['args'],'A.script':man['script'],**man['config']}
    o={'E.launcher':actual['anchor'],'E.instance':[receipt['pid'],receipt['birth']],
       'E.order':launcher['when']<=worker['when']<end['when'],
       'E.job':all(e['job' if selected is actual else 'comparison_job'] is True for e in (worker,launcher))
               and actual['flags'] & 0x1800==0,
       'A.args':receipt['original_argv'][1:],'A.script':receipt['script'],**receipt['config']}
    for k,event in [('L.image',launcher),('I.image',worker)]:
        if {'digest','id'}<=event['image'].keys():
            o[k]=event['image']
    return ref,o

def rows_live(run,man):
    key=secrets.token_bytes(32)
    (run/'private-key').write_bytes(key)
    jobs=[]; guards=[]; pair=[]
    records={}
    try:
        for path in [LAUNCH,BASE,*sorted(HERE.glob('*.py'))]:
            guards.append(win.file(path,win.READ,1))
        for arm in ('A','B'):
            job=win.checked(win.create_job(None,None))
            jobs.append(job)
            ob=observe(LAUNCH,run/arm,env(),str(uuid.uuid4()),assigned_job=job,comparison_job=jobs[0] if arm=='B' else None)
            pair.append(bind(ob,key))
        a,b=pair
        def evaluate(case, selected, process, expected_output, offered, path, verification, tag):
            ref,o=process_maps(man,selected['witness'],process['witness'])
            br,bo,ev=submit(expected_output,offered,path=path,key=verification,tag=tag)
            neutral=dict(expected={**ref,**br},observed={**o,**bo},sources=SOURCES)
            result=score(neutral)
            result['acquisition']=ev
            result['submission_input']=neutral
            records[case]=result
        def ordinary(case,selected,actual,reference,received):
            evaluate(case,selected,actual,reference,received,received['path'],key,received['receipt']['tag'])
        ordinary('W1.A',a,a,a,a)
        ordinary('W1.B',b,b,b,b)
        ordinary('W2.other',a,b,b,b)
        ordinary('W4.denied',a,a,a,a)
        evt=next(e for e in a['witness']['events'] if e['kind']=='create' and e['instance']==a['witness']['anchor'])
        records['W4.denied']['denied']={'error':evt['competing_image_write'],'file':evt['image'],'when':evt['when']}
        ordinary('B1.original',a,a,a,a)
        ordinary('B2.other',a,a,a,b)
        detached=run/'detached.bin'
        detached.write_bytes(a['path'].read_bytes())
        tag=a['receipt']['tag']
        evaluate('B3.copy',a,a,a,a,detached,key,tag)
        evaluate('B4.invalid',a,a,a,a,detached,key,format(int(tag,16)^1,'064x'))
        evaluate('B4.unavailable',a,a,a,a,detached,None,tag)
        win.checked(win.close(a['handle']))
        a['handle']=None
        ordinary('B5.reopen',a,a,a,a)
        return records
    finally:
        for arm in pair:
            if arm['handle'] is not None:
                win.close(arm['handle'])
        for h in guards+jobs:
            win.close(h)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('mode', choices=['manifest','run'])
    p.add_argument('--out', required=True,type=Path)
    p.add_argument('--manifest',type=Path)
    p.add_argument('--inputs',type=Path)
    ns=p.parse_args()
    frozen=manifest()
    if ns.mode=='manifest':
        write(ns.out, frozen)
        return
    if ns.out.exists() or read(ns.manifest)!=frozen:
        raise ValueError('non-fresh output or manifest discrepancy')
    ns.out.mkdir()
    start=time.monotonic()
    schedule=read(SCHEDULE)['rows']
    digests=read(ns.inputs)
    staged=SPACE/'blind'
    for row in schedule:
        if row['interface']=='constructed':
            case=row['id']
            if sha(staged/(case+'.json'))!=digests[case]:
                raise ValueError('constructed input pin '+case)
    records=rows_live(ns.out,frozen)
    write(ns.out/'native.json',records)
    for row in schedule:
        if row['interface']=='constructed':
            case=row['id']
            records[case]=score(read(staged/(case+'.json')))
    write(ns.out/'predictions.json',records)
    records.update(archived_math(ns.out,seconds=max(1,290-int(time.monotonic()-start))))
    write(ns.out/'all.json',records)
    files=sum(f.stat().st_size for f in ns.out.rglob('*') if f.is_file())
    summary=dict(seconds=time.monotonic()-start,bytes=files,rows=len(records),
                 native_tree_processes=sum(len([e for e in read(ns.out/arm/'observer.json')['events'] if e['kind']=='create'])
                                           for arm in ('A','B')),permitted_rows=[r['id'] for r in schedule])
    write(ns.out/'resources.json',summary)
    if set(records)!={r['id'] for r in schedule} or summary['seconds']>300 or files>64*2**20 or summary['native_tree_processes']>12:
        raise RuntimeError('schedule/resource discrepancy')
if __name__=='__main__':
    main()
