"""One-time dev-only rules/protocol preparation; never calls a model or reads test content."""
import json,sys,subprocess
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from corpus import ROOT,DEV,fixtures,expected_for,verified,sha,load_json
OUT=Path(__file__).resolve().parent
labels={};tables={};used=[]
for f in fixtures():
    if f['family_id'] not in DEV:continue
    e=expected_for(f);used.append({'fixture_id':f['fixture_id'],'expected_sha256':f['expected_ground_truth_sha256']})
    for v in e['expected_fields']+e['expected_absences']:
        k=v['label_printed'];new={'label':k,'field_id':v['field_id']}
        if k in labels and labels[k]!=new:raise ValueError('Ambiguous dev label')
        labels[k]=new
for src in load_json(ROOT/'evaluation/manifests/corpus-manifest.json')['source_records']:
    if src['family_id'] not in DEV:continue
    s=json.loads(verified(src['source_path'],src['sha256']))
    for t in s.get('tables',[]):
        tables[t['table_id']]={'table_id':t['table_id'],'headers':[c['header'] for c in t['columns']],'columns':[c['col_id'] for c in t['columns']]}
tables['line_items']={'table_id':'line_items','headers':['Row','SKU / Ref','Description','Qty','Unit Price','Disc%','Disc Amt','Tax','Net Line'],
                      'columns':['row_id','sku','description','qty_unit','unit_price','discount_rate','line_discount','tax_flag','net_line']}
rules={'schema':'eld-baseline-mapping/1','labels':sorted(labels.values(),key=lambda x:x['label']),'tables':list(tables.values()),'dev_provenance':used,
       'limit':'Only dev labels/headers; no known values, fixture IDs or expected boxes are used by extraction. Unseen labels/headers remain unsupported.'}
qpath='qualification/q0/harness/protocol.json';q=load_json(ROOT/qpath)
p={'schema':'eld-baseline-protocol/1','status':'CPU candidate; independent acceptance and coordinator runtime release required',
   'q0_core_tree':subprocess.check_output(['git','rev-parse','HEAD:qualification/q0/harness/q0harness'],cwd=ROOT,text=True).strip(),
   'corpus_candidate':'29b2000265ae6068d9c86818622c81a40cadd961','corpus_manifest_sha256':sha((ROOT/'evaluation/manifests/corpus-manifest.json').read_bytes()),
   'q0_protocol_path':qpath,'q0_protocol_sha256':sha((ROOT/qpath).read_bytes()),
   'dependency_lock_path':'qualification/q0/harness/locks/dependency-lock.json','dependency_lock_sha256':sha((ROOT/'qualification/q0/harness/locks/dependency-lock.json').read_bytes()),
   'model_manifest_path':'qualification/q0/harness/manifests/model-files.json','model_manifest_sha256':sha((ROOT/'qualification/q0/harness/manifests/model-files.json').read_bytes()),
   'model':q['model'],'renderer':q['renderer'],'call':q['call'],'guards':q['guards'],'gpu':q['gpu'],
   'read_only_q0_root':q['storage']['root'],'model_relative':q['storage']['subdirs']['models'],'notice_relative':q['storage']['subdirs']['notices'],
   'runtime_roots':{'author':r'C:\Users\jackg\eLedgerCare-Baseline\WP-0007\author','reviewer':r'C:\Users\jackg\eLedgerCare-Baseline\WP-0007\reviewer'},
   'storage_cap_bytes':4<<30,'free_floor_bytes':20<<30,'measured_calls_per_document':1,
   'warmups':['SYN-WO-01-v0-clean','SYN-MP-01-v0-clean'],'warmup_policy':'one excluded dev call per 1/3-page category after each cold load',
   'sentinel_policy':{'chosen_by':'independent reviewer before result access','required_categories':['single_page','multi_page','raster_or_hybrid'],'ids_bound_in_release':True},
   'failure_policy':'preserve first failure and raw outputs; stop session, mark remaining planned documents not_run_after_failure; no automatic retries',
   'fixtures':[{k:f[k] for k in ['fixture_id','family_id','split','variant_kind','file_path','size_bytes','sha256','page_count','expected_ground_truth_path','expected_ground_truth_sha256','source_record_path','source_record_sha256']} for f in fixtures()],
   'ordering':'dev then eval_holdout; family_id then fixture_id lexical; one measured call per document',
   'split_order':['dev','eval_holdout']}
p['fixtures'].sort(key=lambda f:(p['split_order'].index(f['split']),f['family_id'],f['fixture_id']))
for name,obj in [('mapping.json',rules),('protocol.json',p)]:
    (OUT/name).write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8',newline='\n')
print('Prepared dev-only label/header rules and public-metadata 26-document protocol.')
