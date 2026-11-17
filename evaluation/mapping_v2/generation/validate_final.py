"""Frozen CPU verification of sealed PDFs, source truth, public contract and reproducibility."""
from __future__ import annotations
import argparse,collections,datetime,hashlib,io,json,subprocess,sys,traceback
from pathlib import Path
from PIL import Image
from pypdf import PdfReader
sys.path.insert(0,str(Path(__file__).resolve().parent))
import create_final as gen

ROOT=gen.ROOT
PUBLIC=Path('C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/eld-vocabulary-custodian')

def public_git(*args):return subprocess.check_output(['git','-C',str(PUBLIC),*args],stderr=subprocess.PIPE)
def target(slot):return ('cell',slot['table_id'],slot['row_ordinal'],slot['column_id']) if slot['kind']=='cell' else ('field',slot['field_id'])
def inside(a,b):return b[0]<=a[0]<=a[2]<=b[2] and b[1]<=a[1]<=a[3]<=b[3]

def verify(out,source_commit,corpus_commit,receipt,evidence):
    pins=gen.source_check(source_commit)
    gen.require(gen.git('show',source_commit+':generation/validate_final.py')==Path(__file__).read_bytes(),'validator differs from frozen helper')
    gen.require(gen.git('rev-parse','HEAD').decode().strip()==corpus_commit,'corpus candidate is not current exact HEAD')
    gen.require(not gen.git('diff','--name-only').strip() and not gen.git('diff','--cached','--name-only').strip(),'tracked source changed before verification')
    for item in pins['public_source_files']:
        data=(PUBLIC/item['path']).read_bytes()
        gen.require(data==public_git('show',pins['protocol_source']+':'+item['path']) and gen.sha(data)==item['sha256'],'accepted contract working/Git bytes changed')
    gen.require(public_git('rev-parse',pins['protocol_source']+':qualification/mapping_v2').decode().strip()==pins['protocol_tree'],'accepted protocol tree')
    sys.path.insert(0,str(PUBLIC))
    from qualification.mapping_v2.protocol.common import verify_pins
    from qualification.mapping_v2.protocol.contract import validate,validate_family,validate_catalog
    from qualification.mapping_v1.common import parse_native,norm
    verify_pins();catalog=validate_catalog()
    receipt['checks'].append('frozen generator/validator, all 12 historical foundation files and exact accepted public contract/comparator pins')
    manifest=json.loads((out/'manifest.json').read_bytes());files=manifest['files']
    gen.require(len(files)==84==manifest['file_count_excluding_manifest'],'core artifact count')
    gen.require({str(p.relative_to(out)).replace('\\','/') for p in out.rglob('*') if p.is_file()}=={f['path'] for f in files}|{'manifest.json'},'exact core output path set')
    for entry in files:
        path=out/entry['path'];data=path.read_bytes();rel=str(path.relative_to(ROOT)).replace('\\','/')
        gen.require(len(data)==entry['bytes'] and gen.sha(data)==entry['sha256'],'manifest file identity')
        gen.require(data==gen.git('show',corpus_commit+':'+rel),'core working/committed mismatch')
    gen.require((out/'manifest.json').read_bytes()==gen.git('show',corpus_commit+':corpus/r1/manifest.json'),'manifest working/committed mismatch')
    gen.require(manifest['generator_commit']==source_commit and manifest['catalog_sha256']==pins['catalog_sha256'] and manifest['protocol_sha256']==pins['protocol_sha256'],'manifest release pins')
    receipt['checks'].append('all 85 core files exact manifest, working and committed bytes')

    foundations=gen.load('foundations/r1/families.json')['families'];templates=gen.load('foundations/r1/templates.json')['templates'];plan=gen.load('finalization/plan-r1.json')
    family_map={f['family_id']:f for f in foundations};template_map={t['family_id']:t for t in templates}
    all_field_labels={norm(s).removesuffix(':') for p in catalog['profiles'] for f in p['fields'] for s in f['canonical_labels']+f['aliases']}
    all_headers={norm(s) for p in catalog['profiles'] for t in p['tables'] for s in t['canonical_headers']+t['alias_headers']}
    records=collections.defaultdict(list);summaries=[];render_ids=[];run_count=0;printed_occurrences=0
    for fixture in manifest['fixtures']:
        fid=fixture['fixture_id'];art={x['role']:out/x['path'] for x in fixture['artifacts']}
        expected,reference,policy,source,operators=[json.loads(art[k].read_bytes()) for k in ('expected','reference','policy','source','operators')]
        summaries.append(validate(expected,reference,policy));records[fixture['family_id']].append((expected,reference,policy))
        family=family_map[fixture['family_id']];template=template_map[fixture['family_id']]
        gen.require(source['foundation_family']==family and source['foundation_template']==template and source['foundation_mutated'] is False,'foundation facts/template mutation')
        gen.require(expected['page_count']==fixture['page_count']==1 and policy['fixture_id']==fid,'fixture identities')
        known={('field',f['field_id']):gen.truth(f) for f in family['fields']}
        known[('field',family['absence']['field_id'])]={'printed_text':'','expected_state':'absent_blank'}
        for ri,row in enumerate(family['table']['rows']):
            for column,value in row['cells'].items():known[('cell',family['table']['table_id'],ri,column)]=gen.truth(value)
        gen.require({target(s) for s in policy['slots']}==set(known),'complete foundation opportunity universe')
        for slot in policy['slots']:
            if slot['truth_status']=='known':gen.require(slot['truth']==known[target(slot)],'known truth differs from foundation')
            else:
                gen.require(policy['case']=='conflict' and slot['field_id']==family['reserved_conflict']['field_id'] and slot['truth'] is None,'unresolved truth outside declared conflict')
            for ev in slot['evidence']:
                gen.require(inside(ev['label_bbox_pt'],[0,0,612,792.24]) and (ev['value_bbox_pt'] is None or inside(ev['value_bbox_pt'],[0,0,612,792.24])),'source evidence box outside page')
                gen.require(any(all(ev[k]==occ[k] for k in ('label_printed','value_printed','label_bbox_pt','value_bbox_pt')) for occ in source['source_occurrences']),'policy evidence without source occurrence')
                if policy['case']=='unsupported':
                    normalized=norm(ev['label_printed']) if slot['kind']=='cell' else norm(ev['label_printed']).removesuffix(':')
                    gen.require(normalized not in (all_headers if slot['kind']=='cell' else all_field_labels),'unsupported wording appears in accepted catalog')
        expected_occurrences=sum(len(s['evidence']) for s in policy['slots'])
        gen.require(expected_occurrences==len(source['source_occurrences']),'printed occurrence omitted or duplicated in policy')
        printed_occurrences+=expected_occurrences
        slots={target(s):s for s in policy['slots']}
        if policy['case']=='conflict':
            cfg=plan['conflicts'][family['family_id']];slot=slots[('field',family['reserved_conflict']['field_id'])]
            gen.require(slot['reason']==cfg['mode'] and slot['truth_status']==cfg['truth_status'] and len(slot['evidence'])==2,'conflict plan differs')
            values=[e['value_printed'] for e in slot['evidence']]
            original=known[('field',family['reserved_conflict']['field_id'])]['printed_text']
            extra=original if cfg['value_source']=='original' else family['reserved_conflict']['alternate_value']['printed_text']
            gen.require(values==[original,extra] and slot['evidence'][0]['label_printed']!=slot['evidence'][1]['label_printed'],'duplicate original/alternate lineage')
        gen.require(all(s['action']==('abstain' if policy['case']=='unsupported' else 'assign') for s in policy['slots'] if policy['case']!='conflict' or target(s)!=('field',family['reserved_conflict']['field_id'])),'unaffected policy changed')

        pdf=art['pdf'].read_bytes();reader=PdfReader(io.BytesIO(pdf),strict=True)
        gen.require(len(reader.pages)==1,'PDF actual page count')
        page=reader.pages[0];gen.require([float(page.mediabox.width),float(page.mediabox.height)]==[612.0,792.24],'PDF page box')
        gen.require(not reader.is_encrypted and '/Annots' not in page and '/AcroForm' not in reader.trailer['/Root'],'unexpected PDF active/annotation content')
        extracted=[]
        def visitor(text,cm,tm,font,size):
            if text.strip():extracted.append(text.strip())
        page.extract_text(visitor_text=visitor)
        gen.require(collections.Counter(extracted)==collections.Counter(r['text'] for r in operators['runs']),'actual PDF text occurrence coverage')
        runs=operators['runs'];ordered=sorted(runs,key=lambda r:(-r['baseline'][1],r['baseline'][0],r['ordinal']))
        gen.require(reference['runs']==[ordered] and reference['pages']==['\n'.join(r['text'] for r in ordered)],'complete reference/reading order')
        gen.require(runs==source['furniture_and_text_runs'] and len({r['anchor'] for r in runs})==len(runs),'source anchors and operators')
        gen.require(all(inside(r['bbox_pt'],[12,12,600,782.24]) for r in runs),'printed run outside safe page region')
        run_count+=len(runs)
        parsed=parse_native(policy['ideal_native']);gen.require(not parsed['errors'] and len(parsed['pages'])==1,'ideal native parse')
        blocks=parsed['pages'][0]['blocks'];gen.require(len(blocks)==len(source['native_blocks']),'native block count')
        observed=[];data_tables=[];pair_tables=[]
        for native,original in zip(blocks,source['native_blocks']):
            gen.require(native['bbox']==gen.native_box(original['bbox_pt']) and native['kind']==original['kind'] and native['native_body']==original['body'],'ideal native operator layout fidelity')
            if native['kind']=='table':
                for row in native['rows']:
                    gen.require(all(c['rowspan']==c['colspan']==1 for c in row),'unexpected witness cell span')
                    observed.extend(c['text'] for c in row if c['text'])
                (pair_tables if len(native['rows'])==1 else data_tables).append(native)
            else:observed.append(native['text'])
        gen.require(collections.Counter(observed)==collections.Counter(r['text'] for r in runs),'ideal witness text occurrence coverage')
        gen.require(len(data_tables)==1 and len(pair_tables)==len(family['fields'])+1+(policy['case']=='conflict'),'explicit native field/data structure')
        gen.require(all(len(t['rows'][0])==2 for t in pair_tables),'field/absence immediate adjacency structure')
        gen.require(sum(t['rows'][0][1]['text']=='' for t in pair_tables)==1,'one explicit blank cell')
        rows=data_tables[0]['rows'];rule=next(p for p in catalog['profiles'] if p['profile']==family['profile'])['tables'][0]
        heads=[c['text'] for c in rows[0]]
        gen.require(heads==(plan['unsupported_headers'][rule['table_id']] if policy['case']=='unsupported' else rule['alias_headers']),'exact printed header membership/order')
        gen.require(all(len(r)==len(rule['columns']) for r in rows),'table widths')
        rowkey=rule['columns'].index(rule['row_key_column']);keys=[r[rowkey]['text'] for r in rows[1:]]
        gen.require(all(keys) and len(set(keys))==len(keys),'grounded unique row keys')
        png,pixel_sha=gen.render(pdf);gen.require(png==art['render'].read_bytes() and pixel_sha==fixture['render_pixels_sha256'],'actual PDF render identity')
        image=Image.open(io.BytesIO(png));gen.require(image.size==(2550,3301) and image.getextrema()!=((255,255),(255,255),(255,255)),'empty or wrong render')
        render_ids.append({'fixture_id':fid,'png_sha256':gen.sha(png),'pixel_sha256':pixel_sha,'bytes':len(png)})
    receipt['checks'].extend(['all 12 exact accepted public expected/reference/policy validations','all foundation truth, unit and absence identities; complete policy occurrence/ambiguity lineage',
      'all supported and outside-dictionary label/header memberships, duplicate guards and known row keys',
      'all 12 actual PDF pages, every text occurrence and complete canonical reading order',
      'all 12 ideal-native witnesses preserve printed text multiplicities, explicit field cells, blank cells, table structure and source coordinates',
      'all 12 PDFs render byte-identically to frozen canonical PNGs with exact dimensions/pixel hashes'])
    for rows in records.values():validate_family(rows)
    gen.require(len(records)==4 and len(summaries)==12,'bounded family/case count')
    receipt['checks'].append('four complete accepted-contract family-pair validations with invariant opportunity universes and known truth')
    replay=ROOT/'scratch'/('reproduce-'+evidence.name);reproduced=gen.generate(replay,source_commit)
    original_files=sorted(p.relative_to(out) for p in out.rglob('*') if p.is_file());new_files=sorted(p.relative_to(replay) for p in replay.rglob('*') if p.is_file())
    gen.require(original_files==new_files and all((out/p).read_bytes()==(replay/p).read_bytes() for p in original_files),'deterministic regeneration mismatch')
    receipt['checks'].append('all 85 regenerated core files byte-identical in new ignored scratch')
    for family_id in records:
        sheet=Image.new('RGB',(1836,792),'white')
        for i,case in enumerate(plan['cases']):
            image=Image.open(out/'renders'/(family_id+'-'+case+'-v0.png'));sheet.paste(image.resize((612,792),Image.Resampling.LANCZOS),(i*612,0))
        target_path=evidence/(family_id+'-contact.png');sheet.save(target_path,format='PNG',compress_level=9)
    receipt.update({'source_commit':source_commit,'corpus_candidate':corpus_commit,'protocol_source':pins['protocol_source'],'protocol_review':pins['independent_protocol_review'],
      'catalog_sha256':pins['catalog_sha256'],'protocol_sha256':pins['protocol_sha256'],'fixture_checks':summaries,'renders':render_ids,'families':4,'documents':12,'pages':12,
      'core_files':85,'regenerated_equal_files':85,'complete_text_runs':run_count,'policy_source_occurrences':printed_occurrences,
      'known_slots':sum(s['known'] for s in summaries),'ambiguous_slots':sum(s['ambiguous'] for s in summaries),'unknown_slots':sum(s['unknown'] for s in summaries),
      'required_abstentions':sum(s['required_abstentions'] for s in summaries),'visual_inspection':'contact sheets and original renders prepared; actual author inspection recorded separately',
      'coverage_limits':plan['coverage_limits']})

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source-commit',required=True);parser.add_argument('--corpus-commit',required=True);parser.add_argument('--run-id',required=True);a=parser.parse_args()
    gen.require(a.run_id.replace('-','').isalnum(),'invalid attempt ID');evidence=ROOT/'evidence'/a.run_id;gen.require(not evidence.exists(),'existing attempt must be retained');evidence.mkdir(parents=True)
    receipt={'schema':'eld-wp13-final-verification/1','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':[sys.executable,*sys.argv],
      'checks':[],'status':'running','model_inference':False,'prediction_mapper_execution':False,'reference_contract_execution':True}
    try:verify(ROOT/'corpus/r1',a.source_commit,a.corpus_commit,receipt,evidence);receipt['status']='passed'
    except Exception:receipt.update(status='failed',failure=traceback.format_exc())
    finally:
        receipt['ended_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();gen.write(evidence/'receipt.json',receipt)
        print(json.dumps({'status':receipt['status'],'checks':len(receipt['checks']),'receipt':str(evidence/'receipt.json')}))
    return 0 if receipt['status']=='passed' else 1

if __name__=='__main__':raise SystemExit(main())
