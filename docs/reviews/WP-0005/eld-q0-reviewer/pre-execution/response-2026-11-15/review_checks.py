"""eld-q0-reviewer independent offline checks of Astra WP-0005 /007 frozen response.

Reviewer-authored. Reads committed repository files only (plus read-only host/storage
observation). No network, no imports of torch/transformers/model code, no installs.
Graph closure is recomputed from the raw requires_dist in pypi-metadata.json and
cuda-metadata.json, NOT from the author's lock edges, and then compared to the lock.
pip's vendored `packaging` is used only as the PEP 508/440/425 evaluator.
Usage: python -I -B review_checks.py <repo-root> <output-json>
"""
import ast, datetime, email, hashlib, json, os, pathlib, platform, shutil, subprocess, sys, urllib.parse
from pip._vendor.packaging.requirements import Requirement
from pip._vendor.packaging.tags import sys_tags
from pip._vendor.packaging.utils import canonicalize_name, parse_wheel_filename
from pip._vendor.packaging.version import Version

repo = pathlib.Path(sys.argv[1]).resolve(); out_path = pathlib.Path(sys.argv[2]).resolve()
R = repo / 'qualification/q0/preflight/response'; P = repo / 'qualification/q0/preflight'
load = lambda p: json.loads(p.read_text(encoding='utf-8'))
sha = lambda b: hashlib.sha256(b).hexdigest()
blob = lambda b: hashlib.sha1(b'blob %d\0' % len(b) + b).hexdigest()
results, failures = {}, []
def check(name, ok, detail=None):
    results[name] = {'pass': bool(ok), 'detail': detail}
    if not ok: failures.append(name)
def ts(s): return datetime.datetime.fromisoformat(s.replace('Z', '+00:00'))

started = datetime.datetime.now(datetime.timezone.utc).isoformat()
# ---- Q0R-01: producer/receipt provenance -------------------------------------------
rc = load(R / 'collection-receipt.json')
helper = (R / 'collect-response.py').read_bytes()
check('Q0R01.helper_hash_matches_receipt', sha(helper) == rc['helper_sha256'] and blob(helper) == rc['helper_git_blob'],
      {'sha256': sha(helper), 'git_blob': blob(helper)})
frozen = subprocess.run(['git', '-C', str(repo), 'show', rc['frozen_helper_commit'] + ':qualification/q0/preflight/response/collect-response.py'], capture_output=True).stdout
check('Q0R01.helper_identical_in_frozen_commit', frozen == helper, rc['frozen_helper_commit'])
anc = subprocess.run(['git', '-C', str(repo), 'merge-base', '--is-ancestor', rc['frozen_helper_commit'], 'd666c4163b8b6bdf5f6c69b455c30f3c377cbdc5']).returncode
check('Q0R01.frozen_commit_is_candidate_ancestor', anc == 0)
t0, t1 = ts(rc['started_utc']), ts(rc['completed_utc'])
outs = {o['path']: o for o in rc['outputs']}
bad = [p for p, o in outs.items() if (lambda d: (len(d), sha(d), blob(d)) != (o['size'], o['sha256'], o['git_blob']))((R / p).read_bytes())]
check('Q0R01.all_receipt_outputs_match_bytes', not bad, {'outputs': len(outs), 'mismatch': bad})
present = sorted(str(p.relative_to(R)).replace('\\', '/') for p in R.rglob('*') if p.is_file())
check('Q0R01.unreceipted_files_are_only_docs_scripts_evidence', set(present) - set(outs) == {'README.md', 'collect-response.py', 'verify-response.py', 'collection-receipt.json', 'verification.json'},
      sorted(set(present) - set(outs)))
stamps = []
for rec in load(R / 'pypi-metadata.json'): stamps.append(('pypi:' + rec['name'], rec['receipt']['retrieved_utc']))
for rec in load(R / 'cuda-metadata.json'):
    for k in ('index_receipt', 'metadata_receipt', 'head_receipt'): stamps.append((f"cuda:{rec['name']}:{k}", rec[k]['retrieved_utc']))
for rec in load(R / 'source-closure.json'): stamps.append(('src:' + rec['path'], rec['receipt']['retrieved_utc']))
for rec in load(R / 'torchvision-alternate-indexes.json'): stamps.append(('alt:' + rec['receipt']['url'], rec['receipt']['retrieved_utc']))
outside = [(n, s) for n, s in stamps if not (s.endswith('+00:00') and t0 <= ts(s) <= t1)]
check('Q0R01.all_retrieval_stamps_utc_inside_collection_interval', not outside, {'stamps': len(stamps), 'interval': [rc['started_utc'], rc['completed_utc']], 'outside': outside})

# ---- Q0R-03: source identity vs retained pinned model tree (independent of 'expected_git_blob') -----
tree = {e['path']: e for e in load(repo / 'research/astra/sources/hf-tree.json')}
src = load(R / 'source-closure.json'); model_rows = []
for rec in src:
    data = (R / rec['local_path']).read_bytes()
    row = {'path': rec['path'], 'size': len(data), 'git_blob': blob(data), 'sha256': sha(data)}
    if rec['revision'] == '0480966938291445591f69f08a13b041c073a96a':
        row['tree_match'] = tree[rec['path']]['oid'] == blob(data) and tree[rec['path']]['size'] == len(data)
        model_rows.append(row)
    row['url_pinned'] = rec['revision'] in rec['receipt']['url'] and rec['receipt']['final_url'].startswith('https://')
check('Q0R03.six_model_texts_match_pinned_tree', len(model_rows) == 6 and all(r['tree_match'] for r in model_rows), model_rows)
imports = {}
for name in ['configuration_deepseek_v2.py', 'conversation.py', 'packing_patch.py']:
    mods = set()
    for n in ast.walk(ast.parse((R / 'sources' / name).read_text(encoding='utf-8'))):
        if isinstance(n, ast.Import): mods |= {a.name.split('.')[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.level == 0 and n.module: mods.add(n.module.split('.')[0])
    imports[name] = sorted(mods)
third = {k: [m for m in v if m not in sys.stdlib_module_names] for k, v in imports.items()}
check('Q0R03.new_model_sources_need_only_torch_transformers', all(set(v) <= {'torch', 'transformers'} for v in third.values()), {'all_absolute_imports': imports, 'non_stdlib': third})
tc = load(R / 'sources/tokenizer_config.json'); stm = load(R / 'sources/special_tokens_map.json')
check('Q0R03.tokenizer_builtin_fast_class_no_remote_code',
      tc.get('tokenizer_class') == 'LlamaTokenizerFast' and 'auto_map' not in tc and tc.get('add_prefix_space') is None and not tc.get('from_slow', False) and 'auto_map' not in stm,
      {k: tc.get(k) for k in ['tokenizer_class', 'add_prefix_space', 'legacy', 'from_slow', 'use_fast', 'model_max_length', 'clean_up_tokenization_spaces']} | {'auto_map_present': 'auto_map' in tc, 'top_level_keys': sorted(k for k in tc if k != 'added_tokens_decoder')})

# ---- Q0R-02 / closure: recompute graph from raw metadata ------------------------------
lock = load(R / 'metadata-lock.json'); pypi = load(R / 'pypi-metadata.json'); cuda = load(R / 'cuda-metadata.json')
env = {'implementation_name': sys.implementation.name, 'implementation_version': platform.python_version(), 'os_name': os.name,
       'platform_machine': platform.machine(), 'platform_release': platform.release(), 'platform_system': platform.system(),
       'platform_version': platform.version(), 'python_full_version': platform.python_version(), 'platform_python_implementation': platform.python_implementation(),
       'python_version': '.'.join(platform.python_version_tuple()[:2]), 'sys_platform': sys.platform, 'extra': ''}
diff = {k: (env[k], lock['environment'].get(k)) for k in env if env[k] != lock['environment'].get(k)}
check('Q0R02.lock_environment_equals_independent_host_env', not diff, diff)
records = [(r['name'], r['version'], r['requires_dist']) for r in pypi] + [(r['name'], r['version'], r['requires_dist']) for r in cuda]
vers = {canonicalize_name(n): v for n, v, _ in records}
active, inactive, unsat, xet = [], 0, [], []
for parent, _, reqs in records:
    for raw in reqs:
        q = Requirement(raw); on = q.marker is None or q.marker.evaluate(env)
        if canonicalize_name(q.name) == 'hf-xet': xet.append({'parent': parent, 'req': raw, 'active': on})
        if not on: inactive += 1; continue
        active.append((parent, canonicalize_name(q.name)))
        v = vers.get(canonicalize_name(q.name))
        if q.extras or v is None or not q.specifier.contains(Version(v), prereleases=True): unsat.append(raw)
check('Q0R02.hf_xet_inactive_on_AMD64', env['platform_machine'] == 'AMD64' and xet and not any(x['active'] for x in xet), xet)
check('closure.no_unsatisfied_active_requirement', not unsat, unsat)
check('closure.edge_counts_match_author', (len(active), inactive, len(lock['edges'])) == (35, 815, 850), {'active': len(active), 'inactive': inactive, 'lock_edges': len(lock['edges'])})
top = {canonicalize_name(x) for x in ['torch', 'torchvision', 'transformers', 'huggingface-hub', 'tokenizers', 'safetensors', 'pillow', 'numpy', 'requests', 'tqdm', 'addict', 'einops', 'easydict', 'pypdfium2', 'psutil']}
reach, frontier = set(top), list(top)
while frontier:
    n = frontier.pop()
    for p, c in active:
        if canonicalize_name(p) == n and c not in reach: reach.add(c); frontier.append(c)
check('closure.every_artifact_reachable_from_15_top_level', reach == set(vers), {'unreachable': sorted(set(vers) - reach), 'missing': sorted(reach - set(vers))})
arts = {canonicalize_name(a['name']): a for a in lock['artifacts']}
mism, hosts, tags_bad = [], set(), []
my_tags = set(sys_tags())
for r in pypi:
    a = arts[canonicalize_name(r['name'])]; w = r['artifact']
    if (a['filename'], a['url'], a['size'], a['sha256']) != (w['filename'], w['url'], w['size'], w['digests']['sha256']) or w['yanked']: mism.append(r['name'])
for a in lock['artifacts']:
    n, v, _, t = parse_wheel_filename(a['filename'])
    if canonicalize_name(n) != canonicalize_name(a['name']) or str(v) != a['version']: mism.append(a['filename'])
    if not (t & my_tags): tags_bad.append(a['filename'])
    hosts.add(urllib.parse.urlparse(a['url']).hostname)
check('closure.lock_artifacts_equal_raw_metadata_selections', not mism and len(arts) == 32 and sum(a['size'] for a in lock['artifacts']) == 1974477651, mism)
check('closure.all_wheel_tags_compatible_with_this_interpreter', not tags_bad, tags_bad)
check('closure.artifact_hosts_official', hosts <= {'files.pythonhosted.org', 'download-r2.pytorch.org'}, sorted(hosts))
forbidden = {'hf-xet', 'triton', 'sentencepiece', 'protobuf', 'tiktoken', 'gguf', 'accelerate', 'flash-attn', 'xformers'} & set(vers)
check('closure.no_optional_backend_selected', not forbidden, sorted(forbidden))
prior = {canonicalize_name(x['name']): x for x in load(P / 'proposed-artifacts.json')}
check('closure.thirteen_original_pins_unchanged', all((arts[k]['filename'], arts[k]['sha256'], arts[k]['size']) == (v['filename'], v['sha256'], v['size']) for k, v in prior.items()), sorted(prior))

# ---- torchvision artifact identity: /001 vs /007 and kickoff ------------------------------
old = {r['package']: r for r in load(P / 'cuda-wheel-metadata.json')}; new = {r['name']: r for r in cuda}
tv = new['torchvision']; KICK = 'https://download-r2.pytorch.org/whl/cu130/torchvision-0.28.0%2Bcu130-cp312-cp312-win_amd64.whl'
tvmeta = tv['metadata_text'].encode('utf-8'); msg = email.message_from_bytes(tvmeta)
check('tv.identity_stable_and_matches_kickoff',
      tv['url'] == old['torchvision']['url'] == KICK and tv['filename'] == 'torchvision-0.28.0+cu130-cp312-cp312-win_amd64.whl' and tv['size'] == 9091113 == int(old['torchvision']['wheel_head']['Content-Length'])
      and tv['sha256'] is None and arts['torchvision']['sha256'] is None and tv['head_receipt']['headers'].get('ETag') == old['torchvision']['wheel_head']['ETag'],
      {'url': tv['url'], 'size': tv['size'], 'etag_001': old['torchvision']['wheel_head']['ETag'], 'etag_007': tv['head_receipt']['headers'].get('ETag'),
       'last_modified_007': tv['head_receipt']['headers'].get('Last-Modified'), 'head_final_url': tv['head_receipt']['final_url']})
check('tv.metadata_text_unchanged_and_hash',
      tv['metadata_text'] == old['torchvision']['metadata_text'] and sha(tvmeta) == 'f8e91ee987603053e2166e2e4063ddcfb533f266c88bae82b7f79119aadceb59' and msg['Name'] == 'torchvision'
      and msg['Version'] == '0.28.0+cu130' and 'torch (==2.13.0)' in msg.get_all('Requires-Dist'), {'sha256': sha(tvmeta), 'requires_dist': msg.get_all('Requires-Dist')})
alt = load(R / 'torchvision-alternate-indexes.json')
check('tv.no_publisher_wheel_digest_in_either_index', len(alt) == 2 and all(len(a['matches']) == 1 and '#sha256=' not in a['matches'][0] for a in alt), [a['content_type'] for a in alt])
tch = new['torch']
check('torch.publisher_digest_unchanged', tch['sha256'] == old['torch']['published_wheel_sha256'] == '2efab1e83604ca628c6d85b9e188c153690980498d1297081a9dad704919303c' and tch['size'] == 1915519202)

# ---- read-only host/storage observation --------------------------------------------------
root = pathlib.Path(r'C:\Users\jackg\eLedgerCare-Q0\WP-0005'); du = shutil.disk_usage('C:\\')
host = {'observed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'storage_root_exists': root.exists(), 'storage_parent_exists': root.parent.exists(),
        'c_free_bytes': du.free, 'c_total_bytes': du.total, 'python': sys.version, 'executable': sys.executable}
check('host.storage_root_absent', not host['storage_root_exists'])
check('host.free_ge_58GiB_gate', du.free >= 58 * 2**30, du.free)

summary = {'tool': 'eld-q0-reviewer review_checks.py', 'started_utc': started, 'repo_head': subprocess.run(['git', '-C', str(repo), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip(),
           'script_sha256': sha(pathlib.Path(__file__).read_bytes()), 'host': host, 'results': results, 'failures': failures, 'pass': not failures}
out_path.write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8', newline='\n')
print(('PASS' if not failures else 'FAIL ' + ', '.join(failures)) + f' ({len(results)} checks)')
sys.exit(1 if failures else 0)
