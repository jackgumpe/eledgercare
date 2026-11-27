"""Compare both published 0044 routes at their documented cuts; missing measurements stay missing."""
from pathlib import Path
from common import HERE, OLD, BASE, ENV_KEYS, read


def normalize_module(rec):
    if "kind" in rec:
        return [rec["kind"]]
    return [rec["path"].replace("@base/",str(BASE.parent).replace("\\","/")+"/"),rec["sha256"]]


def compare_old(witness, arm):
    cfg=witness["worker"]["config"]
    now=cfg["all_modules"]
    author_arm=read(HERE.parents[1]/"research"/"WP-0044"/"blind-results.json")["arms"][arm]["process"]["worker"]
    ref=read(OLD/"manifest.json")
    reviewer=read(OLD/"native-events.json")["AB"[arm]]
    assert reviewer["config_matches_manifest"] and reviewer["args_match_manifest"]
    a=author_arm["fields"]
    r=ref["config"]
    out={}
    def item(target,key,previous,current,expected="match"):
        identical=previous==current
        outcome=("match" if identical else "intentional difference" if expected=="different" else "unexpected difference")
        out.setdefault(target,{})[key]={"prior":previous,"direct":current,"comparison":outcome}
    def unknown(target,key,value,why):
        out.setdefault(target,{})[key]={"direct":value,"comparison":"unavailable historic measurement","basis":why}
    for role,old in (("author",a),("reviewer",r)):
        item(role,"pyvenv_cfg",old["C.pyvenv"],cfg["pyvenv_cfg"],"different")
        item(role,"include_system",old["C.include_system"],None,"different")
        item(role,"script",a["A.script"] if role=="author" else ref["script"],cfg["script"],"different")
        item(role,"orig_argv_suffix",a["A.args"] if role=="author" else ref["args"],cfg["orig_argv"][1:],"different")
        item(role,"orig_argv0_base_image",author_arm["orig_argv0"]=="@base/python.exe" if role=="author"
             else reviewer["image_roles"]["orig_argv0_is_base"],Path(cfg["orig_argv"][0])==BASE)
        item(role,"executable_is_venv",author_arm["executable"].startswith("@venv") if role=="author"
             else reviewer["image_roles"]["reported_executable_is_venv"],cfg["executable"]!=cfg["base_executable"],"different")
        item(role,"prefix",old["C.prefix"],cfg["prefix"],"different")
        item(role,"effective_pth",old["C.pth"],cfg["effective_pth"])
        item(role,"sitecustomize_present",bool(old["C.sitecustomize"]),cfg["sitecustomize"])
        for key in ENV_KEYS:
            if "C."+key in old:
                item(role,key,old["C."+key],cfg["env"][key])
            else:
                unknown(role,key,cfg["env"][key],"not in prior measured environment projection")
        modules=({k:normalize_module(v) for k,v in old["C.modules"]} if role=="author" else
                 {k:([p.replace("\\","/"),*h] if h else [p]) for k,p,*h in old["C.modules"]})
        for key in sorted(set(modules)|set(now)):
            new=now.get(key)
            if new is not None and len(new)==2:
                new=[new[0].replace("\\","/"),new[1]]
            if key in modules:
                item(role,"module."+key,modules[key],new,"different" if key=="__main__" or new is None else "match")
            elif role=="author":
                item(role,"module."+key,None,new,"different")
            else:
                unknown(role,"module."+key,new,"historical reviewer measured only ctypes, os, sys")
        for key in ("argv","cwd","flags","path","base_prefix","exec_prefix","base_exec_prefix","site_loaded",
                    "version","base_executable"):
            if key=="version" and role=="reviewer":
                item(role,key,ref["version"],cfg[key])
            else:
                unknown(role,key,cfg[key],"full field absent at historical public observation cut")
    return out
