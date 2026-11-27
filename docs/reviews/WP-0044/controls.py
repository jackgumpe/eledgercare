"""Frozen archive and mathematical controls. Uses the original scorer in its normal unmodified entry."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import time
from contract import HERE, read, sha, write

ARCH=HERE.parents[1]/'coordination/WP-0043/native-evidence.json'
ARCH_SHA='66eb8bd4a1d51b813f7de7a846ce841238614017cb9c5970ebd82595a42218bb'

def archived_math(sandbox, seconds=120):
    if sha(ARCH)!=ARCH_SHA:
        raise ValueError('archive checksum')
    archive=read(ARCH)
    rows=archive['retained_rows']
    gaps=[r['final_top_two']['value']-r['final_top_two']['runner_up_value'] for r in rows]
    support=[dict(changed=r['c2_differs_from_c1_at_token_ids'],raw_finite=r['c0_all_finite'],
                  repeat_identical=r['c0_identical_c1'],page_eos_infinite=
                  struct.unpack('<f',bytes.fromhex(r['post_page_eos_fp32le']))[0]==float('-inf'),
                  size=r['copies'][2]['copy_bytes']//4-len(r['c2_differs_from_c1_at_token_ids'])) for r in rows]
    old=archive['offline_scorer']
    cmd=old['normal_command']
    cwd=Path(cmd[2]).parents[3]
    head=subprocess.check_output(['git','-C',str(cwd),'rev-parse','HEAD']).decode().strip()
    if subprocess.check_output(['git','-C',str(cwd),'status','--porcelain','--','docs/research/WP-0043']).strip():
        raise ValueError('historical scorer checkout dirty')
    subprocess.run(['git','-C',str(cwd),'diff','--exit-code',old['source'],head,'--','docs/research/WP-0043'],
                   check=True,stdout=subprocess.DEVNULL)
    run=subprocess.run(cmd,cwd=cwd,capture_output=True,timeout=seconds)
    (sandbox/'archive.stdout').write_bytes(run.stdout)
    (sandbox/'archive.stderr').write_bytes(run.stderr)
    result=json.loads(run.stdout)
    old_evidence=dict(head=head, source=old['source'], command=cmd, returncode=run.returncode,
                      stderr_size=len(run.stderr), bytes=len(run.stdout), stdout=hashlib.sha256(run.stdout).hexdigest(),
                      exact_stdout=hashlib.sha256(run.stdout).hexdigest()==old['stdout_sha256'],
                      exact_record=result==old['verdict'], historical=result)
    pair=rows[0]['final_top_two']
    shifted=[]
    for row in rows:
        z=row['final_top_two']
        pair_z=[z['value'],z['runner_up_value']]
        zp=[v+10 for v in pair_z]
        delta=[b-a for a,b in zip(pair_z,zp)]
        shifted.append(dict(same_winner=zp.index(max(zp))==pair_z.index(max(pair_z)), gap=zp[0]-zp[1],
                            oscillation=max(delta)-min(delta), norm=max(map(abs,delta))))
    def tied(w,j):
        scores={w:pair['value'],j:pair['runner_up_value']+gaps[0]}
        return min(k for k in scores if scores[k]==max(scores.values()))
    def pick(q):
        z=[1-q,q]
        return z.index(max(z))
    return {'archive.gaps':gaps,'archive.support':support,'archive.verdict':old_evidence,
            'math.shift':shifted,'math.tie':dict(gap=gaps[0],unique=False,first=tied(6,1449),reverse=tied(1449,6)),
            'math.signed_zero':dict(equal=0.0==-0.0,plus=struct.pack('<f',0.).hex(),minus=struct.pack('<f',-0.).hex()),
            'math.linked':dict(stock=[pick(0),pick(0)],reset=[pick(0),pick(0)],linked=[pick(0),pick(2)])}
