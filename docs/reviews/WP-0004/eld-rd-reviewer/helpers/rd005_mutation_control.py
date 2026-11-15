#!/usr/bin/env python3
"""Negative-control mutation check for rd005_verify.py (reviewer-authored, scratch-only).

Copies an exported candidate into a scratch directory, plants two independent defects, reruns
rd005_verify.py and asserts that both are reported. Proves the binding checks are not vacuous.
  M1: F05 source L04 discount_rate 0.1500 -> 0.1400 (source no longer matches expected/visible PDF)
  M2: F06 v0 expected amount_due printed_text $900.68 -> $900.69 (expected no longer matches own math)
"""
import json, pathlib, shutil, subprocess, sys

src, work, lstree, wheels = map(pathlib.Path, sys.argv[1:5])
if work.exists():
    shutil.rmtree(work)
shutil.copytree(src, work)
p = work / "evaluation/synthetic/sources/F05_SYN-INV-02_source.json"
t = p.read_text(encoding="utf-8")
assert t.count('"discount_rate": "0.1500"') == 1
p.write_text(t.replace('"discount_rate": "0.1500"', '"discount_rate": "0.1400"'), encoding="utf-8", newline="\n")
q = work / "evaluation/synthetic/expected/SYN-INV-03-v0-clean_expected.json"
e = json.loads(q.read_text(encoding="utf-8"))
for f in e["expected_fields"]:
    if f["field_id"] == "amount_due":
        f["printed_text"] = "$900.69"
q.write_text(json.dumps(e, indent=2) + "\n", encoding="utf-8", newline="\n")
out = work.parent / (work.name + "_ev")
r = subprocess.run([sys.executable, str(pathlib.Path(__file__).with_name("rd005_verify.py")), "--repo", str(work), "--lstree", str(lstree),
                    "--wheels", str(wheels), "--out", str(out)], capture_output=True, text=True)
s = json.loads((out / "verify-summary.json").read_text(encoding="utf-8"))
msgs = [f["message"] for f in s["findings"]]
m1 = [m for m in msgs if "F05" in m or "SYN-INV-02" in m]
m2 = [m for m in msgs if "SYN-INV-03-v0-clean field amount_due" in m]
res = {"M1_detected": bool(m1), "M1_sample": m1[:4], "M1_count": len(m1), "M2_detected": bool(m2), "M2_sample": m2[:2], "total_findings": len(msgs)}
print(json.dumps(res, indent=1))
sys.exit(0 if res["M1_detected"] and res["M2_detected"] else 1)
