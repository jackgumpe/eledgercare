"""Only writer. No file handles inherited. Transfer our own fresh file's read-only view."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import os
from common import ordinary, win, runtime, sha, read, save, filesystem, module_inventory


def main():
    modules=module_inventory()
    if sys.argv[1]=="profile":
        import json
        print(json.dumps(modules))
        return
    token=ordinary()
    cfg=runtime()
    cfg["all_modules"]=modules
    cfg.update(script=sha(__file__), argv=list(sys.argv), orig_argv=list(sys.orig_argv),
               cwd=str(Path.cwd()))
    control=read("request.json")
    assert int(sys.argv[1]) == control["selection"]
    payload=bytes.fromhex(control["payload_hex"])
    assert len(payload)==4
    parent = os.getppid()
    assert parent==control["supervisor_pid"]
    started=win.moment()
    file=win.file("original.bin",win.READ|win.WRITE,1,1)
    try:
        member=win.ident(file)
        ntfs=filesystem(file)
        denied=win.denied("original.bin")
        before=win.moment()
        n=win.DWORD()
        win.checked(win.write_file(file,payload,len(payload),win.ref(n),None))
        win.checked(win.flush(file))
        transfer=win.give_read_view(file,parent)
        sent=win.moment()
    finally:
        win.checked(win.close(file))
    closed=win.moment()
    save("worker.json",dict(token=token,config=cfg,instance=[os.getpid(),win.birth(win.process())],
                            parent=parent,start=started,write=before,transfer=sent,closed=closed,
                            length=n.value,member=member,ntfs=ntfs,denied=denied,view=transfer,
                            supervisor_pid=parent))


if __name__=="__main__":
    try:
        main()
    except BaseException:
        import traceback
        Path("worker-error.txt").write_text(traceback.format_exc(), encoding="utf8")
        raise
