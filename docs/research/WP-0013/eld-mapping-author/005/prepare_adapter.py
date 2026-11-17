"""Materialize a bounded namespace adaptation of accepted WP11 supervision.

Reads only accepted source and the public hash reservation, never fresh content.
The generated runtime is inspected and frozen before execution/check evidence.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
TARGET = ROOT / 'qualification/mapping_v2'


def main():
    source = (ROOT / 'qualification/coverage_v1/runtime.py').read_text(encoding='utf-8')
    source = source.replace('Finite WP-0011 adaptation of accepted mapping-v1 runtime at 23e023045b335540d830ce01b75be247552a63f1.',
                            'Finite WP-0013 adaptation of accepted coverage-v1 runtime at 253519e07e7d45cf1f5ecb3e03053582f7f7d4cc.')
    source = source.replace('eLedgerCare-CoverageV1-', 'eLedgerCare-MappingV2-').replace('eld-coverage-v1-run/1', 'eld-mapping-v2-run/1')
    source = source.replace("'coverage_v1_source_commit'", "'mapping_v2_source_commit'")
    with (TARGET / 'runtime.py').open('x', encoding='utf-8', newline='\n') as stream: stream.write(source)
    p = json.loads((ROOT / 'qualification/coverage_v1/protocol.json').read_text(encoding='utf-8'))
    reservation = json.loads((ROOT / 'docs/evaluation/WP-0013/reservation/reservation.json').read_text(encoding='utf-8'))
    for key in ('diagnostic_matrix', 'diagnostic_schema', 'stage_measurements', 'primary_metric', 'paired_design'):
        p.pop(key)
    p.update(schema='eld-mapping-v2-runtime-protocol/1', status='CPU source candidate; no unseal or runtime release',
             runtime_roots={owner: 'C:/Users/jackg/eLedgerCare-Vocabulary/WP-0013/' + owner for owner in ('author', 'reviewer')},
             public_reservation_path='docs/evaluation/WP-0013/reservation/reservation.json',
             public_reservation_commit='b50b2a3bc22927890c8f391943f2a3fe9168d0da',
             public_reservation_sha256='533f4be35fb89efd9e288c0470201457b5ab32373eab3112ae283b42febcfea5',
             publication_prefix='evaluation/mapping_v2/', reviewer_sentinel='WP13-F04-conflict-v0',
             source_review_path='docs/agent-reports/eld-mapping-reviewer/WP-0013/006_2026-11-17_review_eld-mapping-reviewer.md',
             admission_review_path='docs/agent-reports/eld-mapping-reviewer/WP-0013/004_2026-11-17_review_eld-mapping-reviewer.md',
             fresh_fixtures=reservation['fixtures'], coverage_v1_tree='6bdab544c9fe26cbf093cc765212db2a2e7a97a5',
             accepted_protocol_source='6207daf1dc9cbdd141d083ca2d8d1e7507c63b09',
             accepted_protocol_sha256='aa0d8f183f9f0161c6e47b56a6f2cd844d6ad3f31e772b9761aa0ad618f6a372',
             accepted_catalog_sha256='35a99a213b80476747c7a136a4109ac45bc7944c77b0a3dcf0f348f107dd37a2',
             policy_schema='eld-mapping-v2-policy/1',
             primary_metric='Unchanged printed and typed end-to-end scores; separate accepted policy metrics, gains/losses/unavailable all retained.',
             paired_design='One unchanged raw output feeds B0/v1/v2; four independent families, three cases each.')
    p['sentinel_policy'].update(required_categories=['one_page_conflict'], fixture_id=p['reviewer_sentinel'])
    with (TARGET / 'runtime_protocol.json').open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(p, stream, indent=2); stream.write('\n')


if __name__ == '__main__': main()
