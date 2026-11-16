"""Derived extract_prediction from B0 source 522f15f1f6e399c36b9c6c107fc08f51862f1fc1.
Only treatment: guarded immediate-right-neighbor association in non-active table fields.
Parser, vocabulary, thresholds, table extraction and existing fallback are unchanged.
"""
import re
from .common import norm

def extract_prediction(parsed, rules):
    """Only raw-derived structures and frozen dev LABEL/HEADER rules enter here."""
    labels=rules['labels']; by_label={x['label']:x for x in labels}
    pattern=re.compile('|'.join(re.escape(s) for s in sorted(by_label,key=lambda x:(-len(x),x))))
    # Count B0-recognized field identities across each page, including aliases and inline labels.
    # Duplicate occurrence scope is the full native page, not expected-answer identity.
    occurrences={}
    def label_hits(text):
        return [m for m in pattern.finditer(text) if (m.start()==0 or not text[m.start()-1].isalpha()) and (m.end()==len(text) or text[m.end()] in ': \n[')]
    def label_like(text):
        return bool(text.rstrip().endswith(':') or label_hits(text))
    for page in parsed['pages']:
        counts={}
        for block in page['blocks']:
            texts=[c['text'] for row in block['rows'] for c in row] if block['rows'] else [block['text']]
            for text in texts:
                for hit in label_hits(text):
                    fid=by_label[hit[0]]['field_id'];counts[fid]=counts.get(fid,0)+1
        occurrences[page['page']]=counts
    def right_neighbor(rows,ri,ci,key,pn):
        row=rows[ri]
        if ci+1>=len(row) or occurrences[pn].get(by_label[key]['field_id'])!=1:return None
        label,value=row[ci],row[ci+1]
        if any(c.get('colspan',1)!=1 or c.get('rowspan',1)!=1 for c in row):return None
        if not norm(value['text']) or label_like(value['text']):return None
        # A second plain cell to the right or plain below-label cell makes orientation ambiguous.
        if ci+2<len(row) and norm(row[ci+2]['text']) and not label_like(row[ci+2]['text']):return None
        if ri+1<len(rows) and ci<len(rows[ri+1]):
            below=rows[ri+1][ci]
            if norm(below['text']) and not label_like(below['text']):return None
        return value['text']
    fields=[];tables=[];unmapped=[{'kind':'unparsed_fragment','text':s} for s in parsed.get('unparsed_fragments',[])];anchors=[]
    def emit(label,value,page,location):
        rule=by_label[label];fields.append({'field_id':rule['field_id'],'label':label,'page':page,'value':norm(value),'location':location})
    def inline(text,page,location):
        hits=[m for m in pattern.finditer(text) if (m.start()==0 or not text[m.start()-1].isalpha()) and (m.end()==len(text) or text[m.end()] in ': \n[')]
        for i,m in enumerate(hits):
            end=hits[i+1].start() if i+1<len(hits) else len(text)
            tail=text[m.end():end]
            if tail.startswith(':'):tail=tail[1:]
            if norm(tail):emit(m[0],tail,page,location)
        if not hits and re.match(r'^[^:\n]{1,100}:\s*\S',text):unmapped.append({'page':page,'text':text,'kind':'unknown_label','location':location})
        return hits
    for page in parsed['pages']:
        pn=page['page'];blocks=page['blocks']
        for bi,b in enumerate(blocks):
            for m in re.finditer(r'PG-ANCHOR:\s*([A-Za-z0-9_-]+)',b['text']):anchors.append({'page':pn,'value':m[1]})
            if b['kind']=='table':
                active=None
                for ri,row in enumerate(b['rows']):
                    vals=[c['text'] for c in row]
                    matched=next((t for t in rules['tables'] if vals==t['headers'] and all(c['colspan']==1 for c in row)),None)
                    if matched:
                        active={'table_id':matched['table_id'],'columns':matched['columns'],'page':pn,'rows':[],'block':bi};tables.append(active);continue
                    # Any header-like row is retained, never treated as perfect/repaired header.
                    if active is not None:
                        mappable=all(c['colspan']==1 for c in row)
                        reason='unsupported_spanning_row' if not mappable else 'short_table_row' if len(vals)<len(active['columns']) else None
                        active['rows'].append({'values':vals if mappable else [],'physical_values':vals,'cells':row,'native_row':ri,'mapping_status':reason or 'mapped'})
                        if reason:unmapped.append({'page':pn,'kind':reason,'values':vals,'cells':row,'location':[bi,ri]})
                        continue
                    for ci,c in enumerate(row):
                        text=c['text'];key=text.rstrip(':')
                        adjacent=right_neighbor(b['rows'],ri,ci,key,pn) if key in by_label else None
                        if adjacent is not None:
                            emit(key,adjacent,pn,[bi,ri,ci])
                            fields[-1]['association']='immediate_right_neighbor'
                            fields[-1]['value_location']=[bi,ri,ci+1]
                        elif key in by_label and ri+1<len(b['rows']) and len(b['rows'][ri+1])==len(row):
                            emit(key,b['rows'][ri+1][ci]['text'],pn,[bi,ri,ci])
                        else:inline(text,pn,[bi,ri,ci])
                    if active is None:unmapped.append({'page':pn,'kind':'unmapped_table_row','values':vals,'location':[bi,ri]})
            else:
                text=b['text'];key=text.rstrip(':')
                if key in by_label and b['bbox']:
                    x,y,x2,y2=b['bbox']; candidates=[]
                    for j,c in enumerate(blocks):
                        if j==bi or not c['bbox'] or c['kind'] in {'table','footer'} or c['text'].rstrip(':') in by_label:continue
                        a,v,a2,v2=c['bbox']
                        # Frozen native-coordinate thresholds: label/value horizontal or directly below.
                        if a>=x2 and abs(v-y)<=5:candidates.append((0,a-x2,j,c))
                        elif 0<=v-y2<=25 and abs(a-x)<=12:candidates.append((1,v-y2,j,c))
                    if candidates:emit(key,min(candidates,key=lambda t:t[:3])[3]['text'],pn,[bi])
                    else:emit(key,'',pn,[bi])
                else:
                    hits=inline(text,pn,[bi])
                    if not hits:unmapped.append({'page':pn,'kind':'unmapped_text','text':text,'location':[bi]})
    return {'schema':'eld-baseline-prediction/1','fields':fields,'tables':tables,'anchors':anchors,'unmapped':unmapped,
            'pages':parsed['pages'],'parse_errors':parsed['errors']}
