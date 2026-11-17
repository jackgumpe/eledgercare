"""Frozen /009 CPU orchestration, including exact independent public probes.

Reviewer functions are executed unchanged with attribution; their original main
pins the old source, so this owned adapter supplies new output/source bindings.
No private input, model, renderer or live observer is used.
"""
import datetime
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[5]
sys.path.insert(0,str(ROOT))
from qualification.coverage_v1.common import git,sha,write,HERE

INDEPENDENT='c23a2f0cff3621f05fe1caa77b170167a2406876'
HELPER='docs/reviews/WP-0011/eld-mapping-reviewer/source/probes_v2.py'

def main():
    out=Path(sys.argv[1]).resolve();out.relative_to(Path(__file__).parent)
    assert not out.exists() and not git('status','--porcelain').strip(),'Freeze source/helper; use a new attempt'
    started=datetime.datetime.now(datetime.timezone.utc).isoformat();head=git('rev-parse','HEAD').decode().strip()
    command=[sys.executable,'-I','-B','qualification/coverage_v1/run_checks.py','--out',str((out/'author-suite').relative_to(ROOT))]
    run=subprocess.run(command,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    out.mkdir(parents=True,exist_ok=True)
    (out/'stdout.txt').write_bytes(run.stdout);(out/'stderr.txt').write_bytes(run.stderr)
    receipt={'source_commit':head,'source_tree':git('rev-parse','HEAD:qualification/coverage_v1').decode().strip(),
             'helper_sha256':sha(Path(__file__).read_bytes()),'protocol_sha256':sha((HERE/'protocol.json').read_bytes()),
             'started_utc':started,'author_suite_command':command,'author_suite_exit':run.returncode}
    passed=False
    if run.returncode==0:
        original=git('show',INDEPENDENT+':'+HELPER)
        assert (ROOT/HELPER).read_bytes()==original,'Independent helper changed'
        spec=importlib.util.spec_from_file_location('independent_wp11_public_probes',ROOT/HELPER)
        probes=importlib.util.module_from_spec(spec);spec.loader.exec_module(probes)
        scratch=ROOT/'.scratch/wp0011-coverage-correction';scratch.mkdir(parents=True,exist_ok=True)
        result={'independent_helper_commit':INDEPENDENT,'helper_path':HELPER,'helper_sha256':sha(original),
            'visible':probes.visible_probes(),'contract':probes.contract_probes(),
            'supervisor':[probes.supervisor_probe(case,scratch) for case in ('nonzero_return','timeout_row','wrong_device','empty_capture')],
            'score_state':probes.score_state_probe(scratch)}
        write(out/'independent-probes.json',result)
        passed=all(row['pass'] for group in ('visible','contract','supervisor') for row in result[group]) and result['score_state']['pass']
        receipt['independent_probes_pass']=passed
        previous=json.loads((ROOT/'docs/research/WP-0011/eld-mapping-author/001/attempt-2/summary.json').read_text())
        current=json.loads((out/'author-suite/summary.json').read_text())
        receipt['historical_accounting_comparison']={key:{'prior':previous[key],'corrected':current[key],'equal':previous[key]==current[key]}
            for key in ('original_primary_full_scores_reproduced','exposed_wp9_full_predictions_scores_reproduced','separate_recovery_reproduced',
                        'primary_documents','completed_primary_documents','expected_field_cell_slots','presence_eligible_slots','presence_unavailable_slots','flags_nonexclusive')}
    receipt['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();receipt['exit_code']=0 if passed else 1
    write(out/'execution.json',receipt);print(json.dumps(receipt,indent=2));return receipt['exit_code']

if __name__=='__main__':raise SystemExit(main())
