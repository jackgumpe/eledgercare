"""Reconcile the independent results, re-executions of reviewed tools and coordinator gate."""
import hashlib
import json
from pathlib import Path
import subprocess

DIR = Path(__file__).resolve().parent
SCRATCH = Path.home() / "eLedgerCare-Speed/WP-0041/review"
GATE = "5437406595e8cdf055803772fbd1a25809daa180"
AUTH = "da275f4f036c2f6fb1af28a231157ada70fc1430"
CUST = "2950a7e0b9a71bf43a00ff37ceb67af97da62de9"
AGREEMENT = "b249b1becfb7be801016f1c835bd5de7470b83b6"


def blob(rev, path):
    return subprocess.check_output(["git", "show", f"{rev}:{path}"])


def checked_output(revision, path, repeat, crlf=False):
    wanted = blob(revision, path)
    got = (SCRATCH/repeat).read_bytes()
    assert json.loads(got) == json.loads(wanted)
    assert (got.replace(b"\r\n",b"\n") if crlf else got) == wanted
    return hashlib.sha256(wanted).hexdigest()


if __name__ == "__main__":
    review = json.loads((DIR/"archive-results.json").read_bytes())
    math = json.loads((DIR/"mathematical-results.json").read_bytes())
    gate = json.loads(blob(GATE, "docs/coordination/WP-0041/replay-gate.json"))
    custody = json.loads(blob(CUST, "docs/custody/WP-0041/field.json"))
    a_math = json.loads(blob(AUTH, "docs/research/WP-0041/math.json"))
    a_source = json.loads(blob(AUTH, "docs/research/WP-0041/source.json"))
    hashes = {"custody": checked_output(CUST,"docs/custody/WP-0041/field.json","custody-rerun.json", True),
              "author_math": checked_output(AUTH,"docs/research/WP-0041/math.json","author-math.json"),
              "author_source": checked_output(AUTH,"docs/research/WP-0041/source.json","author-source.json")}
    field, archive, ids = gate["field"], review["archive"], review["cell"]["native_tokens_i_id_start_end_piece"]
    assert [field[k] for k in ("page","table","row","column","literal","signed_minor_units")] == [
        custody["field"][k] for k in ("page","table","row","column","literal","minor")]
    assert (field["family"],field["run"],field["observation"]) == ("F07","20261115T202627Z-eb5bf7da",custody["selected_capture_id"])
    assert field["opening_id"] == ids[0][1]
    assert [field[k] for k in ("open_bytes","amount_bytes","close_bytes")] == review["cell"]["raw_ranges_open_value_close"]
    assert [field[k] for k in ("prompt_length","generated_length","decoded_bytes")] == [
        archive["prompt_len"],archive["native_ids"],archive["raw_bytes"]]
    assert field["source_cell_pdf_points_bottom_left"] == review["pdf"]["pdf_cell_left_bottom_right_top"]
    assert field["text_origin_pdf_points"] == custody["geometry"]["printed_baseline_xy_pt"]
    assert custody["geometry"]["native_render_page1"] == review["pdf"]["actual_Q0_render"]
    for (i,tid,_,_,piece), g, c in zip(ids[1:],field["comparison_positions"],custody["prediction_alignment"],strict=True):
        assert (i,tid,i-1,i-1+archive["prompt_len"],piece) == tuple(g[k] for k in
            ("predict","id","consume","absolute_input_position","piece"))
        assert (i,tid,i-1,i-1+archive["prompt_len"]) == tuple(c[k] for k in
            ("emit_index","emit_id","consume_index","absolute_input_position"))
    h, k, s = gate["historical_run"], archive["kernel_path"], archive["aggregate_cache"]
    assert [h[n] for n in ("prefill_tokens","decode_steps","final_cache_length")] == [
        s["prefill_seq_len"],s["decode_steps_observed"],s["final_seq_len"]]
    assert [h[n] for n in ("all_layer_dash_decode_calls","fp32_decode_attend_calls","prefill_dense_fallback_calls",
                            "non_dash_attention_calls")] == [k[n] for n in
                            ("decode_forward_calls","decode_attend_fp32_calls","dense_sdpa_calls","non_dash_attention_calls")]
    assert h["per_position_route_topk_available"] is False
    known = {"development_fields_with_verified_context_and_geometry":1,"requested_comparison_positions":5}
    unknown = ("archive_parity_result","original_document_branch_nonmutation_verified_by_live_comparison","paired_delta","latency_effect")
    for key, value in gate["gate"].items():
        if key in unknown:
            assert value is None
        else:
            assert value == known.get(key,0)
    assert a_math["paired"]["all_nine_contributions"] == math["trial"]["nine_transitions"]
    assert a_math["paired"]["delta"] == math["trial"]["N10_R3_G1_delta"]
    assert a_math["paired"]["one_sided_null_tail"] == math["trial"]["illustrative_sign_p"]
    assert a_math["ledger"]["distance"] == math["trial"]["C9b_distances"]
    assert list(a_math["costs"]["loop_minus_crop_ms_per_page"].values()) == math["cost"]["a2_b3_c11_at_p_.10_.25_.50"]
    assert [a_math["scores"]["worked_lead_delta_relative_new_rival_lead"][i] for i in (0,3,4)] == [
        math["margin"][i] for i in ("initial_lead","relative_gain","final_overtake")]
    assert a_math["toy_state"]["private_lengths"] == [32]*3 and math["cache"]["private_lengths"] == [32]*2
    for name,sha in review["verified_local_source_blobs"].items():
        assert sha == a_source["files"][name]["sha256"]
    assert math["text"]["agents_revision"] == AGREEMENT
    oid = subprocess.check_output(["git", "rev-parse", AGREEMENT+":AGENTS.md"], text=True).strip()
    assert oid == "05e96c7f9992c0cb218c4d1b37a30394d4a543dd"
    print(json.dumps({"outcome":"accepted bounded source, field and stop; unmeasured native parity",
                      "reexecuted_result_sha256_lf":hashes,"complete_custody_evidence_pins":len(custody["source_blobs"]),
                      "gate":GATE,"agreement":AGREEMENT,"agreement_blob":oid,"field_prediction_count":len(ids)-1,
                      "public_comparison":a_source["hf_revision"]},indent=2))
