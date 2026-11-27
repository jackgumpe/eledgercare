"""Observe creation events only for our freshly debug-created, inert supervisor tree."""
import ctypes as ct
import os
from pathlib import Path
import subprocess
import time
from common import BASE, HERE, ordinary, clean_env, save, win


def observe(path):
    token = ordinary()
    job = win.checked(win.create_job(None,None))
    events=[]
    try:
        limits=ct.create_string_buffer(144)
        win.checked(win.query_job(job,9,limits,len(limits),None))
        job_flags=int.from_bytes(limits.raw[16:20],"little")
        argv=[str(BASE),"-I","-S","-B",str(HERE/"supervisor.py")]
        with (path/"supervisor-stderr.txt").open("wb") as err:
            proc=subprocess.Popen(argv,cwd=path,env=clean_env(),creationflags=1|8,
                                  stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=err)
        anchor=[proc.pid,win.birth(int(proc._handle))]
        deadline=time.monotonic()+27
        active=set()
        while True:
            event=win.Event()
            if time.monotonic()>=deadline:
                raise TimeoutError("owned tree budget")
            if not win.wait_debug(win.ref(event),500):
                if ct.get_last_error()==121:
                    continue
                raise ct.WinError(ct.get_last_error())
            kind,pid,tid=event.kind,event.pid,event.tid
            code=0x00010002
            when=win.moment()
            if kind==3:
                item=event.data.create
                if pid==proc.pid:
                    win.checked(win.assign(job,int(proc._handle)))
                active.add(pid)
                image=None
                if item.file:
                    try:
                        image=dict(sha256=win.digest(item.file),id=win.ident(item.file))
                    finally:
                        win.checked(win.close(item.file))
                actualpid=win.fn("GetProcessId",win.DWORD,win.H)(item.proc)
                events.append(dict(kind="create",pid=pid,tid=tid,
                                   instance=[actualpid,win.birth(item.proc)],
                                   image=image,job=win.member(item.proc,job),when=when))
            elif kind==5:
                active.remove(pid)
                events.append(dict(kind="exit",pid=pid,code=int.from_bytes(event.data.raw[:4],"little"),when=when))
            elif kind==6 and event.data.create.file:
                win.close(event.data.create.file)
            elif kind==1 and int.from_bytes(event.data.raw[:4],"little") not in (0x80000003,0x4000001F):
                code=0x80010001
            win.checked(win.cont(pid,tid,code))
            if kind==5 and not active:
                break
        exitcode=proc.wait(1)
        result=dict(token=token,anchor=anchor,argv=argv,job_flags=job_flags,events=events,exitcode=exitcode)
        save(path/"events.json",result)
        if exitcode:
            raise RuntimeError(f"supervisor exit {exitcode}; see private stderr")
        return result
    except BaseException:
        win.end_job(job,1)
        raise
    finally:
        win.close(job)

