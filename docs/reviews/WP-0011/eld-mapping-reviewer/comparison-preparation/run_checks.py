"""CPU preparation checks only; original failed attempts are never overwritten."""
import contextlib
import datetime
import json
from pathlib import Path
import sys
import traceback
import unittest

OWN=Path(__file__).resolve().parent;sys.path.insert(0,str(OWN))
import compare_published as c

def main():
    out=(OWN/sys.argv[1]).resolve();out.relative_to(OWN)
    c.require(not out.exists() and not c.git('status','--porcelain').strip(),'Freeze helper first; new attempt only')
    out.mkdir(parents=True)
    result={'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'executing_head':c.git('rev-parse','HEAD').decode().strip(),
            'accepted_source':c.SOURCE,'accepted_tree':c.TREE,'protocol_sha256':c.PROTOCOL,'python':sys.version,
            'scope':'CPU helper readiness only. All run packets are explicitly public synthetic fixtures; no actual WP11 run/corpus material read.'}
    try:
        c.require(c.sha((c.ROOT/'qualification/coverage_v1/protocol.json').read_bytes())==c.PROTOCOL,'Protocol changed')
        source=c.source_inventory()
        for path in [*sorted(OWN.glob('*.py')),OWN/'README.md',OWN/'.gitattributes',OWN.parent/'source/probes_v2.py',
                     c.ROOT/'docs/reviews/WP-0009/eld-mapping-reviewer/008/preparation/compare_published.py']:
            data=path.read_bytes();source.append({'path':path.relative_to(c.ROOT).as_posix(),'bytes_working':len(data),'sha256_working':c.sha(data),
                                                 'git_blob':c.git('rev-parse','HEAD:'+path.relative_to(c.ROOT).as_posix()).decode().strip()})
        with (out/'stdout.txt').open('x',encoding='utf-8',newline='') as stdout,(out/'stderr.txt').open('x',encoding='utf-8',newline='') as stderr:
            with contextlib.redirect_stdout(stdout),contextlib.redirect_stderr(stderr):
                tests=unittest.TextTestRunner(stream=stderr,verbosity=2).run(unittest.defaultTestLoader.discover(str(OWN),pattern='test_compare.py'))
        result['tests']={'run':tests.testsRun,'failures':len(tests.failures),'errors':len(tests.errors),'skipped':len(tests.skipped)}
        with (out/'input-inventory.json').open('x',encoding='utf-8',newline='\n') as f:json.dump({'files':source},f,indent=2);f.write('\n')
        c.require(tests.wasSuccessful(),'Preparation helper checks failed')
        result['status']='PASS'
    except BaseException:
        result['status']='FAIL';result['traceback']=traceback.format_exc();raise
    finally:
        result['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
        with (out/'execution.json').open('x',encoding='utf-8',newline='\n') as f:json.dump(result,f,indent=2);f.write('\n')
        print(json.dumps(result,indent=2))
if __name__=='__main__':main()
