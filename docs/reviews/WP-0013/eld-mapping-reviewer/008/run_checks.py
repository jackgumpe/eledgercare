"""Run only comparison-helper readiness checks; no source-suite rerun or actual runtime read."""
import contextlib,datetime,json,sys,traceback,unittest
from pathlib import Path
OWN=Path(__file__).resolve().parent;sys.path.insert(0,str(OWN))
import compare_published as c
def main():
    out=(OWN/sys.argv[1]).resolve();out.relative_to(OWN)
    c.require(not out.exists() and not c.git('status','--porcelain').strip(),'Freeze helper first; use a new retained attempt')
    out.mkdir(parents=True)
    result={'schema':'eld-wp13-008-comparison-preparation/1','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'executing_head':c.git('rev-parse','HEAD').decode().strip(),'source':c.SOURCE,'source_tree':c.TREE,'protocol_sha256':c.PROTOCOL,'python':sys.version,'scope':'Only generic public synthetic comparison packets; no actual WP13 inference or actual-run artifact read.'}
    try:
        c.require(c.sha((c.ROOT/'qualification/mapping_v2/runtime_protocol.json').read_bytes())==c.PROTOCOL,'Protocol changed')
        source=c.source_inventory()
        route=json.loads((OWN/'sentinel-route.json').read_text())
        c.require(route['schedule']==c.schedule(c.protocol(),'reviewer') and route['max_document_calls']==3 and route['cold_loads']==1 and route['retries']==0 and route['first_failure_stop'] is True,'Fixed sentinel route changed')
        c.require(route['source_tree']==c.TREE and route['protocol_sha256']==c.PROTOCOL and route['corpus_commit']==c.CORPUS and route['corpus_tree']==c.CORPUS_TREE,'Route bindings changed')
        c.require(Path(route['runtime_root']).resolve()==Path(c.protocol()['runtime_roots']['reviewer']).resolve(),'Reviewer root changed')
        for path in [*sorted(OWN.glob('*.py')),OWN/'README.md',OWN/'.gitattributes',OWN/'sentinel-route.json',OWN/'start.json',
                     c.ROOT/'docs/reviews/WP-0013/eld-mapping-reviewer/protocol-review/public_examples.py',
                     c.ROOT/'docs/reviews/WP-0011/eld-mapping-reviewer/comparison-preparation/compare_published.py']:
            data=path.read_bytes();relative=path.relative_to(c.ROOT).as_posix();source.append({'path':relative,'bytes_working':len(data),'sha256_working':c.sha(data),'git_blob':c.git('rev-parse','HEAD:'+relative).decode().strip()})
        with (out/'stdout.txt').open('x',encoding='utf-8',newline='') as stdout,(out/'stderr.txt').open('x',encoding='utf-8',newline='') as stderr:
            with contextlib.redirect_stdout(stdout),contextlib.redirect_stderr(stderr):
                tests=unittest.TextTestRunner(stream=stderr,verbosity=2).run(unittest.defaultTestLoader.discover(str(OWN),pattern='test_compare.py'))
        result['tests']={'run':tests.testsRun,'failures':len(tests.failures),'errors':len(tests.errors),'skipped':len(tests.skipped)}
        with (out/'input-inventory.json').open('x',encoding='utf-8',newline='\n') as f:json.dump({'files':source},f,indent=2);f.write('\n')
        c.require(tests.wasSuccessful(),'Comparison readiness checks failed')
        result['status']='PASS'
    except BaseException:
        result['status']='FAIL';result['failure']=traceback.format_exc()
    finally:
        result['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
        with (out/'execution.json').open('x',encoding='utf-8',newline='\n') as f:json.dump(result,f,indent=2);f.write('\n')
        print(json.dumps(result,indent=2))
    return int(result['status']!='PASS')
if __name__=='__main__':raise SystemExit(main())
