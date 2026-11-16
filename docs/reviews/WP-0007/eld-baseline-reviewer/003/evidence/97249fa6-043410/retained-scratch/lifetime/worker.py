import sys,os,time
from pathlib import Path
sys.path.insert(0,'C:\\Users\\jackg\\Asp.net Projects\\eledgercare-worktrees\\eld-baseline-reviewer\\qualification\\baseline')
import winjob
winjob.join('Local\\B0-review-2a2240a49e65435e94fb5c732a1b4b94')
Path('C:\\Users\\jackg\\Asp.net Projects\\eledgercare-worktrees\\eld-baseline-reviewer\\.scratch\\wp0007-review-003\\97249fa6-043410\\lifetime\\worker.pid').write_text(str(os.getpid()))
time.sleep(30)
