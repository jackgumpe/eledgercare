"""Freeze-first CPU helper checks and exact source/helper identity receipt."""
import contextlib
import json
from pathlib import Path
import sys
import traceback
import unittest

OWN=Path(__file__).resolve().parent;sys.path.insert(0,str(OWN))
import execute_wrapper as w
def main():
    out=OWN/'preparation-attempt-1'
    assert not out.exists() and not w.git('status','--porcelain').strip(),'Freeze before new attempt'
    out.mkdir();result={'started_utc':w.now(),'helper_head':w.git('rev-parse','HEAD').decode().strip(),'scope':'CPU preparation; only owned standard-library test children and temporary fixtures',
                        'accepted_source':w.SOURCE,'accepted_tree':w.TREE,'protocol_sha256':w.PROTOCOL,'python':sys.version}
    try:
        assert w.git('rev-parse','HEAD:qualification/coverage_v1').decode().strip()==w.TREE
        assert w.sha((w.ROOT/'qualification/coverage_v1/protocol.json').read_bytes())==w.PROTOCOL
        comparison='docs/reviews/WP-0011/eld-mapping-reviewer/comparison-preparation/compare_published.py'
        assert w.git('show','55412990da2af89761979536b0add815e21e492a:'+comparison)==(w.ROOT/comparison).read_bytes()
        paths=[*sorted(OWN.glob('*.py')),OWN/'.gitattributes',OWN/'README.md',w.ROOT/comparison]
        inputs=[{**w.identity(path),'git_blob':w.git('rev-parse','HEAD:'+path.relative_to(w.ROOT).as_posix()).decode().strip()} for path in paths]
        with (out/'stdout.txt').open('x',encoding='utf-8',newline='') as stdout,(out/'stderr.txt').open('x',encoding='utf-8',newline='') as stderr:
            with contextlib.redirect_stdout(stdout),contextlib.redirect_stderr(stderr):
                tests=unittest.TextTestRunner(stream=stderr,verbosity=2).run(unittest.defaultTestLoader.discover(str(OWN),pattern='test_preparation.py'))
        result['tests']={'run':tests.testsRun,'failures':len(tests.failures),'errors':len(tests.errors),'skipped':len(tests.skipped)}
        w.write(out/'input-inventory.json',{'files':inputs});assert tests.wasSuccessful()
        result['status']='PASS'
    except BaseException:result['status']='FAIL';result['error']=traceback.format_exc();raise
    finally:
        result['finished_utc']=w.now();w.write(out/'execution.json',result);print(json.dumps(result,indent=2))
if __name__=='__main__':main()
