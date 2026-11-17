"""Owned CPU-only wrapper/collector tests; no runtime, GPU or backend call."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import execute_wrapper as w
import collect_evidence as c

class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.scratch=w.ROOT/'.scratch/wp0011-reviewer-wrapper-tests';self.scratch.mkdir(parents=True,exist_ok=True)

    def test_actual_owned_child_exit_and_empty_logs_are_separate(self):
        for code in (0,7):
            with self.subTest(exit=code),tempfile.TemporaryDirectory(dir=self.scratch) as tmp:
                attempt=Path(tmp)
                receipt=w.invoke([sys.executable,'-I','-B','-c',f'import sys;sys.exit({code})'],attempt,'cpu-test',{'scope':'public CPU-only test'})
                self.assertEqual(receipt['supervisor_exit_code'],code);self.assertTrue(receipt['observed_exit'])
                self.assertIsNone(receipt['wrapper_error'])
                self.assertEqual((attempt/'cpu-test.stdout.txt').read_bytes(),b'')
                self.assertEqual((attempt/'cpu-test.stderr.txt').read_bytes(),b'')
                self.assertGreater(receipt['supervisor_pid'],0)
                self.assertTrue((attempt/'cpu-test-launch.json').exists() and (attempt/'cpu-test-started.json').exists())

    def test_output_capture_preserves_bytes(self):
        with tempfile.TemporaryDirectory(dir=self.scratch) as tmp:
            attempt=Path(tmp);code="import sys;sys.stdout.buffer.write(b'one\\r\\ntwo\\n');sys.stderr.buffer.write(b'error\\r\\n')"
            receipt=w.invoke([sys.executable,'-I','-B','-c',code],attempt,'cpu-test',{'scope':'public CPU-only test'})
            self.assertEqual((attempt/'cpu-test.stdout.txt').read_bytes(),b'one\r\ntwo\n')
            self.assertEqual((attempt/'cpu-test.stderr.txt').read_bytes(),b'error\r\n')
            self.assertEqual(receipt['stdout']['sha256'],w.sha(b'one\r\ntwo\n'))

    def test_missing_release_and_escaping_paths_rejected(self):
        with self.assertRaises(ValueError):w.checked_release('not-a-release',True)
        with self.assertRaises(ValueError):w.inside(w.ROOT.parent,w.SCRATCH)
        with tempfile.TemporaryDirectory(dir=self.scratch) as tmp:
            path=Path(tmp)/'exclusive.json';w.write(path,{'first':True})
            with self.assertRaises(FileExistsError):w.write(path,{'second':True})
            self.assertEqual(w.load(path),{'first':True})

    def test_collection_retains_failures_missing_and_cache_inventory(self):
        with tempfile.TemporaryDirectory(dir=self.scratch) as tmp:
            root=Path(tmp);run=root/'runtime';attempt=root/'attempt';dest=root/'publication'
            (run/'evidence').mkdir(parents=True);(run/'hf-modules').mkdir();attempt.mkdir()
            (run/'run-result.json').write_bytes(b'{"failure":"synthetic failure"}\r\n')
            (run/'evidence/raw.txt').write_bytes(b'ORIGINAL\r\n');(run/'hf-modules/code.py').write_bytes(b'cache')
            (attempt/'execute-completion.json').write_bytes(b'{"supervisor_exit_code":7}')
            result=c.collect_files(run,attempt,dest)
            self.assertEqual(result['copy_count'],3);self.assertEqual(result['run_files'],2)
            self.assertEqual(len(result['excluded_cache_files']),1)
            self.assertTrue(any(x['path']=='scores.json' and x['status']=='absent' for x in result['missing_wrapper_artifacts']))
            self.assertFalse((dest/'launch/scores.json').exists());self.assertFalse((dest/'run/hf-modules').exists())
            self.assertEqual((dest/'run/evidence/raw.txt').read_bytes(),b'ORIGINAL\r\n')
            self.assertEqual((run/'evidence/raw.txt').read_bytes(),b'ORIGINAL\r\n')
            with self.assertRaises(FileExistsError):c.collect_files(run,attempt,dest)
            manifest=w.load(dest/'run-copy-manifest.json');self.assertEqual(len(manifest['files']),2)
            self.assertTrue(all(x['sha256']==x['original_sha256'] for x in manifest['files']))

    def test_reparse_and_unknown_subtree_rejected(self):
        with tempfile.TemporaryDirectory(dir=self.scratch) as tmp:
            root=Path(tmp);actual=root.stat()
            class Reparse:
                st_mode=actual.st_mode;st_file_attributes=0x400
            with patch.object(Path,'stat',return_value=Reparse()),self.assertRaisesRegex(ValueError,'Reparse'):list(c.files(root))
            run=root/'runtime';attempt=root/'attempt';(run/'unexpected').mkdir(parents=True);attempt.mkdir()
            (run/'unexpected/file.txt').write_bytes(b'keep')
            with self.assertRaisesRegex(ValueError,'Unclassified'):c.collect_files(run,attempt,root/'publication')
            self.assertEqual((run/'unexpected/file.txt').read_bytes(),b'keep')

if __name__=='__main__':unittest.main()
