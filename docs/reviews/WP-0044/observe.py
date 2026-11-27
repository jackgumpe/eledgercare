"""Read-only event collection from a debugger-created inert process tree; no attach or memory operations."""
import ctypes as ct
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from contract import HERE, read, write
import win


def observe(launcher, sandbox, env, alpha, *, assigned_job=None, comparison_job=None):
    sandbox.mkdir()
    write(sandbox/'control.json',{'supervisor':os.getpid()})
    argv=[str(launcher),'-B',str(HERE/'worker.py')]
    job=assigned_job or win.checked(win.create_job(None,None))
    limits=ct.create_string_buffer(144)
    win.checked(win.query_job(job,9,limits,len(limits),None))
    flags=int.from_bytes(limits.raw[16:20],'little')
    entries=[]
    try:
        with (sandbox/'stderr.txt').open('wb') as err, (sandbox/'stdout.txt').open('wb') as out:
            p=subprocess.Popen(argv, cwd=sandbox, env=env, creationflags=1|0x08000000,
                               stdin=subprocess.DEVNULL, stdout=out, stderr=err)
        # Process creation debugging suspends at the initial event, before user-mode code.
        deadline=time.monotonic()+30
        anchor=[p.pid,win.birth(int(p._handle))]
        live=set()
        while True:
            event=win.Event()
            if time.monotonic()>deadline:
                raise TimeoutError('owned fixture exceeded 30 seconds')
            if not win.wait_debug(win.ref(event),1000):
                if ct.get_last_error()==121:
                    continue
                raise ct.WinError(ct.get_last_error())
            kind,pid,tid=event.kind,event.pid,event.tid
            status=0x00010002
            now=win.moment()
            if kind==3:
                data=event.data.create
                live.add(pid)
                if pid==p.pid:
                    win.checked(win.assign(job,int(p._handle)))
                img={}
                if data.file:
                    try:
                        img.update(digest=win.digest(data.file), id=win.ident(data.file))
                    except OSError as exc:
                        img['winerror']=exc.winerror
                    finally:
                        win.close(data.file)
                entries.append(dict(kind='create',pid=pid,instance=[pid,win.birth(data.proc)],
                                    image=img, job=win.member(data.proc,job), when=now,
                                    comparison_job=win.member(data.proc,comparison_job) if comparison_job else None,
                                    competing_image_write=win.denied(launcher) if pid==p.pid else None))
            elif kind==5:
                live.discard(pid)
                entries.append(dict(kind='exit',pid=pid,code=int.from_bytes(event.data.raw[:4],'little'),when=now))
            elif kind==6 and event.data.create.file:
                win.close(event.data.create.file)
            elif kind==1:
                code=int.from_bytes(event.data.raw[:4],'little')
                if code not in (0x80000003,0x4000001F):
                    status=0x80010001
            win.checked(win.cont(pid,tid,status))
            if kind==5 and not live:
                break
        rc=p.wait(timeout=2)
        if rc:
            raise RuntimeError(f'fixture failed rc={rc}: {(sandbox/"stderr.txt").read_text(errors="replace")}')
        receipt=read(sandbox/'receipt.json')
        witness=dict(anchor=anchor, flags=flags, events=entries, receipt=receipt,
                     arm=alpha, command=argv, output=str(sandbox/'payload.bin'))
        write(sandbox/'observer.json',witness)
        return witness
    except BaseException:
        win.end_job(job,1)
        raise
    finally:
        if assigned_job is None:
            win.close(job)
