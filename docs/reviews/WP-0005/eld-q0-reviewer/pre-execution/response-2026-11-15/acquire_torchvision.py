"""eld-q0-reviewer bounded, non-executing torchvision wheel provenance acquisition.

Released by docs/kickoffs/WP-0005-resume-2026-11-15.md (reviewer section). Stdlib only.
Downloads ONLY the exact URL below into a NEW, empty, ignored scratch directory; reads only
the wheel's own dist-info/METADATA member from the ZIP (no extraction, install, import or
execution). Result label: local-sha256-TOFU; publisher wheel digest unavailable.
Usage: python -I -B acquire_torchvision.py <new-empty-scratch-dir> <receipt-json> <cuda-metadata.json>
"""
import datetime, email, hashlib, json, pathlib, sys, urllib.parse, urllib.request, zipfile

URL = 'https://download-r2.pytorch.org/whl/cu130/torchvision-0.28.0%2Bcu130-cp312-cp312-win_amd64.whl'
FILENAME = 'torchvision-0.28.0+cu130-cp312-cp312-win_amd64.whl'
SIZE = 9_091_113
LIMIT = 10 * 2**20
METADATA_SHA256 = 'f8e91ee987603053e2166e2e4063ddcfb533f266c88bae82b7f79119aadceb59'
METADATA_MEMBER = 'torchvision-0.28.0+cu130.dist-info/METADATA'
OFFICIAL_HOSTS = {'download-r2.pytorch.org', 'download.pytorch.org'}
now = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()

def official(url):
    u = urllib.parse.urlparse(url)
    return u.scheme == 'https' and u.hostname in OFFICIAL_HOSTS and urllib.parse.unquote(u.path).endswith('/' + FILENAME)

class GuardedRedirect(urllib.request.HTTPRedirectHandler):
    hops = []
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.hops.append({'code': code, 'location': newurl})
        if not official(newurl): raise ValueError(f'Redirect outside official PyTorch hosts/filename rejected: {newurl}')
        return super().redirect_request(req, fp, code, msg, headers, newurl)

def main():
    target_dir = pathlib.Path(sys.argv[1]).resolve(); receipt_path = pathlib.Path(sys.argv[2]).resolve()
    recorded = {r['name']: r for r in json.loads(pathlib.Path(sys.argv[3]).read_text(encoding='utf-8'))}['torchvision']
    assert official(URL) and recorded['url'] == URL and recorded['size'] == SIZE and recorded['sha256'] is None
    assert not target_dir.exists(), f'Scratch directory must be new: {target_dir}'
    target_dir.mkdir(parents=True)
    part = target_dir / (FILENAME + '.part'); final = target_dir / FILENAME
    rec = {'label': 'local-sha256-TOFU; publisher wheel digest unavailable', 'released_by': 'docs/kickoffs/WP-0005-resume-2026-11-15.md',
           'requested_url': URL, 'expected_size': SIZE, 'size_limit': LIMIT, 'started_utc': now(), 'checks': {}, 'pass': False}
    try:
        opener = urllib.request.build_opener(GuardedRedirect)
        req = urllib.request.Request(URL, headers={'User-Agent': 'eLedgerCare-WP0005-reviewer-provenance', 'Accept-Encoding': 'identity'})
        h = hashlib.sha256(); n = 0
        with opener.open(req, timeout=60) as r:
            rec.update(final_url=r.url, http_status=r.status, response_headers=dict(r.headers), redirects=GuardedRedirect.hops)
            assert official(r.url), 'Final origin not an official PyTorch host/filename'
            assert r.headers.get('Content-Encoding') in (None, 'identity'), 'Unexpected content encoding'
            assert int(r.headers['Content-Length']) == SIZE, 'Content-Length differs from recorded size'
            with open(part, 'xb') as f:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk: break
                    n += len(chunk)
                    if n > LIMIT: raise ValueError('Download exceeded 10 MiB bound')
                    h.update(chunk); f.write(chunk)
        rec['completed_utc'] = now()
        rec['checks']['exact_size'] = n == SIZE == part.stat().st_size
        rec['actual_size'] = n; rec['local_sha256'] = h.hexdigest()
        assert rec['checks']['exact_size'], f'Size {n} != {SIZE}'
        part.rename(final)
        rec['local_path'] = str(final)
        with zipfile.ZipFile(final) as z:
            names = z.namelist()
            meta = [m for m in names if m.endswith('.dist-info/METADATA')]
            rec['zip_member_count'] = len(names); rec['zip_dist_info_metadata_members'] = meta
            rec['checks']['single_expected_metadata_member'] = meta == [METADATA_MEMBER]
            assert rec['checks']['single_expected_metadata_member'], meta
            info = z.getinfo(METADATA_MEMBER)
            rec['metadata_member'] = {'name': METADATA_MEMBER, 'compress_type': info.compress_type, 'file_size': info.file_size, 'CRC': info.CRC}
            body = z.read(METADATA_MEMBER)  # in-memory read of one member; nothing written or extracted
        msg = email.message_from_bytes(body)
        rec['metadata_sha256'] = hashlib.sha256(body).hexdigest()
        rec['metadata_fields'] = {'Name': msg['Name'], 'Version': msg['Version'], 'Requires-Python': msg['Requires-Python'], 'Requires-Dist': msg.get_all('Requires-Dist')}
        rec['checks']['metadata_sha256_equals_pep658_published'] = rec['metadata_sha256'] == METADATA_SHA256
        rec['checks']['metadata_bytes_equal_recorded_pep658_body'] = body == recorded['metadata_text'].encode('utf-8')
        rec['checks']['name_version'] = msg['Name'] == 'torchvision' and msg['Version'] == '0.28.0+cu130'
        rec['checks']['torch_requirement'] = 'torch (==2.13.0)' in (msg.get_all('Requires-Dist') or [])
        rec['etag_matches_recorded_head'] = rec['response_headers'].get('ETag') == recorded['head_receipt']['headers'].get('ETag')
        rec['last_modified_matches_recorded_head'] = rec['response_headers'].get('Last-Modified') == recorded['head_receipt']['headers'].get('Last-Modified')
        rec['pass'] = all(rec['checks'].values())
    except Exception as exc:
        rec['error'] = f'{type(exc).__name__}: {exc}'; rec['failed_utc'] = now()
    rec['limits'] = ['Publisher wheel SHA-256 unavailable from both official indexes; local hash is trust-on-first-use over TLS from official origin',
                     'PEP 658 METADATA match authenticates only the metadata member, not the remaining wheel body',
                     'Multipart ETag is not a content digest', 'No extraction, installation, import or execution performed']
    receipt_path.write_text(json.dumps(rec, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: rec.get(k) for k in ['pass', 'final_url', 'actual_size', 'local_sha256', 'metadata_sha256', 'checks', 'error']}, indent=2))
    sys.exit(0 if rec['pass'] else 1)

if __name__ == '__main__': main()
