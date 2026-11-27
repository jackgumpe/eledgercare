"""Exercise monotonic final-worker receipts and actual parent termination with harmless CPU children."""
import datetime as dt
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch


CHILD = """
from pathlib import Path
import os, sys, time
root=Path(sys.argv[2])
sys.path.insert(0,sys.argv[1])
from timing import mark
mode=sys.argv[3]
sys.stdin.readline()
(root/'interpreter.pid').write_text(str(os.getpid()))
mark(root,'load')
for phase in ('F01.warmup','F07.warmup','F01.warm1','F07.warm1'):
    mark(root,phase)
    if phase=='F07.warm1':
        if mode=='exit_between_polls':
            time.sleep(.45)
        elif mode in ('stderr_stall','live','expires'):
            for i in range(180):
                print(i,file=sys.stderr,flush=True)
                time.sleep(.02)
        elif mode=='end_files':
            for i in range(10):
                (root/('file'+str(i))).touch()
        elif mode=='untouched_progress':
            mark(root,phase,16)
        elif mode=='bad_progress':
            mark(root,phase,32)
        elif mode=='observed_progress':
            mark(root,phase,16)
            mark(root,phase,32)
if mode!='missing_finish':
    mark(root,'finished')
if mode=='truncated':
    with (root/'phase').open('ab') as out:
        out.write(b'[123,')
"""


def main(src, work):
    sys.path.insert(0,str(src))
    import native
    import psutil
    work.mkdir()
    results=[]
    scenarios=(('inside','untouched'),('exit_between_polls','untouched'),('live','untouched'),
               ('stderr_stall','observed'),('expires','observed'),('end_files','untouched'),
               ('untouched_progress','untouched'),('bad_progress','observed'),('observed_progress','observed'),
               ('missing_finish','untouched'),('truncated','observed'))
    for mode,arm in scenarios:
        root=work/mode
        root.mkdir()
        folder=root/arm
        limits=dict(native.LIMITS,poll_s=1,load_s=10,call_s=.25,stall_s=.8)
        if mode=='stderr_stall':
            limits.update(poll_s=.15,call_s=20,stall_s=.25)
        if mode=='expires':
            limits.update(call_s=30,stall_s=30)
        if mode=='end_files':
            limits.update(files=8)
        lease={'lease_id':'independent-harmless-cpu','end_utc':(dt.datetime.now(dt.timezone.utc)+
               dt.timedelta(seconds=.6 if mode=='expires' else 30)).isoformat()}
        argv=[str(native.PYTHON),'-B','-u','-c',CHILD,str(src),str(folder),mode]
        start=time.monotonic()
        with patch.object(native,'OUT',root),patch.object(native,'LIMITS',limits),patch.object(native,'device_check',return_value={}):
            try:
                native.supervise(arm,argv,lease,start)
                outcome='finished'
            except Exception as exc:
                outcome=f'{type(exc).__name__}: {exc}'
            partial_count=len(native.partial_inventory())
        phase=folder/'phase'
        rows=phase.read_bytes().splitlines() if phase.exists() else []
        stamps=[json.loads(x) for x in rows if x.endswith(b']')]
        final=[x[0] for x in stamps if x[1]=='finished']
        entry=[x[0] for x in stamps if x[1]=='F07.warm1' and x[2]==0]
        pidfile=folder/'interpreter.pid'
        child_gone=pidfile.exists() and not psutil.pid_exists(int(pidfile.read_text()))
        results.append({'scenario':mode,'arm':arm,'outcome':outcome,'elapsed_s':round(time.monotonic()-start,3),
                        'observed_call_s':round((final[0]-entry[0])/1e9,6) if final and entry else None,
                        'partial_inventory_count':partial_count,'stderr_bytes':(folder/'stderr.log').stat().st_size,
                        'surviving_interpreter':not child_gone,'journal_entries':len(rows)})
    print(json.dumps(results,indent=2))
    for row in results:
        assert (row['outcome']=='finished')==(row['scenario'] in ('inside','observed_progress')),row
        assert not row['surviving_interpreter'],row


if __name__=='__main__':
    main(Path(sys.argv[1]),Path(sys.argv[2]))
