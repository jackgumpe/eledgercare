"""Read-only per-field comparison with the two published WP-0044 venv worker cuts."""
import hashlib
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import state as s

HISTORIC = s.HERE.parent / "WP-0044/blind-results.json"
OLD_MANIFEST = s.HERE.parent / "WP-0044/manifest.json"
UNMEASURED = {"availability":"unmeasured"}

def comparison(manifest, live_root=None):
    if s.sha(HISTORIC) != "4a407a3c75ac4e1447a8cdc4bd5d2553fef72b3f7f4cec8ad302cfd7f6764502":
        raise ValueError("historical observed bytes changed")
    if s.sha(OLD_MANIFEST) != "87a4ded6ceac20c88bd5108b0b912c844c23c690996f9d64ba50fc02dddde7c1":
        raise ValueError("historical manifest changed")
    old, homes = s.read(HISTORIC), {}
    for i, arm in enumerate(old["arms"]):
        rows = {}
        def add(key, historical, direct, intent="same"):
            if historical == UNMEASURED:
                finding = "historic_measurement_unavailable"
            elif direct == UNMEASURED:
                finding = "direct_measurement_outside_selected_coverage"
            elif historical == direct:
                finding = "match"
            else:
                finding = "intentional_difference" if intent == "diff" else "unexpected_difference"
            rows[key] = {"venv":historical, "direct":direct,"finding":finding}
        f = arm["process"]["worker"]
        fields = f["fields"]
        v = (s.read(live_root / f"arm-{i}" / "worker.json")["snapshot"]
             if live_root else manifest["roles"][f"worker{i}"])
        cmd, r = v["command"], v["runtime"]
        proc = arm["process"]["observed"]
        add("image.supervisor_or_venv_launcher",proc["L.image"],manifest["base"],"diff")
        add("image.interpreter",proc["I.image"],r["image_sha256"])
        add("script_sha256",fields["A.script"],cmd["script"]["sha256"],"diff")
        add("orig_argv", [f["orig_argv0"],*fields["A.args"]],cmd["orig_argv"],"diff")
        add("orig_argv0",f["orig_argv0"],cmd["orig_argv"][0])
        add("orig_argv_tail",fields["A.args"],cmd["orig_argv"][1:],"diff")
        for k in ("cwd","argv"): add(k,UNMEASURED,cmd[k])
        add("exe",f["executable"],r["exe"],"diff")
        add("prefix",fields["C.prefix"],r["prefix"],"diff")
        for k in ("base_exe","base_prefix","sys_path","site_loaded","environment_names"):
            add(k,UNMEASURED,r[k])
        add("pyvenv_cfg_active",fields["C.pyvenv"],r["pyvenv_cfg"]["@base/pyvenv.cfg"],"diff")
        add("pyvenv_cfg_alternate",UNMEASURED,r["pyvenv_cfg"]["@base-parent/pyvenv.cfg"])
        add("include_system_site_packages",fields["C.include_system"],None,"diff")
        add("effective_pth",fields["C.pth"],r["effective_pth"])
        add("visible_sitecustomize",fields["C.sitecustomize"],r["sitecustomize"])
        for k,value in r["flags"].items(): add("flags."+k,UNMEASURED,value)
        for k,value in r["environment"].items(): add("env."+k,fields.get("C."+k,UNMEASURED),value)
        modules = dict(fields["C.modules"])
        for k in sorted(modules.keys() | r["modules"].keys()):
            old_value = modules.get(k,{"loaded":False})
            new_value = r["modules"].get(k,UNMEASURED)
            add("module."+k,old_value,new_value,
                "diff" if k in ("__main__","state","win","ctypes","_ctypes","subprocess") else "same")
        add("version_frozen_preflight", s.read(OLD_MANIFEST)["version"],r["version"])
        homes[str(i)] = rows
    return {"date_utc":"2026-11-27","historical_revision":"f4d3bd49e7c106c22547aa6f75ca136f0426f6d7",
            "observed_archive_sha256":s.sha(HISTORIC),"historic_manifest_sha256":s.sha(OLD_MANIFEST),
            "direct_cut":"actual decisive worker" if live_root else "predeclared medium-token worker calibration",
            "arms":homes}

if __name__ == "__main__":
    dest = Path(sys.argv[1])
    s.save(dest,comparison(s.read(s.HERE / "manifest.json"), Path(sys.argv[2]) if len(sys.argv)>2 else None))
