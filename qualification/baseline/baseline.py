"""CPU entry point. Runtime/test content requires an exact coordinator release."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from corpus import ROOT,DEV,fixtures,expected_for,reference_for,load_json,sha
from native import parse_native,extract_prediction,ParseError
from score import score_document,summarize
from typed_values import compare
from release import protocol,read_release,HERE,released_schedule

def prediction(raw,rules):
    try:return extract_prediction(parse_native(raw),rules)
    except (ParseError,ValueError,TypeError) as e:return {'fields':[],'tables':[],'anchors':[],'unmapped':[{'kind':'parse_failure','detail':str(e)}],'pages':[],'parse_errors':[str(e)]}
def dump(path,obj):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(obj,f,indent=2,ensure_ascii=False);f.write('\n')

def dev_check(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False);rules=load_json(HERE/'mapping.json');inventory=[];scores=[];type_coverage={}
    rawroot=ROOT/'qualification/q0/harness/evidence/004-gpu-trial/9e73ef86/run-20261115T202627Z-eb5bf7da/evidence'
    for f in fixtures():
        if f['family_id'] not in DEV:continue
        expected=expected_for(f);reference=reference_for(f)
        typed_items=[(x['field_id'],x) for x in expected['expected_fields']]+[(k,x) for t in expected['expected_tables'] for r in t['rows'] for k,x in r['cells'].items()]
        for slot,item in typed_items:
            record=type_coverage.setdefault(item.get('value_type','missing'),{'expected_items':0,'printed_form_parses_and_matches':0,'mutation_rejected':0})
            record['expected_items']+=1
            record['printed_form_parses_and_matches']+=int(compare(item['printed_text'],item,True,slot)['credited_exact'])
            record['mutation_rejected']+=int(not compare(item['printed_text']+'?',item,True,slot)['credited_exact'])
        inventory.append({'fixture_id':f['fixture_id'],'expected_sha256':f['expected_ground_truth_sha256'],'reference_tokens':len('\n'.join(reference['pages']).split()),'reference_coverage':reference['coverage'],
                          'fields':len(expected['expected_fields']),'cells':sum(len(r['cells']) for t in expected['expected_tables'] for r in t['rows'])})
        if f['family_id'] in ('F01','F07') and f['variant_kind']=='v0_clean':
            rawpath=rawroot/(f['family_id']+'.warm1.raw.txt');raw=rawpath.read_bytes();pred=prediction(raw.decode('utf-8'),rules)
            score=score_document(pred,expected,reference)
            score['source']={'kind':'retrospective Q0 dev output, not a new baseline call','path':str(rawpath.relative_to(ROOT)).replace('\\','/'),'sha256':sha(raw)}
            dump(out/(f['family_id']+'.prediction.json'),pred);dump(out/(f['family_id']+'.score.json'),score);dump(out/(f['family_id']+'.reference.json'),reference);scores.append(score)
    result={'schema':'eld-baseline-cpu-dev/1','dev_inventory':inventory,'q0_retrospective_summary':summarize(scores),'holdout_content_reads':0,'no_model_execution':True,
      'limit':'Two historical clean dev outputs test the parser/scorer. This is not the 26-document vanilla accuracy baseline.'}
    dump(out/'typed-dev-coverage.json',{'scope':'dev reference grammar audit, not model predictions','by_type':type_coverage,'mutation':'append ? to each printed form; no expected value enters conversion'})
    dump(out/'summary.json',result);print(json.dumps({'dev_documents':len(inventory),'q0_outputs_scored':len(scores),'holdout_content_reads':0}))

def score_run(run,output,authority,path,split,owner):
    release=read_release(authority,path,split,owner);result=load_json(Path(run)/'run-result.json');rules=load_json(HERE/'mapping.json')
    if result['release']!=release:raise PermissionError('Run/release mismatch')
    records={x['fixture_id']:x for x in result['calls'] if not x['excluded']};scores=[]
    selected={c['fixture_id'] for c in released_schedule(protocol(),release,split,owner) if not c['excluded']}
    for f in protocol()['fixtures']:
        if f['fixture_id'] not in selected:continue
        rec=records.get(f['fixture_id'],{'status':'missing_run_record','observation':None});raw=b''
        if rec['observation']:
            obs_path=(Path(run)/rec['observation']).resolve();obs_path.relative_to(Path(run).resolve());obs=load_json(obs_path)
            if 'raw_output' in obs:
                rawpath=obs_path.parent/obs['raw_output']['name'];raw=rawpath.read_bytes()
                if sha(raw)!=obs['raw_output']['sha256_written']:raise ValueError('Retained raw hash mismatch')
        pred=prediction(raw.decode('utf-8'),rules);score=score_document(pred,expected_for(f,split=='eval_holdout'),reference_for(f,split=='eval_holdout'),rec['status']);score['raw_sha256']=sha(raw);scores.append(score)
    packet={'scores':scores,'summary':summarize(scores),'run_result_sha256':sha((Path(run)/'run-result.json').read_bytes())}
    if 'supplemental_recovery' in release:
        packet['scope']='supplemental_single_failed_dev; does not replace original primary scores'
        packet['supplemental_recovery']=release['supplemental_recovery']
    dump(output,packet)

def main():
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='command',required=True)
    dev=sub.add_parser('dev-check');dev.add_argument('--output',required=True)
    sub.add_parser('plan')
    for name in ('execute','worker','score-run'):
        p=sub.add_parser(name)
        for opt in ('authority','release-path','split','owner'):p.add_argument('--'+opt,required=True)
        if name=='worker':p.add_argument('--run-dir',required=True);p.add_argument('--job',required=True)
        if name=='score-run':p.add_argument('--run-dir',required=True);p.add_argument('--output',required=True)
    args=parser.parse_args()
    if args.command=='dev-check':dev_check(args.output);return 0
    if args.command=='plan':print(json.dumps(protocol(),indent=2));return 0
    if args.command=='score-run':score_run(args.run_dir,args.output,args.authority,args.release_path,args.split,args.owner);return 0
    from runtime import execute,worker
    if args.command=='execute':return execute(args.authority,args.release_path,args.split,args.owner)
    return worker(args.authority,args.release_path,args.split,args.owner,args.run_dir,args.job)
if __name__=='__main__':raise SystemExit(main())
