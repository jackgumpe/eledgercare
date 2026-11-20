"""Run the frozen warm crossover plan serially on one host. Labels never enter this command."""
import argparse
import datetime
import hashlib
import json
import msvcrt
import os
from pathlib import Path
import subprocess
import sys
import time


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as data:
        for chunk in iter(lambda:data.read(1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()


def git(root,*args):
    return subprocess.check_output(['git','-C',str(root),*args],text=True,encoding='utf8').strip()


def save(path, value):
    with path.open('x',encoding='utf8',newline='\n') as handle:
        json.dump(value,handle,indent=2)
        handle.write('\n')
        handle.flush()
        os.fsync(handle.fileno())


def run(args):
    if digest(args.plan)!=args.expected_sha256:raise ValueError('release plan identity')
    plan=json.loads(args.plan.read_bytes())
    if git(args.code,'rev-parse','HEAD')!=plan['candidate']:raise ValueError('worktree revision')
    policy='docs/research/WP-0019/astra'
    worker='docs/research/WP-0019/carbon'
    legacy='docs/research/WP-0015/astra'
    for path in (policy,worker,legacy):
        if git(args.code,'status','--porcelain','--',path):raise ValueError('modified candidate '+path)
    for family,source in plan['manifests'].items():
        f=Path(source['path'])
        if digest(f)!=source['sha256']:raise ValueError('manifest hash '+family)
        data=json.loads(f.read_bytes())
        if (len(data['pages']),data['family'])!=(source['pages'],family):raise ValueError('manifest shape')
        for page in data['pages']:
            if digest(Path(page['bmp']))!=page['bmp_sha256']:raise ValueError(f'{family}/{page["page"]} BMP bytes')
    args.out.mkdir(parents=True,exist_ok=False)
    results=[]
    with args.lock.open('a+b') as lock:
        lock.seek(0)
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        try:
            for item in plan['runs']:
                family,order=item['family'],item['order']
                if order not in ('AB','BA'):raise ValueError(order)
                dest=args.out/(family+'-'+order)
                command=[sys.executable,'-B',str(args.code/policy/'run.py'),'--manifest',plan['manifests'][family]['path'],
                         '--order',order,'--out',str(dest),'--engine-dir',str(args.code/worker)]
                begin=datetime.datetime.now(datetime.timezone.utc).isoformat()
                mark=time.perf_counter()
                env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES='')
                print(f'Beginning {family}-{order}',flush=True)
                with (args.out/(family+'-'+order+'.stdout')).open('xb') as so,(args.out/(family+'-'+order+'.stderr')).open('xb') as se:
                    outcome=subprocess.run(command,cwd=args.code,stdout=so,stderr=se,env=env)
                receipt=dict(family=family,order=order,command=command,startUtc=begin,endUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    exit=outcome.returncode,wrapperSeconds=time.perf_counter()-mark)
                if not outcome.returncode:
                    required=['receipt.json','A/prediction.json','B/prediction.json']
                    required.extend(f'{arm}/page-{n:03d}.json' for arm in ('A','B') for n in range(1,plan['manifests'][family]['pages']+1))
                    receipt['outputs']={name:digest(dest/name) for name in required}
                results.append(receipt)
                save(args.out/(family+'-'+order+'.bound.json'),receipt)
                print(f'Finished {family}-{order}, exit {outcome.returncode}',flush=True)
                if outcome.returncode:raise RuntimeError(f'runner failed in {dest}; see retained stderr')
        finally:
            lock.seek(0)
            msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)
    save(args.out/'return.json',dict(candidate=plan['candidate'],planSha256=args.expected_sha256,runs=results))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for opt in ('plan','code','out','lock'):p.add_argument('--'+opt,type=Path,required=True)
    p.add_argument('--expected-sha256',required=True)
    run(p.parse_args())
