"""Direct acquisition and authentication of this study's single-member originals."""
import hashlib
import hmac
import os
from pathlib import Path
import secrets
import struct
from contract import write
from predicate import encoded
import win

def members(payload):
    name=b'payload.bin'
    inventory=struct.pack('>III',1,1,len(name))+name+struct.pack('>Q',len(payload))+payload
    return hashlib.sha256(inventory).hexdigest()

def acquired(path):
    h=win.file(path,win.READ,3)
    try:
        return win.ident(h),b''.join(win.chunks(h))
    finally:
        win.checked(win.close(h))

def bind(witness, key):
    r=witness['receipt']
    handle=r['transferred_read_view']
    obj=win.ident(handle)
    payload=b''.join(win.chunks(handle))
    path=Path(witness['output'])
    live_writers=[x for x in witness['events'] if x['kind']=='create' and
                  x['instance']==[r['pid'],r['birth']]]
    sealed={'schema':1,'run':witness['arm'],'instance':[r['pid'],r['birth']],
            'object':obj,'members':members(payload)}
    proof={'writer': bool(live_writers and r['writer_id']==obj and r['denied_at_create']==32
                          and r['started']<=r['finished']),
           'at_seal':win.moment(),'deny_after_exit':win.denied(path)}
    tag=hmac.digest(key,encoded(sealed).encode(),'sha256').hex()
    record=dict(sealed=sealed,proof=proof,tag=tag)
    write(path.parent/'seal.json',record)
    return dict(witness=witness, receipt=record, handle=handle, path=path)


def submit(reference, offered, *, path, key, tag):
    receipt=offered['receipt']
    att=receipt['sealed']
    obj,payload=acquired(path)
    expected_origin=reference['receipt']['sealed']['run']
    expected={'B.origin':expected_origin, 'B.members':members(b'F07\n'), 'B.seal':True,
              'B.protection':True,'B.direct':True,'B.writer':True,'content.bytes':b'F07\n'.hex()}
    observed={'content.bytes':payload.hex(), 'B.members':members(payload)}
    if key is not None:
        verified=hmac.compare_digest(hmac.digest(key,encoded(att).encode(),'sha256').hex(), tag)
        observed['B.seal']=verified
    else:
        verified=None
    if receipt['proof']['writer']:
        observed['B.writer']=True
    # A closed original can have identical file ID and contents after reopening.
    guard=offered['handle']
    if guard is not None and win.ident(guard)==att['object'] and receipt['proof']['deny_after_exit']==32:
        observed['B.protection']=True
        if obj==att['object']:
            observed['B.direct']=True
            if verified:
                observed['B.origin']=att['run']
                if observed['B.members']!=att['members']:
                    observed['B.members']=['seal disagrees',observed['B.members'],att['members']]
    event=dict(acquired_id=obj, referenced_id=att['object'], held=guard is not None,
               verified=verified, time=win.moment(), payload=payload.hex())
    return expected,observed,event
