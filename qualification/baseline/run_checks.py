"""Capture decisive CPU commands on a frozen candidate, including read-access audit."""
import datetime,hashlib,json,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def main():
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    out=ROOT/'docs/evidence/WP-0007/eld-rd-astra'/head[:8];out.mkdir(parents=True,exist_ok=False)
    commands=[['tests/test_baseline.py','-v'],['baseline.py','dev-check','--output',str(out/'dev')]];results=[]
    for i,argv in enumerate(commands,1):
        cmd=[sys.executable,'-I','-B',str(HERE/argv[0]),*argv[1:]]
        cp=subprocess.run(cmd,cwd=ROOT,capture_output=True,timeout=120)
        (out/f'{i:02d}.stdout.txt').write_bytes(cp.stdout);(out/f'{i:02d}.stderr.txt').write_bytes(cp.stderr)
        results.append({'argv':cmd,'exit_code':cp.returncode})
    # Audit actual scoring-side file opens independently of reported counters.
    audit_script=out/'audit_dev_reads.py'
    audit_script.write_text("import sys,json,runpy\nfrom pathlib import Path\nseen=[]\ndef audit(event,args):\n if event=='open' and isinstance(args[0],(str,bytes)):\n  p=str(args[0]).replace('\\\\','/')\n  if '/evaluation/synthetic/' in p:seen.append(p)\nsys.addaudithook(audit)\nsys.path.insert(0,"+repr(str(HERE))+")\nimport baseline\nbaseline.dev_check("+repr(str(out/'audit-dev'))+")\nprint(json.dumps({'opened_synthetic_paths':sorted(set(seen))}))\n",encoding='utf-8',newline='\n')
    cp=subprocess.run([sys.executable,'-I','-B',str(audit_script)],cwd=ROOT,capture_output=True,timeout=120)
    (out/'03.audit.stdout.txt').write_bytes(cp.stdout);(out/'03.audit.stderr.txt').write_bytes(cp.stderr)
    results.append({'argv':[sys.executable,'-I','-B',str(audit_script)],'exit_code':cp.returncode})
    if cp.returncode==0:
        paths=json.loads(cp.stdout.decode().splitlines()[-1])['opened_synthetic_paths']
        sys.path.insert(0,str(HERE));from corpus import fixtures
        allowed=set()
        for f in fixtures():
            if f['split']=='dev':allowed.update(str((ROOT/f[k]).resolve()).replace('\\','/') for k in ('file_path','expected_ground_truth_path','source_record_path'))
        unexpected=[x for x in paths if x not in allowed]
    else:paths=[];unexpected=['audit failed']
    inventory=[]
    for p in sorted(out.rglob('*')):
        if p.is_file():inventory.append({'path':str(p.relative_to(ROOT)).replace('\\','/'),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    record={'candidate':head,'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python':sys.version,'commands':results,
            'synthetic_paths_observed':paths,'unexpected_or_holdout_paths':unexpected,'passed':all(r['exit_code']==0 for r in results) and not unexpected,'inventory':inventory,
            'limitations':['author CPU checks, not independent acceptance','no model/runtime/held-out execution','Q0 scores retrospective only']}
    (out/'checks.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({'candidate':head,'passed':record['passed'],'evidence':str(out),'synthetic_files_observed':len(paths)}));return 0 if record['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
