"""Pre-decisive ordinary-account observation at the normal participant script's cut."""
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import state as s
import win

def main():
    win.ordinary()
    out = s.role_root() / sys.argv[1]
    out.mkdir()
    (out / "calibration.only").touch(exist_ok=False)
    manifest = {"version": 1, "base": s.sha(win.BASE), "source": {
        f.name: s.sha(f) for f in sorted(s.HERE.glob("*.py"))}, "roles": {}}
    for role in ("supervisor", "worker"):
        for selection in (0, 1):
            r = subprocess.run(s.argv(role, selection), cwd=out, env=s.env(), check=True,
                               stdin=subprocess.DEVNULL, stdout=None, stderr=None, timeout=15)
            value = s.read(out / f"{role}-{selection}.json")
            manifest["roles"][f"{role}{selection}"] = {k: value[k] for k in ("command", "runtime")}
    s.save(out / "manifest.json", manifest)

if __name__ == "__main__":
    main()
