"""Cross-check a published engine candidate's A1 probe geometry against the frozen reviewer anchors (CPU only).

eld-rd-reviewer, continuation session (common.OPERATOR). Loads the candidate's span_probe.py from its exact Git
blob (digest verified against the author's published handoff), never from a working tree, and runs only its
pure locator functions with the pinned tokenizer.json (Q0 `tokenizers`). No torch, CUDA, model, output or key.

For each window it records the engine's frozen locator (native prefix end, shared pre-divergence tokens, both
branch spans) and the free-field extraction on both frozen histories, and checks what a1_normalize.map_probe
assumes: prefix P plus the shared tokens equals the audited boundary (019: 417, 037: 41) with the audited
prefix digest, the common-boundary branch ids equal the audited spans, and the same locator reads the native
and Carbon identifiers on their own histories with the expected branch roles.
"""
import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import a1_decide as A1  # noqa: E402
from common import DISK, REPO, Check, disk, ids_sha, load, sha, sha_file, utc, write_new  # noqa: E402

BOUNDARY = {"019": 417, "037": 41}


def candidate_module(commit, rel, want, scratch):
    data = subprocess.run(["git", "-C", str(REPO), "cat-file", "blob", f"{commit}:{rel}"], check=True,
                          capture_output=True).stdout
    if sha(data) != want:
        raise SystemExit(f"{commit}:{rel} has {sha(data)}, expected {want}")
    scratch.mkdir(parents=True, exist_ok=False)
    path = scratch / Path(rel).name
    path.write_bytes(data)
    spec = importlib.util.spec_from_file_location("candidate_span_probe", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--commit", required=True)
    ap.add_argument("--span-probe-sha256", required=True, help="from the author's published handoff")
    ap.add_argument("--audit", type=Path, required=True)
    ap.add_argument("--audit-sha256", required=True)
    ap.add_argument("--scratch", type=Path, required=True, help="new directory")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    check = Check()
    check(sha_file(a.audit) == a.audit_sha256, "audit digest")
    audit = load(a.audit)
    import tokenizers  # noqa: PLC0415  (Q0 venv; pinned tokenizer.json bytes verified by disk())
    disk("tokenizer.json")
    tok = tokenizers.Tokenizer.from_file(str(DISK["tokenizer.json"][0]))
    sp = candidate_module(a.commit, "docs/research/WP-0017/engine/span_probe.py", a.span_probe_sha256, a.scratch)
    from common import A1_MANIFEST  # noqa: PLC0415
    check(sha_file(A1_MANIFEST[0]) == A1_MANIFEST[1], "A1 manifest digest")
    man = load(A1_MANIFEST[0])
    vocab = A1.Vocab(disk("tokenizer.json"))
    out = {}
    for win in man["windows"]:
        w = f"{win['first_page']:03d}"
        nat, car = win["by_mode"]["native"]["token_ids"], win["by_mode"]["carbon_bf16"]["token_ids"]
        loc = sp.build_frozen_field_locator(first_page=win["first_page"], identifier_page=win["identifier_page"],
                                            alternatives=win["alternatives"], native_token_ids=nat,
                                            carbon_token_ids=car, tokenizer=tok)
        cs = loc["competing_spans"]
        lcp = cs["lcp_offset_from_pre_space"]
        P = len(loc["native_prefix_tokens"])
        ent = {e["role"]: e for e in cs["entries"]}
        pref = audit["windows"][A1.AUDIT_KEY[w]]["a1_prefixes"]["native_prefix_to_boundary"]
        spans = {m: [t["id"] for t in audit["windows"][A1.AUDIT_KEY[w]]["divergence"]["span_to_identifier_end"][m]]
                 for m in ("native", "carbon_bf16")}
        check(loc["native_prefix_tokens"] == nat[:P], f"{w}: engine native prefix is a prefix of the frozen history")
        check(P + lcp == BOUNDARY[w] == pref["tokens"] and ids_sha(nat[:P + lcp]) == pref["sha256"],
              f"{w}: engine P {P} + shared {lcp} = audited boundary {pref['tokens']} with the audited digest")
        check(ent["native_id"]["pre_space_token_ids"][:lcp] == ent["carbon_id"]["pre_space_token_ids"][:lcp]
              == nat[P:P + lcp], f"{w}: shared pre-divergence tokens continue the frozen history")
        check(ent["native_id"]["common_boundary_token_ids"] == spans["native"] and
              ent["carbon_id"]["common_boundary_token_ids"] == spans["carbon_bf16"],
              f"{w}: engine common-boundary branch ids = audited spans")
        fields = {}
        for m, hist in (("native", nat), ("carbon_bf16", car)):
            f = sp.extract_free_field_at_locator(hist, tok, loc, native_window_token_ids=nat)
            fp = f.get("free_prefix_tokens") or []
            fields[m] = dict(aligned=f.get("aligned"), observed_id=f.get("observed_id"),
                             role=f.get("matched_probed_branch_role"), free_prefix_len=len(fp),
                             prefix_identical_to_native=f.get("prefix_identical_to_native"))
            want_id = win["alternatives"][0 if m == "native" else 1]
            check(f.get("aligned") is True and f.get("observed_id") == want_id and
                  f.get("matched_probed_branch_role") == ("native_id" if m == "native" else "carbon_id"),
                  f"{w}/{m}: engine locator reads {want_id} with the expected branch role")
            line = audit["windows"][A1.AUDIT_KEY[w]]["divergence"]["common_line_prefix"]
            b = A1.free_boundary(vocab, hist, A1.freeze_locator(vocab, nat, w),
                                 len(b"".join(vocab.piece(t["id"]) for t in line)))
            check(len(fp) + lcp == b, f"{w}/{m}: engine free prefix {len(fp)} + shared {lcp} = reviewer structural boundary {b}")
        out[w] = dict(engine_prefix_tokens=P, shared_pre_divergence_tokens=nat[P:P + lcp], lcp=lcp,
                      native_prefix_sha256_engine_P=ids_sha(nat[:P]), normalized_prefix_tokens=P + lcp,
                      normalized_prefix_sha256=ids_sha(nat[:P + lcp]),
                      branches={r: dict(pre_space=e["pre_space_token_ids"], common_boundary=e["common_boundary_token_ids"])
                                for r, e in ent.items()},
                      free_fields=fields, early_pre_id_divergence=loc.get("early_pre_id_divergence"))
    rec = dict(kind="WP-0017 reviewer cross-check of a published engine's A1 probe geometry (CPU, no model)",
               reviewer="eld-rd-reviewer", created_utc=utc(), candidate=a.commit,
               span_probe_sha256=a.span_probe_sha256, audit_sha256=a.audit_sha256, manifest_sha256=A1_MANIFEST[1],
               tokenizers_version=tokenizers.__version__, windows=out, checks_run=check.count, failures=check.failures)
    digest = write_new(a.out, rec)
    print(json.dumps(dict(out=str(a.out), sha256=digest, checks=check.count, failures=check.failures), indent=1))
    return 0 if not check.failures else 1


if __name__ == "__main__":
    sys.exit(main())
