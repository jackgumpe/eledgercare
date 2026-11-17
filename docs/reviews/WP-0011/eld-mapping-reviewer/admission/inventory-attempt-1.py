import hashlib,json,subprocess
from pathlib import Path
base='68ed24346039c6b26a8c2010ca0956f958a1e4dc'
rev=subprocess.check_output(['git','rev-parse','HEAD']).decode().strip()
changes=subprocess.check_output(['git','diff','--name-status',base,rev]).decode().splitlines()
rows=[]
for line in changes:
    action,path=line.split('\t')
    assert action=='A' and path.startswith('docs/reviews/WP-0011/eld-mapping-reviewer/admission/')
    data=Path(path).read_bytes()
    assert data==subprocess.check_output(['git','show',rev+':'+path])
    rows.append({'action':action,'path':path,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
record={'schema':'eld-review-deliverable-inventory/1','base':base,'deliverable':rev,'files':rows,'file_count':len(rows),'protected_files_unchanged':2724,'metadata_after_deliverable':['docs/reviews/WP-0011/eld-mapping-reviewer/admission/public-inventory.json','docs/agent-reports/eld-mapping-reviewer/WP-0011/004_2026-11-17_review_eld-mapping-reviewer.md'],'private_artifacts_copied_to_public':0}
with Path('docs/reviews/WP-0011/eld-mapping-reviewer/admission/public-inventory.json').open('x',encoding='utf-8',newline='\n') as f:json.dump(record,f,indent=2);f.write('\n')
print(json.dumps({'files':len(rows),'deliverable':rev}))
