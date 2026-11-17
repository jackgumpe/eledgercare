"""Three independent predictions on one raw output, unchanged scores/policy counts."""
import json
from pathlib import Path
from .common import parse_native, ParseError, load_json, sha, write, summarize
from .mapper import extract_prediction
from .protocol.scoring import original_comparison, score_policy, summarize_policy
from .release import read_release, protocol, schedule, fixture, read_artifact, require


def paired(raw, expected, reference, completion):
    try:
        v2 = extract_prediction(parse_native(raw))
    except (ParseError, ValueError, TypeError) as exc:
        v2 = {'fields': [], 'tables': [], 'anchors': [], 'unmapped': [{'kind': 'parse_failure', 'detail': str(exc)}],
              'pages': [], 'parse_errors': [str(exc)]}
    return original_comparison(raw, expected, reference, completion, v2)


def validated_calls(result, p, owner, run):
    """Unchanged coverage-v1 progression/observation rules with the WP13 schema."""
    require(isinstance(result, dict) and result.get('schema') == 'eld-mapping-v2-run/1' and
            'failure' in result and (result['failure'] is None or isinstance(result['failure'], str)), 'Malformed run result')
    calls = result.get('calls'); plan = schedule(p, owner)
    require(isinstance(calls, list) and len(calls) == len(plan), 'Finite run denominator mismatch')
    stopped = False
    for call, wanted in zip(calls, plan):
        require(isinstance(call, dict) and all(call.get(k) == v for k, v in wanted.items()), 'Finite call order mismatch')
        require({'status', 'observation', 'observation_status'} <= call.keys(), 'Incomplete call record')
        state = call['status']; obs = call['observation']; availability = call['observation_status']
        require(state in ('completed', 'failed', 'not_run_after_failure'), 'Unknown call status')
        require(availability in ('available', 'absent', 'unavailable'), 'Unknown observation status')
        require(not stopped or state == 'not_run_after_failure', 'Call executed after first failure/unavailable call')
        if state != 'completed': stopped = True
        if state == 'not_run_after_failure': require(obs is None, 'Not-run call has a scored observation')
        elif state == 'completed': require(isinstance(obs, str) and bool(obs) and availability == 'available', 'Completed call observation unavailable')
        if obs is not None: require(isinstance(obs, str) and bool(obs) and availability == 'available', 'Malformed observation reference')
    require(not stopped or bool(result['failure']), 'Incomplete calls without run failure')
    raws = []
    for call in calls:
        raw = None
        if call['observation'] is not None:
            path = (run/call['observation']).resolve(); path.relative_to(run); obs = load_json(path)
            require(isinstance(obs, dict) and isinstance(obs.get('flags'), list), 'Malformed call observation')
            if call['status'] == 'completed':
                require(not obs['flags'] and not obs.get('error') and isinstance(obs.get('raw_output'), dict), 'Completed call contains failure or missing raw metadata')
                require(obs['raw_output'].get('truncated_by_writer') is False, 'Completed raw capture unavailable/truncated')
            if 'raw_output' in obs:
                meta = obs['raw_output']; require(isinstance(meta, dict) and isinstance(meta.get('name'), str) and bool(meta['name']), 'Malformed raw metadata')
                raw_path = (path.parent/meta['name']).resolve(); raw_path.relative_to(run)
                data = raw_path.read_bytes(); require(sha(data) == meta.get('sha256_written'), 'Raw hash mismatch'); raw = data.decode('utf-8')
        raws.append(raw)
    return calls, raws


def score_run(run, output, authority, release_path, owner):
    r = read_release(authority, release_path, owner, execution=False); p = protocol(); run = Path(run).resolve()
    run.relative_to(Path(r['runtime_root']).resolve()/'runs'/owner)
    result = load_json(run/'run-result.json')
    require(result['release'] == r and result.get('executing_head') == r['executing_head'], 'Run/release/executing HEAD mismatch')
    calls, raws = validated_calls(result, p, owner, run)
    records = []
    for call, raw in zip(calls, raws):
        if call['excluded']: continue
        fx = fixture(p, call['fixture_id']); artifacts = {a['role']: a for a in fx['artifacts']}
        expected, reference, policy = [json.loads(read_artifact(r, p, artifacts[role])) for role in ('expected', 'reference', 'policy')]
        comparison = paired(raw or '', expected, reference, call['status'])
        policy_scores = {key: score_policy(pred, expected, reference, policy, call['status']) for key, pred in comparison['predictions'].items()}
        records.append({'fixture_id': fx['fixture_id'], 'raw_available': raw is not None, **comparison, 'policy_scores': policy_scores})
    packet = {'schema': 'eld-mapping-v2-paired/1', 'owner': owner, 'executing_head': r['executing_head'],
              'run_result_sha256': sha((run/'run-result.json').read_bytes()), 'records': records,
              'historical_summary': {key: summarize([row['scores'][key] for row in records]) for key in ('b0', 'mapping_v1', 'mapping_v2')},
              'policy_summary': {key: summarize_policy([row['policy_scores'][key] for row in records]) for key in ('b0', 'mapping_v1', 'mapping_v2')} if owner == 'author' else
                  {'sentinel_documents': 1, 'preselected_id': p['reviewer_sentinel'], 'limit': 'Single prespecified sentinel; not the twelve-author-document population.'},
              'interpretation': 'Unchanged end-to-end metrics and accepted separate policy metrics on identical raw outputs. Gains, losses, neutral and unavailable all retained; abstentions are not correct values.'}
    write(output, packet)
