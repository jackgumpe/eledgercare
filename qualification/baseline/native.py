"""Safe native markup parsing and prediction-only mapping. No corpus/expected reads."""
from __future__ import annotations
import re
import unicodedata
from html.parser import HTMLParser

MAX_BYTES = 16 << 20
MAX_BLOCKS = 10000
MAX_CELLS = 20000

def norm(value):
    return unicodedata.normalize('NFC', str(value).replace('\r\n','\n').replace('\r','\n')).strip()

class ParseError(ValueError): pass

class TableParser(HTMLParser):
    """Closed table grammar; no browser-style error recovery or ignored attributes."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows=[];self.row=None;self.cell=None;self.count=0;self.events=0
        self.stack=[];self.seen_table=False
    def event(self):
        self.events+=1
        if self.events>100000:raise ParseError('html_event_limit')
    def handle_starttag(self,tag,attrs):
        self.event();parent=self.stack[-1] if self.stack else None
        parents={'table':{None},'thead':{'table'},'tbody':{'table'},'tfoot':{'table'},
                 'tr':{'table','thead','tbody','tfoot'},'td':{'tr'},'th':{'tr'},'br':{'td','th'}}
        if tag not in parents:raise ParseError('unsupported_html_tag:'+tag)
        if parent not in parents[tag]:raise ParseError('invalid_table_nesting:'+tag)
        if tag=='table':
            if self.seen_table:raise ParseError('multiple_table_roots')
            self.seen_table=True
        allowed={'colspan','rowspan'} if tag in ('td','th') else set()
        names=[k for k,v in attrs]
        if len(names)!=len(set(names)) or any(k not in allowed or v is None for k,v in attrs):
            raise ParseError('unsupported_or_valueless_attributes:'+tag)
        spans=dict(attrs)
        if any(not re.fullmatch(r'[1-9][0-9]{0,2}',v) for v in spans.values()):raise ParseError('invalid_span')
        col=int(spans.get('colspan','1'));row=int(spans.get('rowspan','1'))
        if col>100 or row!=1:raise ParseError('unsupported_span')
        if tag=='br':self.cell['text']+='\n';return
        self.stack.append(tag)
        if tag=='tr':self.row=[]
        if tag in ('td','th'):self.cell={'text':'','colspan':col,'rowspan':row}
    def handle_startendtag(self,tag,attrs):
        if tag!='br':raise ParseError('unsupported_self_closing_tag:'+tag)
        self.handle_starttag(tag,attrs)
    def handle_endtag(self,tag):
        self.event()
        if not self.stack or self.stack[-1]!=tag:raise ParseError('unmatched_table_end:'+tag)
        self.stack.pop()
        if tag in ('td','th'):
            self.cell['text']=norm(self.cell['text']);self.row.append(self.cell);self.cell=None
            self.count+=1
            if self.count>MAX_CELLS:raise ParseError('cell_limit')
        if tag=='tr':self.rows.append(self.row);self.row=None
    def handle_data(self,data):
        self.event()
        if self.cell is not None:self.cell['text']+=data
        elif data.strip():raise ParseError('text_outside_cell')
    def handle_comment(self,data):raise ParseError('unsupported_html_comment')
    def handle_decl(self,decl):raise ParseError('unsupported_html_declaration')
    def handle_pi(self,data):raise ParseError('unsupported_html_instruction')
    def unknown_decl(self,data):raise ParseError('unsupported_html_declaration')
    def result(self):
        if self.stack or not self.seen_table:raise ParseError('unclosed_or_missing_table')
        return self.rows,[]

HEADER=re.compile(r'([A-Za-z_][A-Za-z_0-9-]*)(?:<LEVEL([1-9][0-9]?)>)?\[([0-9]{1,4}),\s*([0-9]{1,4}),\s*([0-9]{1,4}),\s*([0-9]{1,4})\]<FORK>')
def parse_native(raw):
    if len(raw.encode('utf-8'))>MAX_BYTES:raise ParseError('raw_limit')
    pages=[];errors=[];fragments=[];block_count=0
    chunks=raw.split('<PAGE>')
    if chunks[0].strip():errors.append('content_before_first_page');fragments.append(chunks[0])
    for pn,chunk in enumerate(chunks[1:],1):
        blocks=[];pieces=chunk.split('<BLOCK>')
        if pieces[0].strip():errors.append(f'page_{pn}:unblocked_content');fragments.append(pieces[0])
        for piece in pieces[1:]:
            block_count+=1
            if block_count>MAX_BLOCKS:raise ParseError('block_limit')
            match=HEADER.match(piece)
            if not match:
                errors.append(f'page_{pn}:malformed_block_header')
                blocks.append({'kind':'unparsed','bbox':None,'text':norm(piece),'rows':[]});continue
            kind=match[1]; box=list(map(int,match.group(3,4,5,6)));body=norm(piece[match.end():])
            if not (0<=box[0]<=box[2]<=1000 and 0<=box[1]<=box[3]<=1000):errors.append('invalid_coordinates')
            rows=[]
            if kind=='table':
                try:
                    parser=TableParser();parser.feed(body);parser.close();rows,errs=parser.result();errors.extend(errs)
                    text='\n'.join(' '.join(c['text'] for c in row) for row in rows)
                except (ParseError,ValueError,TypeError) as e:
                    errors.append(f'page_{pn}:table:{e}');rows=[];text=body
            else:text=body
            blocks.append({'kind':kind,'bbox':box,'text':text,'rows':rows,'native_body':body})
        pages.append({'page':pn,'blocks':blocks})
    if not pages:errors.append('no_page_markers')
    return {'schema':'eld-baseline-native/1','pages':pages,'errors':errors,'unparsed_fragments':fragments,'raw_bytes':len(raw.encode('utf-8'))}

def extract_prediction(parsed, rules):
    """Only raw-derived structures and frozen dev LABEL/HEADER rules enter here."""
    labels=rules['labels']; by_label={x['label']:x for x in labels}
    pattern=re.compile('|'.join(re.escape(s) for s in sorted(by_label,key=lambda x:(-len(x),x))))
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
                        if key in by_label and ri+1<len(b['rows']) and len(b['rows'][ri+1])==len(row):
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
