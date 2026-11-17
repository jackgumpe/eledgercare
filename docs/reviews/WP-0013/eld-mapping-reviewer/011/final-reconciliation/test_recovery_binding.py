"""Only four binding replacements; actual route guard positives and negatives."""
import ast,subprocess,unittest
from pathlib import Path,PurePosixPath,PureWindowsPath
ROOT=Path(__file__).resolve().parents[6]
OWN=Path(__file__).resolve().parents[2]/'008'
OLD=OWN/'compare_published_original007_v2.py';NEW=OWN/'compare_published_recovery012.py'
AUTHOR='docs/research/WP-0013/eld-mapping-author/012/evidence/attempt-1/run'
REVIEWER='docs/reviews/WP-0013/eld-mapping-reviewer/008/results/attempt-1/run'
REPLACE={
 b"SOURCE='c0a1af638e807803b6014b3a93ecb7f9946ce6e1'":b"SOURCE='ae790497f3fdd10573e8179757416bc2d1736250'",
 b"TREE='4477104eb2a3c73f496ef451cef9578f54d96518'":b"TREE='8fd68c96bb18ca0177f227ad9a82505090d997b0'",
 b"PROTOCOL='46a0d3e7bec0f14a3911eb7365385b7d132db8e8a72c8edb3f030aeeda124ec2'":b"PROTOCOL='ef648a3cd52df16ed6ed352e666ffedf789148100d640e2582cf13f76b6f9783'",
 b"prefix.startswith(('docs/evidence/WP-0013/','docs/reviews/WP-0013/')) or (spec['owner']=='author' and prefix=='docs/research/WP-0013/eld-mapping-author/007/evidence/attempt-1/run')":b"(spec['owner']=='author' and prefix=='docs/research/WP-0013/eld-mapping-author/012/evidence/attempt-1/run') or (spec['owner']=='reviewer' and prefix=='docs/reviews/WP-0013/eld-mapping-reviewer/008/results/attempt-1/run')"}
def guard(path,owner):
    tree=ast.parse(NEW.read_text());funcs=[n for n in tree.body if isinstance(n,ast.FunctionDef)]
    nodes=[n for n in funcs if n.name in ('safe','require')];audit=next(n for n in funcs if n.name=='audit_published')
    i=next(i for i,n in enumerate(audit.body) if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='prefix')
    nodes.extend(audit.body[i:i+2]);env={'PurePosixPath':PurePosixPath,'PureWindowsPath':PureWindowsPath,'spec':{'run_prefix':path,'owner':owner}}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(NEW),'exec'),env);return env['prefix']
class BindingTests(unittest.TestCase):
    def test_exact_four_replacements_and_originals_immutable(self):
        original=OLD.read_bytes()
        self.assertEqual(original,subprocess.check_output(['git','show','0a2c68357f8884095a7f40447e8b5ea4e68435ed:'+OLD.relative_to(ROOT).as_posix()],cwd=ROOT))
        baseline=OWN/'compare_published.py'
        self.assertEqual(baseline.read_bytes(),subprocess.check_output(['git','show','8e0b8090dc0471bf7162b1d64bc3251df693a2ad:'+baseline.relative_to(ROOT).as_posix()],cwd=ROOT))
        for a,b in REPLACE.items():self.assertEqual(original.count(a),1);original=original.replace(a,b)
        self.assertEqual(NEW.read_bytes(),original)
    def test_exact_author_and_reviewer_routes(self):
        self.assertEqual(guard(AUTHOR,'author'),AUTHOR);self.assertEqual(guard(REVIEWER,'reviewer'),REVIEWER)
    def test_owner_attempt_sequence_and_broad_prefix_rejection(self):
        cases=[(AUTHOR,'reviewer'),(REVIEWER,'author'),(AUTHOR.replace('/012/','/007/'),'author'),
               (AUTHOR.replace('attempt-1','attempt-2'),'author'),(REVIEWER.replace('attempt-1','attempt-2'),'reviewer'),
               ('docs/evidence/WP-0013/run','author'),('docs/reviews/WP-0013/someone/run','reviewer'),
               (AUTHOR+'/raw.txt','author'),(REVIEWER+'-other','reviewer')]
        for path,owner in cases:
            with self.subTest(path=path,owner=owner),self.assertRaises(ValueError):guard(path,owner)
    def test_unsafe_paths_rejected(self):
        for path in [AUTHOR+'/../run','/'+AUTHOR,'C:/'+AUTHOR,AUTHOR+'/',AUTHOR.replace('/012/','//012/')]:
            with self.subTest(path=path),self.assertRaises(ValueError):guard(path,'author')
if __name__=='__main__':unittest.main(verbosity=2)
