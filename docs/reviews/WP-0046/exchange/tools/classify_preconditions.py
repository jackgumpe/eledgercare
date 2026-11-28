"""Post-hoc descriptive classification of the peer register's missing_precondition texts.
Written AFTER reading the data (not a frozen test). Keyword rule: a precondition that asks
to fix, add, update, extend, implement, freeze, decide, agree, inspect or bind separately is
'binding_or_decision_pending'; any other non-empty precondition is 'observation_or_release_pending'.
Usage: python -I classify_preconditions.py PEER_REGISTER
"""
import json
import re
import sys
from collections import Counter

K = re.compile(r"Fix |agreement|Freeze|Decision|implement|Extend|Add |Update|must inspect|bound separately|Complete Stage-3|reviewed", re.I)
E = json.load(open(sys.argv[1], encoding="utf-8"))["entries"]
c, keys = Counter(), {}
for e in E:
    pre = e["missing_precondition"] or []
    dec = [p for p in pre if K.search(p)]
    cls = "binding_or_decision_pending" if dec else "observation_or_release_pending" if pre else "none"
    c["%s@%d" % (cls, e["direct_stock_stage"])] += 1
    if dec:
        keys.setdefault(cls, []).append(e["key"])
print(json.dumps({"counts": dict(sorted(c.items())), "binding_or_decision_pending_keys": keys.get("binding_or_decision_pending", [])}, indent=1))
