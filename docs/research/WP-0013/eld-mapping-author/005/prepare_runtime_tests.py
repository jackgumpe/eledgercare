"""Adapt accepted CPU supervision counterexamples without running observers."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]


def main():
    source = (ROOT/'qualification/coverage_v1/tests/test_runtime.py').read_text(encoding='utf-8')
    source = source.replace('qualification.coverage_v1', 'qualification.mapping_v2')
    source = source.replace('wp0011-coverage', 'wp0013-vocabulary').replace('eLedgerCare-CoverageV1-', 'eLedgerCare-MappingV2-')
    start = source.index('    def test_runtime_worker_and_model_settings_preserve_accepted_source(self):')
    end = source.index('    def test_exact_storage_time_log_and_stall_guards(self):', start)
    source = source[:start] + '''    def test_runtime_worker_and_model_settings_preserve_accepted_source(self):
        old=git('show','253519e07e7d45cf1f5ecb3e03053582f7f7d4cc:qualification/coverage_v1/runtime.py').decode()
        expected=old.replace('eLedgerCare-CoverageV1-','eLedgerCare-MappingV2-').replace('coverage_v1_source_commit','mapping_v2_source_commit')
        current=(HERE/'runtime.py').read_text().split('\\ndef worker(',1)[1]
        identity_block="    if parent_plan.get('supervisor_identity')!=process_identity(parent_plan['supervisor_pid']):\\n        raise PermissionError('Supervisor creation identity changed')\\n    worker_identity=process_identity(os.getpid())\\n"
        self.assertIn(identity_block,current)
        current=current.replace(identity_block,'').replace(",'worker_identity':worker_identity",'')
        self.assertEqual(current,expected.split('\\ndef worker(',1)[1])
        previous=json.loads(git('show','253519e07e7d45cf1f5ecb3e03053582f7f7d4cc:qualification/coverage_v1/protocol.json'))
        p=protocol()
        for key in ('model','renderer','call','guards','gpu','read_only_q0_root','model_relative','notice_relative','storage_cap_bytes','free_floor_bytes','warmups','historical_warmups'):
            self.assertEqual(p[key],previous[key],key)

    def test_current_owned_process_creation_identity_is_stable(self):
        first=runtime.process_identity(os.getpid());second=runtime.process_identity(os.getpid())
        self.assertEqual(first,second);self.assertEqual(first['pid'],os.getpid())
        self.assertGreater(first['creation_filetime_100ns'],0)

''' + source[end:]
    source = source.replace("(runtime,'git',{'return_value':b'cpu-head'}),", "(runtime,'git',{'return_value':b'cpu-head'}),\n                    (runtime,'process_identity',{'side_effect':lambda pid:{'pid':pid,'creation_filetime_100ns':pid,'created_utc':'CPU'}}),")
    source = source.replace("if case=='normal':self.assertTrue(all(c['status']=='completed' for c in result['calls']))", "if case=='normal':\n                self.assertTrue(all(c['status']=='completed' for c in result['calls']))\n                self.assertEqual(result['child_launcher_identity']['pid'],proc.pid)\n                self.assertEqual(result['supervisor_identity']['pid'],os.getpid())")
    with (ROOT/'qualification/mapping_v2/tests/test_runtime.py').open('x', encoding='utf-8', newline='\n') as stream: stream.write(source)


if __name__ == '__main__': main()
