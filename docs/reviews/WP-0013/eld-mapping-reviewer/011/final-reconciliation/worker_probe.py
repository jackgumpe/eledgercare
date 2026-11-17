"""Actual owned-job worker entry, stopping after real CPU release/pin checks."""
import datetime,json,os,sys,traceback
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import selection_probe as guard  # CPU import denial, audit-event observation.
from qualification.mapping_v2 import runtime,release
from qualification.mapping_v2.process_identity import process_identity
class CpuPinBoundary(Exception):pass
def main():
    c=json.loads(Path(sys.argv[1]).read_bytes());run=Path(c['run'])
    result={'case':c['case'],'identity':process_identity(os.getpid()),'read_release_calls':0,
        'pin_entered':False,'pin_completed':False,'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'job_name':c['job'],'source':c['source'],'runtime_authority':False}
    assert sys.stdin.readline().strip()=='RUN'
    actual_protocol=runtime.protocol
    # Only worker audit storage-root data is substituted with owned CPU scratch.
    def cpu_protocol():
        p=actual_protocol();p['runtime_roots']={**p['runtime_roots'],'reviewer':c['root']};return p
    runtime.protocol=cpu_protocol
    actual_read=runtime.read_release;real_git=release.git;real_pins=release.verify_frozen_mappers
    def fixture_git(*args):
        if args==('show',c['authority']+':'+c['release_path']):return json.dumps(c['fixture']).encode()
        return real_git(*args)
    def pins_stop():
        result['pin_entered']=True;real_pins();result['pin_completed']=True
        raise CpuPinBoundary('CPU-only post-pin stop; no model, plan or corpus continuation')
    def observed_read(*args):
        result['read_release_calls']+=1
        return actual_read(*args,execution=False)
    release.git=fixture_git;release.verify_frozen_mappers=pins_stop;runtime.read_release=observed_read
    try:
        runtime.worker(c['authority'],c['release_path'],'reviewer',c['run'],c['job'])
        result['outcome']='unexpected_return'
    except BaseException as exc:
        traceback.print_exc();result['outcome']='exception'
        result['exception']={'type':type(exc).__name__,'message':str(exc),'winerror':getattr(exc,'winerror',None)}
    result['subprocess_events']=guard.spawn_events;result['blocked_import_attempts']=guard.blocked
    result['forbidden_modules_loaded']=sorted(n for n in sys.modules if any(n==x or n.startswith(x+'.') for x in guard.DENIED))
    if c['case']=='clean':
        result['control_passed']=result['pin_completed'] and result['read_release_calls']==1 and result['exception']['type']=='CpuPinBoundary'
    else:
        result['control_passed']=result['read_release_calls']==0 and not result['pin_entered'] and not guard.spawn_events and result['exception']['type']=='PermissionError' and 'shadowed' in result['exception']['message']
    result['control_passed'] &= not guard.blocked and not result['forbidden_modules_loaded']
    result['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    with (run/'child-receipt.json').open('x',encoding='utf-8',newline='\n') as f:json.dump(result,f,indent=2);f.write('\n')
    return 1  # All paths intentionally stop before the model boundary.
if __name__=='__main__':raise SystemExit(main())
