"""Exact owned CPU evidence collection with complete original-to-copy mapping."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[6]
OWN=Path(__file__).resolve().parents[1]/'final-evidence/attempt-1'
def sha(data):return hashlib.sha256(data).hexdigest()
def main():
    assert not OWN.exists();OWN.mkdir(parents=True)
    sources={name:ROOT/'.scratch/wp0013-reviewer-011-final'/folder for name,folder in [
        ('selection','selection-attempt-1'),('worker','worker-attempt-1'),('source','source-attempt-1'),
        ('recovery-binding','recovery-binding-attempt-1'),('publication','publication-attempt-1')]}
    sources['standard']=ROOT/'.scratch/wp0013-reviewer-011/final-standard-attempt-1'
    rows=[]
    for phase,src in sources.items():
        assert src.is_dir()
        for path in sorted(src.rglob('*')):
            if not path.is_file():continue
            assert not path.is_symlink() and path.resolve().is_relative_to(src.resolve())
            rel=path.relative_to(src);target=OWN/phase/rel
            if path.suffix.lower()=='.exe':target=target.with_name(target.name+'.fixture-bytes')
            target.parent.mkdir(parents=True,exist_ok=True);data=path.read_bytes()
            with target.open('xb') as f:f.write(data)
            assert target.read_bytes()==data
            rows.append({'phase':phase,'original':str(path),'original_relative_path':rel.as_posix(),
                'published_path':target.relative_to(ROOT).as_posix(),'bytes':len(data),'sha256':sha(data)})
    value={'files':rows,'original_files':len(rows),'all_originals_copied_exact':True,'retained_only':[],
        'invalid_executable_fixture_suffix':'.fixture-bytes','scope':'Independent CPU test evidence only; no runtime model outputs'}
    with (OWN/'collection.json').open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2);f.write('\n')
    print(json.dumps({'files':len(rows),'bytes':sum(r['bytes'] for r in rows),'phases':{k:sum(r['phase']==k for r in rows) for k in sources}}))
if __name__=='__main__':main()
