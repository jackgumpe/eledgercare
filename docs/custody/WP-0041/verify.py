"""Read the named development archive at its reservation. No dynamic model imports."""
from collections import namedtuple
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import sys
import zlib

BASE = '5f73e671ccd2fc12eb0f2d85b2effae713dc867c'
RUN = 'qualification/q0/harness/evidence/004-gpu-trial/9e73ef86/run-20261115T202627Z-eb5bf7da/evidence/'
Q0 = 'qualification/q0/harness/'
COORD = 'docs/coordination/WP-0005/'
MODEL = Path('C:/Users/jackg/eLedgerCare-Q0/WP-0005/models/Unlimited_OCR_2_04809669')
LABEL = 'F07.warm1'
FIXTURE = 'SYN-MP-01-v0-clean'
INPUT_HASH = '4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a'
PIN = '0480966938291445591f69f08a13b041c073a96a'
sources = {}


def digest(data):
    return sha256(data).hexdigest()


def blob(path):
    data = subprocess.check_output(['git', 'cat-file', 'blob', f'{BASE}:{path}'])
    sources[path] = {'sha256': digest(data), 'bytes': len(data)}
    return data


def record(path):
    return json.loads(blob(path))


def verify(condition, detail):
    if not condition:
        raise ValueError(detail)


def bytelevel_stream(tokenizer, ids):
    """Invert ByteLevel's printable alphabet. Added token contents are literal UTF-8."""
    verify(tokenizer['decoder']['type'] == 'ByteLevel', 'unexpected byte decoder')
    printable = [*range(33, 127), *range(161, 173), *range(174, 256)]
    inverse = {chr(b): b for b in printable}
    remaining = [b for b in range(256) if b not in printable]
    inverse.update({chr(256 + i): b for i, b in enumerate(remaining)})
    words = {v: k for k, v in tokenizer['model']['vocab'].items()}
    added = {t['id']: t['content'].encode() for t in tokenizer['added_tokens']}
    parts = []
    for token in ids:
        parts.append(added[token] if token in added else bytes(inverse[c] for c in words[token]))
    return parts


# Only the released Q0 fixture grammar is used for selection. Regex spans refer
# to the original byte stream. The table, tr and td elements do not nest in kind.
MONEY_COLUMNS = {b'Unit Price', b'Disc Amt', b'Net Line', b'Amount', b'Net USD'}
Field = namedtuple('Field', 'page table row column header literal minor opening value closing')


def first_field(raw):
    for page_number, marker in enumerate(re.finditer(b'<PAGE>', raw), 1):
        next_page = raw.find(b'<PAGE>', marker.end())
        end = next_page if next_page != -1 else len(raw)
        for table_number, table in enumerate(re.compile(rb'<table>.*?</table>', re.S).finditer(raw, marker.end(), end), 1):
            rows = list(re.compile(rb'<tr>.*?</tr>', re.S).finditer(raw, *table.span()))
            if not rows:
                continue
            cell_pattern = re.compile(rb'(<td(?: [^<>]*)?>)([^<>]*)(</td>)')
            headers = [m[2] for m in cell_pattern.finditer(raw, *rows[0].span())]
            for row_number, row in enumerate(rows[1:], 2):
                for col, m in enumerate(cell_pattern.finditer(raw, *row.span())):
                    if col >= len(headers) or headers[col] not in MONEY_COLUMNS:
                        continue
                    if re.fullmatch(rb'-?\$?-?(?:0|[1-9][0-9]*)\.[0-9]{2}', m[2]) and m[2].count(b'-') <= 1:
                        amount = Decimal(m[2].replace(b'$', b'').decode('ascii'))
                        return Field(page_number, table_number, row_number, col+1, headers[col].decode(),
                                     m[2].decode(), int(amount * 100), m.span(1), m.span(2), m.span(3))
    return None


def pdf_object(pdf, number):
    # The two pinned fixture PDFs are deterministic PDF 1.4 with direct /Length
    # and a classic xref. Resolve exact offsets so compressed data cannot match.
    start = int(re.search(rb'startxref\s+(\d+)\s+%%EOF\s*$', pdf)[1])
    rows = pdf[start:].splitlines()
    verify(rows[0] == b'xref' and rows[1].startswith(b'0 '), 'PDF xref')
    offset = int(rows[2 + number].split()[0])
    header = (str(number) + ' 0 obj\n').encode()
    verify(pdf.startswith(header, offset), 'xref points to wrong object')
    body = pdf[offset + len(header):]
    dictionary, _, remainder = body.partition(b'\n')
    if not remainder.startswith(b'stream\n'):
        return dictionary, None
    verify(b'/FlateDecode' in dictionary, 'unexpected stream filter')
    size = int(re.search(rb'/Length (\d+)', dictionary)[1])
    return dictionary, zlib.decompress(remainder[7:7+size])


def source_geometry(fixture, observed):
    pdf = blob(fixture['path'])
    child = fixture['raster_derivation']
    images = blob(child['v1_raster300_path'])
    verify(digest(pdf) == fixture['sha256'] and digest(images) == child['v1_raster300_sha256'], 'PDF digests')
    verify(b'/Kids [8 0 R' in pdf_object(pdf, 2)[0], 'first source page')
    page, _ = pdf_object(pdf, 8)
    verify(b'/Contents 7 0 R' in page and b'/MediaBox [0 0 612.00 792.00]' in page, 'source page link')
    _, commands = pdf_object(pdf, 7)
    ix = commands.index(b' Tm (L01) Tj ET')
    row_end = commands.index(b' Tm (L02) Tj ET', ix)
    row = commands[ix:row_end]
    verify(b'40.00 504.50 532.00 25.00 re' in commands[:ix], 'printed row rectangle')
    match = re.search(rb'344.00 529.50 m 344.00 504.50 l S Q\nBT [^\n]* 371.44 519.00 Tm \(\$28.50\) Tj ET\n[^\n]*398.00 529.50 m 398.00 504.50 l S Q', row)
    verify(match and row.count(b'($28.50) Tj ET') == 2, 'column edges, printed amount, repeated literal')
    header = re.search(rb'344.00 [0-9.]+ m 344.00 [0-9.]+ l S Q\nBT [^\n]* \(Unit Price\) Tj ET', commands[:ix])
    verify(header, 'Unit Price header at the same column')
    verify(b'/Kids [5 0 R' in pdf_object(images, 2)[0], 'first raster PDF page')
    verify(b'/Im1 4 0 R' in pdf_object(images, 5)[0], 'raster page/image reference')
    dictionary, rgb = pdf_object(images, 4)
    verify(all(item in dictionary for item in [b'/Width 2550', b'/Height 3301', b'/DeviceRGB', b'/BitsPerComponent 8']), 'raster format')
    page_hash = digest(rgb)
    verify(page_hash == observed[0]['rgb_sha256'] == fixture['raster'][0]['rgb_sha256'], 'actual rendered page')
    verify(len(rgb) == 2550 * 3301 * 3 == observed[0]['rgb_bytes'], 'RGB byte count')
    edges = {}
    for name, point in {'left': (1433,1120), 'right': (1658,1120), 'top': (1470,1093), 'bottom': (1470,1198)}.items():
        x,y = point
        offset = (y*2550+x)*3
        color = list(rgb[offset:offset+3])
        verify(max(color) < 125, 'predicted grid line missing from raster')
        edges[name] = {'xy': point, 'rgb': color}
    return {'paper_points_bottom_left_xyxy': [344,504.50,398,529.50], 'page_points': [612,792],
            'printed_baseline_xy_pt': [371.44,519], 'row_label': 'L01',
            'clean_pdf_sha256': digest(pdf), 'raster_pdf_sha256': digest(images),
            'native_render_page1': observed[0], 'row_col_edge_pixels_top_left': edges}


def main():
    verify(sys.version_info[:3] == (3,12,10) and digest(Path(sys.executable).read_bytes()) == INPUT_HASH, 'unbound Python')
    protocol = record(Q0+'protocol.json')
    verify(protocol['model']['revision'] == PIN, 'model pin')
    fixture = next(f for f in protocol['fixtures'] if f['fixture_id'] == FIXTURE)
    verify(fixture['split'] == 'dev', 'fixture partition')
    obs = record(RUN+LABEL+'.observation.json')
    run = record(RUN+'outcome.json')
    context = run['context']
    code = context['code_identity']
    verify(code['harness_clean'] and not code['dirty'] and code['head'] == context['release']['harness_commit'], 'running harness')
    verify(context['protocol_sha256'] == digest(blob(Q0+'protocol.json')), 'executed protocol')
    index = {r['name']:r for r in context['evidence_index']}
    capture_labels = sorted(name.removesuffix('.observation.json') for name in index if name.endswith('.observation.json'))
    historical_names = sorted(index)
    verify(len(capture_labels) == 6 and len(set(capture_labels)) == 6, 'historical capture count')
    model_files = {row['path']: row for row in record(RUN+'model-files.json')['files']}
    local = {}
    for name in ['tokenizer.json','tokenizer_config.json','modeling_unlimitedocr.py','modeling_deepseekv2.py']:
        data = (MODEL/name).read_bytes()
        verify(model_files[name]['ok'] and digest(data) == model_files[name]['sha256'], 'local '+name)
        local[name] = digest(data)
    modules = record(RUN+'module-cache.json')['modules']
    for name in ['modeling_unlimitedocr.py','modeling_deepseekv2.py']:
        verify(any(m['file'] == name and m['identical'] and m['cache_sha256'] == local[name] for m in modules), 'import receipt '+name)
    tokenizer = json.loads((MODEL/'tokenizer.json').read_bytes())
    verify(json.loads((MODEL/'tokenizer_config.json').read_bytes())['clean_up_tokenization_spaces'] is False, 'decoder cleanup')
    checked = []
    for label in capture_labels:
        raw = blob(RUN+label+'.raw.txt')
        field = first_field(raw)
        checked.append([label, field is not None])
        if field:
            break
    verify(label == LABEL and field[:7] == (1,2,2,5,'Unit Price','$28.50',2850), 'frozen structural selection')
    id_bytes = blob(RUN+LABEL+'.token_ids.json')
    ids = json.loads(id_bytes)
    verify(not obs['raw_output']['truncated_by_writer'] and not obs['token_ids_file']['truncated_by_writer'], 'truncated evidence')
    verify(digest(id_bytes) == obs['token_ids_file']['full_sha256'], 'ID serialization')
    native = obs['native']
    verify(digest(json.dumps(ids).encode()) == native['token_ids_sha256'] and len(ids) == native['output_tokens'], 'native ordered IDs')
    parts = bytelevel_stream(tokenizer, ids)
    verify(b''.join(parts) == raw and digest(raw) == native['text_sha256'] == obs['raw_output']['full_sha256'], 'whole context decode')
    offset = 0
    pieces = []
    for index, (token, part) in enumerate(zip(ids, parts, strict=True)):
        end = offset + len(part)
        if offset < field.closing[1] and end > field.opening[0]:
            pieces.append({'index': index, 'id': token, 'piece': part.decode(), 'bytes': [offset,end]})
        offset = end
    verify([p['id'] for p in pieces] == [128821,6,1449,16,1328,128822], 'field pieces')
    verify(tuple(pieces[0]['bytes']) == field.opening and tuple(pieces[-1]['bytes']) == field.closing, 'delimiter straddle')
    verify(field.value == (pieces[1]['bytes'][0],pieces[-2]['bytes'][1]), 'value straddle')
    decisions = []
    for before, emitted in zip(pieces, pieces[1:]):
        decisions.append({'consume_index': before['index'], 'consume_id': before['id'],
                          'absolute_input_position': native['prompt_len'] + before['index'],
                          'emit_index': emitted['index'], 'emit_id': emitted['id']})
    dr = run['checks']['2_artifact_dependency_lock']['rendered_pages'][FIXTURE]
    geometry = source_geometry(fixture, dr)
    returned = record(COORD+'gpu-reviewer-release/author-exit.json')
    verify(returned['author_lease_id'] == run['context']['release']['lease_id'] and returned['prior_pids_present'] == []
           and 'RETURNED' in returned['author_lease_status'], 'historical author return')
    # Supplemental records are metadata, source or public dev receipts only.
    for path in ['evaluation/ADMISSION.md','evaluation/generation/generate_corpus.py',
                 Q0+'q0harness/session.py', Q0+'q0harness/telemetry.py', Q0+'q0harness/backend_torch.py',
                 COORD+'final-runtime-observations/README.md', COORD+'final-runtime-observations/run-comparison.json',
                 'docs/coordination/WP-0007/gpu-author-dev-release/README.md',
                 'docs/evidence/WP-0007/eld-rd-astra/runtime-dev/20261116T051059Z-eda73dc6/evidence/SYN-INV-01-v0-clean.measured.observation.json',
                 'docs/evaluation/WP-0015/dev/dense/rasters.json',
                 'docs/research/WP-0015/astra/evidence/dev-ab-01/05-dense-native/window-001.json',
                 'docs/fixtures/WP-0024/h0/source-witness.json','docs/coordination/WP-0024/h0-r1-plan.json',
                 'docs/research/WP-0024/sensor/capture.py','docs/coordination/WP-0024/decision.json',
                 'docs/coordination/WP-0029/decision.json','docs/reviews/WP-0036/evidence/summary.json',
                 'docs/custody/WP-0040/intake.json','docs/coordination/WP-0041/assignment.md']:
        blob(path)
    for filename in [LABEL+'.raw.txt', LABEL+'.token_ids.json', LABEL+'.observation.json']:
        verify(index[filename]['full_sha256'] == sources[RUN+filename]['sha256'], 'historical output receipt')
    output = {'base': BASE, 'selected_capture_id': LABEL,'observed_candidates_before_stop': checked,
              'fixture': FIXTURE, 'model': PIN, 'verified_local_files':local,
              'original_ids':len(ids),'raw_utf8_bytes':len(raw),'raw_sha256':digest(raw),
              'ordered_ids_sha256_native_json':native['token_ids_sha256'], 'field': field._asdict(),
              'context_pieces': pieces,'prediction_alignment': decisions,'prompt_len': native['prompt_len'],
              'native_branch_input_ids_prefix_including_open_sha256_json':digest(json.dumps(ids[:pieces[0]['index']+1]).encode()),
              'geometry': geometry,'historical_kernel_path': obs['kernel_path'],'historical_cache':obs['cache'],
              'historical_call_kwargs': obs['call_kwargs'],'historical_platform':run['context']['platform'],
              'historical_evidence_index_names':historical_names,'executing_code':code,
              'historical_prompt':native['prompt'],'historical_executing_harness':run['context']['harness'],'historical_release':run['context']['release'],
              'historical_lease_return_utc':returned['observed_utc'],'source_blobs':sources}
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
