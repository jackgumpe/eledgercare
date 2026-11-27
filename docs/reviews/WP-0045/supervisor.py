"""Trusted current-user caller. One explicit CreateProcessW of the absolute base image."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import ctypes as ct
import hashlib
import hmac
import os
import secrets
import subprocess
from ctypes import wintypes as wt
from common import BASE, HOME, HERE, clean_env, ordinary, read, save, sha, stream_inventory, win, worker_command
from clauses import encoded


class Info(ct.Structure):
    _fields_=[("process",win.H),("thread",win.H),("pid",wt.DWORD),("tid",wt.DWORD)]


def run():
    token=ordinary()
    request=read("input.json")
    actual_caller=[os.getpid(),win.birth(win.process())]
    nonce=secrets.token_hex(16)
    sel=request["selection"]
    save("request.json",dict(selection=sel, payload_hex=request["payload_hex"], supervisor_pid=os.getpid()))
    argv=worker_command(Path.cwd(),sel)
    command=ct.create_unicode_buffer(subprocess.list2cmdline(argv))
    env="\0".join(f"{k}={v}" for k,v in sorted(clean_env().items(),key=lambda kv:kv[0].lower()))+"\0\0"
    # STARTUPINFOW, x64. No standard or inheritable file handles.
    start=ct.create_string_buffer(104)
    wt.DWORD.from_buffer(start).value=104
    info=Info()
    create=win.fn("CreateProcessW",win.BOOL,wt.LPCWSTR,wt.LPWSTR,win.PTR,win.PTR,win.BOOL,
                  wt.DWORD,win.PTR,wt.LPCWSTR,win.PTR,ct.POINTER(Info))
    envbuf=ct.create_unicode_buffer(env)
    before=win.moment()
    win.checked(create(str(BASE),command,None,None,False,8|0x400|4,
                       envbuf,str(Path.cwd()),start,ct.byref(info)))
    returned=win.moment()
    try:
        pid_for=win.fn("GetProcessId",wt.DWORD,win.H)
        instance=[pid_for(info.process),win.birth(info.process)]
        assert instance[0]==info.pid
        resume=win.fn("ResumeThread",wt.DWORD,win.H)
        resumed=win.moment()
        suspend_count=resume(info.thread)
        wait=win.fn("WaitForSingleObject",wt.DWORD,win.H,wt.DWORD)
        if wait(info.process,24000)!=0:
            raise TimeoutError("owned child wait")
        finish=win.moment()
        code=wt.DWORD()
        win.checked(win.fn("GetExitCodeProcess",win.BOOL,win.H,ct.POINTER(wt.DWORD))(info.process,ct.byref(code)))
        if code.value:
            raise RuntimeError(f"worker exit {code.value}")
        worker=read("worker.json")
        guard=worker["view"]
        try:
            identity=win.ident(guard)
            member=stream_inventory(b"".join(win.chunks(guard)))
            seal=dict(selection=sel,nonce=nonce,caller=actual_caller,child=instance,object=identity,members=member)
            key=secrets.token_bytes(32)
            Path("key.bin").write_bytes(key)
            tag=hmac.digest(key,encoded(seal).encode(),"sha256").hex()
            save("seal.json",dict(body=seal,tag=tag))
            signed=win.moment()
            # Acquire the separate scorer handle while the transferred original view remains open.
            denied=win.denied("original.bin")
            score=win.file("original.bin",win.READ,3)
            try:
                observed=win.ident(score)
                scored=b"".join(win.chunks(score))
                second=read("seal.json")
                authenticated=hmac.compare_digest(second["tag"],hmac.digest(key,encoded(second["body"]).encode(),"sha256").hex())
                held_after=win.ident(guard)
                scored_at=win.moment()
            finally:
                win.checked(win.close(score))
        finally:
            win.checked(win.close(guard))
        save("supervisor.json",dict(token=token,script=sha(__file__),caller=actual_caller,selection=sel,
             argv=argv,command=subprocess.list2cmdline(argv),application=str(BASE),inherited=False,caller_thread=win.fn("GetCurrentThreadId",wt.DWORD)(),
             before=before,returned=returned,resumed=resumed,suspend_count=suspend_count,
             finish=finish,code=code.value,child=instance,tid=info.tid,returned_process_handle=int(info.process),
             signed_at=signed,acquired_at=scored_at,seal=second,authenticated=authenticated,
             object_at_seal=identity,scored_object=observed,held_after=held_after,
             denied_after=denied,score=scored.hex(),nonce=nonce))
    finally:
        win.close(info.thread)
        win.close(info.process)


if __name__=="__main__":
    run()

