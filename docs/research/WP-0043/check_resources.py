"""Harmless venv launcher test; both launcher and actual interpreter must be in our exact Job."""
import json
import subprocess
from limits import job,job_member
from native import PYTHON

def main():
    code="import os,sys; print(os.getpid(),flush=True); input()"
    with subprocess.Popen([str(PYTHON),"-B","-u","-c",code],stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,
                          creationflags=subprocess.CREATE_NO_WINDOW|4) as proc:
        try:
            with job(proc,512<<20) as handle:
                child=int(proc.stdout.readline())
                result={"launcher":proc.pid,"interpreter":child,"launcher_in_job":job_member(proc.pid,handle),
                        "interpreter_in_job":job_member(child,handle)}
                proc.communicate("\n",timeout=8)
                result["exit"]=proc.returncode
                print(json.dumps(result))
                if not all([result["launcher_in_job"],result["interpreter_in_job"],proc.returncode==0]):
                    raise RuntimeError("job containment")
        finally:
            if proc.poll() is None:
                proc.kill()

if __name__=="__main__":
    main()
