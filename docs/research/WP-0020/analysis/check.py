"""Pre-score controls for critical token vs whole-line scoring, field association, empty values and clocks."""
from copy import deepcopy
from replay import ASTRA, evaluate, label_predicate, measured_cost, read, require, score

label = label_predicate()
require(label("Serial") and not label("serially") and label("inspection"), "frozen predicate")
sha = "0" * 64
ref = dict(page=1, width=100, height=100, text="Serial 10 A\nCode Note\nXB \n",
           lines=[dict(text="Serial 10 A", critical="10", bbox=[0, 1, 50, 10])],
           tables=[dict(bbox=[0, 20, 100, 80], rows=[
               [dict(text="Code", critical=False, bbox=[0, 20, 50, 50]), dict(text="Note", critical=False, bbox=[50,20,100,50])],
               [dict(text="XB", critical=True, bbox=[0,50,50,80]), dict(text="", critical=False, bbox=[50,50,100,80])]])])
truth = dict(family="dev", source_sha256=sha, pages=[ref])
source = dict(source_sha256=sha, pages=[dict(page=1, source_sha256=sha, state="complete", text=ref["text"],
              spans=[dict(text="Serial", bbox=[0,1,18,10]), dict(text="10", bbox=[20,1,28,10]),
                     dict(text="A", bbox=[32,1,40,10]), dict(text="missing label", bbox=[0,90,10,94])],
              tables=[dict(bbox=[0,20,100,80], rows=[["Code","Note"], ["X8",""]])])])
routed = deepcopy(source)
routed["pages"][0]["tables"][0]["rows"][1][0] = "XB"
routed["pages"][0]["spans"][0]["text"] = "SeriaI"
native = deepcopy(routed)
native["pages"][0]["tables"][0]["rows"][1].pop()
native["pages"][0]["spans"][1]["text"] = "1O"
fields = [
    dict(kind="cell", id="c", page=1, window_start=1, span_indices=[], table_index=0, row_index=1, col_index=0,
         windows_value="X8", label_text="Code"),
    dict(kind="prose", id="l", page=1, window_start=1, span_indices=[0,1,2],
         windows_value="Serial 10 A", label_text="Serial"),
    dict(kind="prose", id="empty", page=1, window_start=1, span_indices=[3],
         windows_value="missing label", label_text="label")]
decisions = [
    dict(id="c", page=1, status="substituted", reason="bound", emitted_value="XB", native_value="XB", changed=True),
    dict(id="l", page=1, status="substituted", reason="bound", emitted_value="SeriaI 10 A", native_value="SeriaI 10 A", changed=True),
    dict(id="empty", page=1, status="unresolved", reason="no native line", emitted_value="missing label", native_value=None, changed=False)]
metrics, rows = evaluate(truth, source, {"fields": fields}, {"fields": decisions},
                         {k: score(truth,p) for k,p in dict(windows=source,native=native,routed=routed).items()}, label)
crit = metrics["metrics"]["critical"]
require(crit["windows_to_routed"] == dict(right_to_right=1, wrong_to_right=1, right_to_wrong=0, wrong_to_wrong=0), "transitions")
require(crit["native_risks"] == 1 and crit["opportunities"] == {"recovered":1}, "opportunities and risk")
require(metrics["selection"]["unmatched"] == 1 and metrics["protected_damaged"] == ["page/1/line/1"], "unmatched/spacing")
blank, = [r for r in rows["regions"] if r["printed_blank"]]
require(blank["native_risk"] and blank["missing"]["native"] and blank["routed"], "absent vs printed blank")

dev = ASTRA/"evidence/dev-ab-01"
native_dir = dev/"07-boundary-native"
native_time, win_time = (read(folder/"timing.json") for folder in (native_dir, dev/"08-boundary-windows"))
windows = {i:read(native_dir/f"window-{i:03d}.json") for i in (1,4)}
cost = measured_cost(win_time, native_time, windows, [dict(page=1,window_start=1), dict(page=3,window_start=1)])
require((cost["selected_windows"],cost["routed_pages"],cost["purchased_pages"]) == (1,2,3), "deduplicated windows")
require(cost["modeled_serial_engine_floor_s"] < cost["modeled_serial_segment_s"] and cost["verdict"]=="over budget", "matched lower bound")
cost = measured_cost(win_time, native_time, windows, [dict(page=4,window_start=4)])
require(cost["windows_with_one_field"] == [4] and cost["purchased_pages"] == 1, "partial last window")
print("PASS label predicate, marker join, token/line distinction, unmatched selector, missing vs printed blank, native opportunity/risk, matched window accounting.")
