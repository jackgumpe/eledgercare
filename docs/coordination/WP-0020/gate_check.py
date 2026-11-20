"""Recompute the three immutable prediction arms and the serial budget from pinned archive timings."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
SCORER=ROOT/"docs/evaluation/WP-0015/score.py"
SCORE_SHA="1ceb36fe922ef63ea8cd9b2dc2ff55b48abe1193bb818430ddb1531f364f4bf7"

def digest(raw):return hashlib.sha256(raw).hexdigest()
def read(path):return json.loads(path.read_bytes())
def write(path,obj):
    raw=(json.dumps(obj,indent=2)+"\n").encode()
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and path.read_bytes()!=raw:raise ValueError(f"Existing evidence differs: {path}")
    path.write_bytes(raw)
def index(score,kind):return {row["at"]:row for pg in score["pages"] for row in pg[kind]}
def flip(a,b):return ("R" if a["correct"] else "W")+("R" if b["correct"] else "W")

def verify(scratch,archive,out):
    assert digest(SCORER.read_bytes())==SCORE_SHA
    freeze=read(ROOT/"docs/coordination/WP-0020/predictions-freeze.json")
    admission=read(ROOT/"docs/coordination/WP-0020/scoring-admission.json")
    result={}
    for family in ("H","A"):
        snap=freeze["families"][family]
        route=scratch/"frozen"/family/"prediction.json"
        assert digest(route.read_bytes())==snap["predictionSha256"]
        truth=scratch/"keys"/family/"truth.json"
        win=scratch/"windows"/family/"prediction.json"
        native=scratch/"baselines"/family/"native.json"
        scores={}
        for arm,path in (("windows",win),("native",native),("routed",route)):
            dest=scratch/"coordinator"/"scores"/family/(arm+".json")
            dest.parent.mkdir(parents=True,exist_ok=True)
            subprocess.run([sys.executable,"-B",str(SCORER),str(truth),str(path),"--out",str(dest)],
                           check=True,stdout=subprocess.DEVNULL)
            scores[arm]=read(dest)
            assert scores[arm]["packet_complete"],scores[arm]["faults"]
        critical={k:index(v,"critical") for k,v in scores.items()}
        assert critical['windows'].keys()==critical['native'].keys()==critical['routed'].keys()
        counts={key:0 for key in ['RR','WR','RW','WW']}
        upper={key:0 for key in counts}
        witnesses=[]
        for addr,base in critical['windows'].items():
            after=critical['routed'][addr];neural=critical['native'][addr]
            counts[flip(base,after)]+=1;upper[flip(base,neural)]+=1
            if base['correct']!=after['correct']:
                witnesses.append(dict(at=addr,expected=base['expected'],windows=base['observed'],native=neural['observed'],routed=after['observed']))
        flags={}
        for kind in ('cells','lines'):
            a=index(scores['windows'],kind);b=index(scores['routed'],kind)
            assert a.keys()==b.keys()
            flags[kind]=[x for x in a if a[x]['correct'] and not b[x]['correct']]
        manifest=read(scratch/'manifest'/family/'manifest.json')
        pin=admission[family]
        root=archive/'runs'/pin['run']
        def timing(path):
            raw=(root/path).read_bytes()
            assert digest(raw)==pin['verifiedFiles'][path]
            return json.loads(raw)
        def duration(meta):
            return (meta['document_committed_ns']-meta['accepted_ns'])/1e9
        wfolder=f'04-{family.lower()}-windows';nfolder=f'03-{family.lower()}-native'
        wt=timing(wfolder+'/timing.json');nt=timing(nfolder+'/timing.json')
        window_data=[]
        for start in manifest['selected_windows']:
            wi=timing(f'{nfolder}/window-{start:03d}.json')
            begin=wi['engine_begin_ns'];end=wi['engine_end_ns']
            assert nt['accepted_ns']<=begin<=end<=nt['document_committed_ns']
            window_data.append(dict(start=start,pages=wi['pages'],beginNs=begin,endNs=end,engineSeconds=(end-begin)/1e9))
        chronological=sorted(window_data,key=lambda w:w['beginNs'])
        assert all(a['endNs']<=b['beginNs'] for a,b in zip(chronological,chronological[1:]))
        engine=sum(x['engineSeconds'] for x in window_data)
        available=pin['availableWindows']
        n=sum(len(w['pages']) for w in available)
        wall=duration(wt);budget=n*2
        assert abs(wall-wt['elapsed_s'])<1e-5 and abs(duration(nt)-nt['elapsed_s'])<1e-5
        full_set={w['start'] for w in available}==set(manifest['selected_windows'])
        result[family]=dict(criticalTransitions=counts,correctedNativeAgainstWindowsUpperBound=upper,
            criticalWitnesses=witnesses,previouslyCorrectNowWrongLocations=flags,
            scorerHashes={k:digest((scratch/"coordinator"/"scores"/family/(k+".json")).read_bytes()) for k in scores},
            scoreCounts={k:v['counts'] for k,v in scores.items()},pages=n,
            availableWindows=len(available),requestedWindows=len(window_data),windowCosts=window_data,
            observedWindowsSeconds=wall,observedNativeFullDocumentSeconds=duration(nt),selectedEngineSeconds=engine,
            totalBudgetSeconds=budget,remainingAfterWindowsSeconds=budget-wall,
            modeledSerialWindowsPlusSelectedEngineSeconds=wall+engine,
            modeledSumOfDocumentClocksSeconds=wall+duration(nt) if full_set else None,
            costDisposition="over budget" if wall+engine>budget else "cost unknown")
        assert (upper['WR'],upper['RW'])==({'H':(6,0),'A':(60,3)}[family])
    write(out,result)

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('scratch','archive','out'):p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args();verify(args.scratch,args.archive,args.out)
