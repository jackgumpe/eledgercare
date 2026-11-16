import sys,subprocess,time
from pathlib import Path
sys.path.insert(0,'C:\\Users\\jackg\\Asp.net Projects\\eledgercare-worktrees\\eld-baseline-reviewer\\qualification\\baseline')
import winjob
h=winjob.create('Local\\B0-review-2a2240a49e65435e94fb5c732a1b4b94')
p=subprocess.Popen(['C:\\Users\\jackg\\eLedgerCare-Q0\\WP-0005\\venv\\Scripts\\python.exe',"-I","-B",'C:\\Users\\jackg\\Asp.net Projects\\eledgercare-worktrees\\eld-baseline-reviewer\\.scratch\\wp0007-review-003\\97249fa6-043410\\lifetime\\worker.py'],creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
Path('C:\\Users\\jackg\\Asp.net Projects\\eledgercare-worktrees\\eld-baseline-reviewer\\.scratch\\wp0007-review-003\\97249fa6-043410\\lifetime\\launcher.pid').write_text(str(p.pid))
time.sleep(30)
