"""Post-opening, offline checks on the exact input files, frozen returned predicates and private receipts."""
import hashlib
import hmac
import json
from pathlib import Path
import struct
import subprocess
import sys

ROOT=Path.home()/'eLedgerCare-Speed/WP-0044'
REV=ROOT/'eld-rd-reviewer'
ORIG=ROOT/'eld-owner-probe/decisive-v1'
OWN=REV/'decisive01'
WORK=Path(__file__).resolve().parent
def read(p):
    return json.loads(p.read_bytes())
def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    pkg=REV/'opening'
    cert=read(pkg/'fixtures/oracle-commitment.json')
    pins={k:digest(pkg/k)==v['sha256'] and (pkg/k).stat().st_size==v['bytes'] for k,v in cert['sealed_files'].items()}
    author=json.loads(subprocess.check_output(['git','show','f3c59b478d4b6ce19dc7dd32ae68ad663a8ee29c:docs/research/WP-0044/blind-results.json']))
    reviewer=read(WORK/'blind-results.json')
    comparisons={}
    for row in read(pkg/'fixtures/manifest.json')['rows']:
        if row['interface']!='constructed':
            continue
        key=row['id'];inp=REV/'blind'/(key+'.json')
        cor=lambda p:json.loads(subprocess.check_output([sys.executable,'-B',*map(str,p),str(inp)]))
        comparisons[key]={'input_bytes':digest(inp)==row['input']['sha256'],
                          'author':cor([pkg/'author/probe.py','score'])==author['rows'][key]['verdict'],
                          'reviewer':cor([WORK/'predicate.py'])==reviewer[key]}
    stored={}
    for role,root,keyfile in [('author',ORIG,'hmac.key'),('reviewer',OWN,'private-key')]:
        secret=(root/keyfile).read_bytes()
        receipts=[]
        for label in (('first','second') if role=='author' else ('A','B')):
            folder=root/label
            data=read(folder/('supervision.json' if role=='author' else 'seal.json'))
            sealed=data['sealed']
            msg=json.dumps(sealed,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(',',':')).encode()
            original=root/(label+'-result.bin') if role=='author' else folder/'payload.bin'
            payload=original.read_bytes()
            if role=='author':
                name=b'result.bin'
                checked=sealed['members']==[dict(name=name.decode(),length=len(payload),sha256=hashlib.sha256(payload).hexdigest())]
            else:
                name=b'payload.bin'
                checked=sealed['members']==hashlib.sha256(struct.pack('>III',1,1,len(name))+name+struct.pack('>Q',len(payload))+payload).hexdigest()
            receipts.append(dict(arm=label,tag_verified=hmac.compare_digest(hmac.digest(secret,msg,'sha256').hex(),data['tag']),
                                 exact_four_bytes=payload==b'F07\n',member_commitment=checked,
                                 object=sealed['object'],instance=sealed['instance']))
        stored[role]=receipts
    results={'sealed_file_hashes_and_sizes':pins,'oracle_regenerated':digest(pkg/'expected.json')==digest(pkg/'recreated.json'),
             'fixture_inputs_and_rerun_predicates':comparisons,'closed_artifact_checks':stored,
             'archive_stdout_verified':digest(OWN/'archive.stdout')==reviewer['archive.verdict']['stdout']}
    assert all(pins.values()) and results['oracle_regenerated'] and results['archive_stdout_verified']
    assert all(all(x.values()) for x in comparisons.values())
    assert all(all(row[k] for k in ('tag_verified','exact_four_bytes','member_commitment')) for a in stored.values() for row in a)
    output=WORK/'comparison/offline-checks.json'
    output.write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8',newline='\n')
    print('verified',len(comparisons)*2,'offline scorer returns and',sum(map(len,stored.values())),'archived HMAC/byte/member receipts')
if __name__=='__main__':
    main()
