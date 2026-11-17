"""Execute actual parsed path-guard statements; no actual result packet consumed."""
import ast
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import unittest

OWN = Path(__file__).resolve().parents[2] / '008'
OLD = OWN / 'compare_published.py'
NEW = OWN / 'compare_published_original007_v2.py'
EXACT = 'docs/research/WP-0013/eld-mapping-author/007/evidence/attempt-1/run'
BEFORE = b"prefix=safe(spec['run_prefix']);require(prefix.startswith(('docs/evidence/WP-0013/','docs/reviews/WP-0013/')),'Only immutable WP-0013 published evidence accepted')"
AFTER = b"prefix=safe(spec['run_prefix']);require(prefix.startswith(('docs/evidence/WP-0013/','docs/reviews/WP-0013/')) or (spec['owner']=='author' and prefix=='docs/research/WP-0013/eld-mapping-author/007/evidence/attempt-1/run'),'Only immutable WP-0013 published evidence accepted')"


def guard(path, owner, source=NEW):
    tree = ast.parse(source.read_text())
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    checks = [n for n in funcs if n.name in ('require', 'safe')]
    audit = next(n for n in funcs if n.name == 'audit_published')
    index = next(i for i,n in enumerate(audit.body) if isinstance(n,ast.Assign)
                 and isinstance(n.targets[0],ast.Name) and n.targets[0].id == 'prefix')
    checks.extend(audit.body[index:index+2])
    module = ast.Module(body=checks, type_ignores=[])
    env = {'PurePosixPath': PurePosixPath, 'PureWindowsPath': PureWindowsPath,
           'spec': {'owner': owner, 'run_prefix': path}}
    exec(compile(module, str(source), 'exec'), env)
    return env['prefix']


class PrefixTests(unittest.TestCase):
    def test_only_exact_byte_replacement_and_pins_unchanged(self):
        before,after=OLD.read_bytes(),NEW.read_bytes()
        self.assertEqual(before.count(BEFORE),1)
        self.assertEqual(after,before.replace(BEFORE,AFTER))
        for name in ('SOURCE','TREE','PROTOCOL','CORPUS','CORPUS_TREE'):
            def value(path):
                return next(ast.literal_eval(n.value) for n in ast.parse(path.read_text()).body
                    if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id==name)
            self.assertEqual(value(OLD),value(NEW))

    def test_actual_author007_exact_prefix_new_accept_old_reject(self):
        self.assertEqual(guard(EXACT,'author'),EXACT)
        with self.assertRaisesRegex(ValueError,'Only immutable'):
            guard(EXACT,'author',OLD)

    def test_other_owner_sequence_attempt_or_descendant_rejected(self):
        cases=[(EXACT,'reviewer'),(EXACT.replace('/007/','/012/'),'author'),
               (EXACT.replace('attempt-1','attempt-2'),'author'),
               (EXACT.replace('eld-mapping-author','another-author'),'author'),
               (EXACT+'-copy','author'),(EXACT+'/raw.txt','author'),
               ('docs/research/WP-0013/','author')]
        for path,owner in cases:
            with self.subTest(path=path,owner=owner),self.assertRaises(ValueError):guard(path,owner)

    def test_prior_prefixes_and_unsafe_path_rules_preserved(self):
        for path,owner in [('docs/evidence/WP-0013/author/run','author'),
                           ('docs/reviews/WP-0013/reviewer/run','reviewer')]:
            self.assertEqual(guard(path,owner),guard(path,owner,OLD))
        for path in [EXACT+'/../run','/'+EXACT,'C:/'+EXACT,EXACT+'/',EXACT.replace('/007/','//007/')]:
            with self.subTest(path=path),self.assertRaises(ValueError):guard(path,'author')


if __name__=='__main__':unittest.main(verbosity=2)
