"""The only program in this study authorized to write a four-byte original."""
import os
from pathlib import Path
import sys
from contract import read, sha, worker_config, write
import win

def main():
    control=read('control.json')
    cfg=worker_config()
    args=list(sys.orig_argv)
    before=win.moment()
    h=win.file('payload.bin', win.READ|win.WRITE, 1, 1)
    try:
        writer_id=win.ident(h)
        blocked=win.denied('payload.bin')
        size=win.DWORD()
        win.checked(win.write_file(h,b'F07\n',4,win.ref(size),None))
        if size.value!=4:
            raise IOError('short write')
        win.checked(win.flush(h))
        exported=win.give_read_view(h,control['supervisor'])
    finally:
        win.checked(win.close(h))
    write('receipt.json',dict(pid=os.getpid(), ppid=os.getppid(), birth=win.birth(win.process()),
                              current_executable=sys.executable, original_argv=args,
                              config=cfg, script=sha(__file__), writer_id=writer_id,
                              transferred_read_view=exported, denied_at_create=blocked,
                              started=before, finished=win.moment()))
if __name__=='__main__':
    main()
