"""Actual Windows lookup controls in a qualified restricted CPU child."""
import datetime,hashlib,importlib.abc,json,os,shutil,subprocess,sys,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[6]
sys.path[:0]=[str(ROOT),str(ROOT/'qualification/q0/harness')]
DENIED=('torch','transformers','pypdfium2','PIL','triton','q0harness.backend_torch',
        'q0harness.render','q0harness.session','q0harness.supervisor','q0harness.telemetry','q0harness.procmem')
blocked=[];spawn_events=[]
class NoModel(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if any(fullname==x or fullname.startswith(x+'.') for x in DENIED):
            blocked.append(fullname);raise AssertionError('Forbidden model/renderer import: '+fullname)
sys.meta_path.insert(0,NoModel())
def observe(event,args):
    if event=='subprocess.Popen':
        spawn_events.append({'executable':str(args[0]),'argv':args[1],'cwd':str(args[2])})
sys.addaudithook(observe)
from qualification.mapping_v2.process_identity import process_identity
def main():
    config=json.loads(Path(sys.argv[1]).read_bytes());run=Path(config['run'])
    receipt={'case':config['case'],'source':config['source'],'identity':process_identity(os.getpid()),
        'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'parent_current_directory':str(Path.cwd()),
        'requested_pin_git_cwd':str(ROOT),'initial_path':os.environ['PATH'],
        'explicit_git':os.environ['Q0_GIT_EXECUTABLE'],'gate_returned':False,'pins_completed':False,
        'stage':'waiting_owned_parent','runtime_authority':False}
    assert sys.stdin.readline().strip()=='RUN'
    try:
        from qualification.mapping_v2.runtime import enable_pinned_git_lookup
        from qualification.mapping_v2.common import verify_frozen_mappers
        receipt['stage']='candidate_environment_gate'
        old=dict(os.environ)
        new=enable_pinned_git_lookup(dict(old),root=Path(config['root']),owner='reviewer',run_dir=run)
        receipt['gate_returned']=True
        receipt['changed_environment']={k:{'before':old.get(k),'after':new.get(k)} for k in set(old)|set(new) if old.get(k)!=new.get(k)}
        os.environ.clear();os.environ.update(new)
        receipt['which_git_after_gate']=shutil.which('git')
        receipt['stage']='actual_frozen_pins'
        verify_frozen_mappers()
        receipt['pins_completed']=True;receipt['outcome']='actual_pins_completed'
    except BaseException as exc:
        traceback.print_exc()
        receipt['outcome']='exception'
        receipt['exception']={'type':type(exc).__name__,'message':str(exc),'winerror':getattr(exc,'winerror',None)}
    receipt['spawn_events']=spawn_events
    receipt['blocked_import_attempts']=blocked
    receipt['forbidden_modules_loaded']=sorted(n for n in sys.modules if any(n==x or n.startswith(x+'.') for x in DENIED))
    receipt['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    # A negative fixture is safe either if the gate rejects before pin launch,
    # or actual pin commands complete using the trusted installation. Invalid PE
    # failure from actual pins demonstrates late/unbound selection, not safety.
    clean=config['case']=='clean'
    rejected=(not receipt['gate_returned'] and receipt['stage']=='candidate_environment_gate'
              and receipt.get('exception',{}).get('type') in ('Q0Failure','PermissionError','ValueError','RuntimeError')
              and not spawn_events)
    receipt['control_passed']=receipt['pins_completed'] if clean else (receipt['pins_completed'] or rejected)
    receipt['control_passed'] &= not blocked and not receipt['forbidden_modules_loaded']
    with (run/'child-receipt.json').open('x',encoding='utf-8',newline='\n') as f:json.dump(receipt,f,indent=2);f.write('\n')
    return 0 if receipt['pins_completed'] else 1
if __name__=='__main__':raise SystemExit(main())
