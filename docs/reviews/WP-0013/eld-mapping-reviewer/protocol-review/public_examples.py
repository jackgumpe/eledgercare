"""Independent tiny public reference/prediction examples; no extractor or policy scorer."""
import copy
import html
from qualification.mapping_v1.common import parse_native
from qualification.mapping_v2.protocol.common import catalog,catalog_sha
from qualification.mapping_v2.protocol.contract import FAMILIES

def example(case='supported',family='WP13-F01'):
    profile=next(p for p in catalog()['profiles'] if p['profile']==FAMILIES[family])
    fr=profile['fields'][0];tr=profile['tables'][0];cols=list(tr['columns']);headers=list(tr['alias_headers'])
    fid=family+'-'+case+'-v0';field_value='PUBLIC-0042';values=['PUBLIC-ROW-001']+['public-cell-'+str(i) for i in range(1,len(cols))]
    def truth(value,kind='text'):return {'printed_text':value,'normalized_value':value,'value_type':kind}
    def evidence(label,value,y):return {'label_printed':label,'value_printed':value,'label_bbox_pt':[10,y,80,y+8],'value_bbox_pt':[90,y,180,y+8]}
    ft=truth(field_value,'identifier');cells={col:truth(value,'identifier' if col==tr['row_key_column'] else 'text') for col,value in zip(cols,values)}
    label=fr['aliases'][0] if case!='unsupported' else 'Unlisted public marker'
    e={'fixture_id':fid,'family_id':family,'doc_kind':profile['doc_kind'],'split':'vocabulary_eval','variant_kind':case,'page_count':1,
       'expected_fields':[{'field_id':fr['field_id'],'page_number':1,'label_printed':label,**copy.deepcopy(ft)}],
       'expected_tables':[{'table_id':tr['table_id'],'column_ids':list(cols),'rows':[{'row_id':'REVIEW-ROW','page_number':1,'cells':copy.deepcopy(cells)}]}],
       'expected_absences':[],'page_sentinels':[],'expected_adjacent_page_pairs':[],'cross_page_links':[]}
    field={'kind':'field','page_number':1,'field_id':fr['field_id'],'truth_status':'known','truth':copy.deepcopy(ft),
           'action':'assign','reason':'supported','evidence':[evidence(label,field_value,20)]}
    if case=='conflict':field.update(action='abstain',reason='duplicate_equal');field['evidence'].append(evidence(label,field_value,40))
    if case=='unsupported':field.update(action='abstain',reason='unsupported_vocabulary')
    slots=[field]+[{'kind':'cell','page_number':1,'table_id':tr['table_id'],'row_ordinal':0,'row_id':'REVIEW-ROW','column_id':col,
                   'truth_status':'known','truth':copy.deepcopy(cells[col]),'action':'assign','reason':'supported',
                   'evidence':[evidence(head,value,100+i*12)]} for i,(col,head,value) in enumerate(zip(cols,headers,values))]
    native='<PAGE><BLOCK>text[10,20,500,40]<FORK>'+label+': '+field_value
    if case=='conflict':native+='<BLOCK>text[10,50,500,70]<FORK>'+label+': '+field_value
    native+='<BLOCK>table[10,100,900,300]<FORK><table>'+''.join('<tr>'+''.join('<td>'+html.escape(v)+'</td>' for v in row)+'</tr>' for row in [headers,values])+'</table>'
    p={'schema':'eld-mapping-v2-policy/1','fixture_id':fid,'family_id':family,'case':case,'profile':profile['profile'],
       'page_count':1,'catalog_sha256':catalog_sha(),'ideal_native':native,
       'tables':[{'table_id':tr['table_id'],'column_ids':list(cols),'row_ids':['REVIEW-ROW']}],'slots':slots}
    ref={'pages':[label+' '+field_value+' '+' '.join(headers+values)],'coverage':{'scope':'generic independent public policy probe only'}}
    pred={'schema':'eld-baseline-prediction/1','fields':[{'field_id':fr['field_id'],'page':1,'value':field_value,'location':[0]}],
          'tables':[{'table_id':tr['table_id'],'page':1,'columns':list(cols),'block':1,'rows':[{'values':values,'physical_values':list(values),'native_row':1,'mapping_status':'mapped'}]}],
          'pages':parse_native(native)['pages'],'parse_errors':[],'anchors':[],'unmapped':[]}
    return e,ref,p,pred

def unresolved_cell(e,p,index=2,status='ambiguous'):
    slot=p['slots'][index];del e['expected_tables'][0]['rows'][0]['cells'][slot['column_id']]
    slot.update(truth_status=status,truth=None,action='abstain',reason='header_collision')

def unresolved_field(e,p,status):
    e['expected_fields']=[];slot=p['slots'][0]
    slot.update(truth_status=status,truth=None,action='abstain',reason='conflicting_values')
    slot['evidence'][1]['value_printed']='PUBLIC-9999'
