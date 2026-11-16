import sys,json,runpy
from pathlib import Path
seen=[]
def audit(event,args):
 if event=='open' and isinstance(args[0],(str,bytes)):
  p=str(args[0]).replace('\\','/')
  if '/evaluation/synthetic/' in p:seen.append(p)
sys.addaudithook(audit)
sys.path.insert(0,'C:\\Users\\jackg\\Asp.net Projects\\eledgercare-worktrees\\eld-baseline-astra\\qualification\\baseline')
import baseline
baseline.dev_check('C:\\Users\\jackg\\Asp.net Projects\\eledgercare-worktrees\\eld-baseline-astra\\docs\\evidence\\WP-0007\\eld-rd-astra\\a998b765\\audit-dev')
print(json.dumps({'opened_synthetic_paths':sorted(set(seen))}))
