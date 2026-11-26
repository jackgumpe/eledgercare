"""Read-only source audit. No package, model, tokenizer, or device is initialized."""
import argparse
import ast
import hashlib
from importlib.metadata import distributions
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.request import urlopen

BASE = "a0bf6122d082675d483ffd9aeb7f4dbedbfb174c"
PIN = "0480966938291445591f69f08a13b041c073a96a"
CHILD = "cb16b920ec2249c4b280f3aa67942e00b5099122"
HF = "https://huggingface.co/baidu/Unlimited-OCR-2"
HOME = Path("C:/Users/jackg/eLedgerCare-Q0/WP-0005")
MODEL = HOME / "models/Unlimited_OCR_2_04809669"
SITE = HOME / "venv/Lib/site-packages"
PDF = Path("C:/Users/jackg/Downloads/eLedgerCare-Layer-11-Coordinator-Review (1).pdf")
RECEIPT = ("qualification/q0/harness/evidence/004-gpu-trial/9e73ef86/"
           "run-20261115T202627Z-eb5bf7da/evidence/module-cache.json")


def git_json(path, rev=BASE):
    return json.loads(subprocess.check_output(["git", "show", f"{rev}:{path}"]))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify_files():
    manifest = git_json("qualification/q0/harness/manifests/model-files.json")
    assert manifest["revision"] == PIN
    checked = {}
    for entry in manifest["files"]:
        name = entry["path"]
        path = MODEL / name
        assert path.stat().st_size == entry["size"], name
        if entry["digest_kind"] == "lfs_sha256":
            # Sequential opaque bytes only; no deserialization or weight tensors.
            with path.open("rb") as handle:
                digest = hashlib.file_digest(handle, "sha256").hexdigest()
            assert digest == entry["sha256"], name
            checked[name] = {"sha256": digest, "bytes": entry["size"]}
        else:
            data = path.read_bytes()
            oid = hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()
            assert oid == entry["git_blob_sha1"], name
            checked[name] = {"git_blob": oid, "sha256": sha(data), "bytes": len(data)}
    assert len(checked) == manifest["runtime_object_count"] == 18
    receipt = git_json(RECEIPT)
    cache = Path(receipt["modules_cache"]) / "transformers_modules/Unlimited_OCR_2_04809669"
    historical = {}
    for entry in receipt["modules"]:
        name = entry["file"]
        cached_hash = sha((cache / name).read_bytes())
        assert cached_hash == checked[name]["sha256"] == entry["model_sha256"] == entry["cache_sha256"]
        assert entry["identical"]
        historical[name] = {"module": entry["module"], "sha256": cached_hash}
    return checked, historical


def versions():
    lock = git_json("qualification/q0/harness/locks/dependency-lock.json")
    src = lock["source"]
    pins = git_json(src["path"], src["commit"])["artifacts"]
    installed = {d.metadata["Name"].lower().replace("_", "-"): d.version for d in distributions(path=[str(SITE)])}
    verified = {}
    for row in pins:
        name = row["name"].lower()
        assert installed[name] == row["version"], name
        verified[name] = installed[name]
    assert len(verified) == 32
    assert not ({"triton", "triton-windows", "xformers", "flash-attn"} & installed.keys())
    tie_source = (SITE / "torch/_torch_docs.py").read_text(encoding="utf-8")
    tie_doc = tie_source.split("torch.argmax,", 1)[1].split('"""', 2)[1]
    assert "first maximal value" in tie_doc
    cache_source = (SITE / "transformers/cache_utils.py").read_text(encoding="utf-8")
    dynamic = cache_source.split("class DynamicCache(", 1)[1].split("\nclass ", 1)[0]
    assert "if layer_idx == 0:" in dynamic and "self._seen_tokens += key_states.shape[-2]" in dynamic
    assert "self.key_cache[layer_idx] = torch.cat(" in dynamic
    assert "self.value_cache[layer_idx] = torch.cat(" in dynamic
    installed_blobs = {p: sha((SITE / p).read_bytes()) for p in
                       ("transformers/cache_utils.py", "torch/_torch_docs.py", "torch/version.py")}
    return {"verified_pinned_distributions": verified, "installed_extra_names": sorted(installed.keys() - verified.keys()),
            "triton_distribution_present": False, "runtime_source_sha256": installed_blobs,
            "scope": "Metadata and installed source only; no current instrumented runtime or dispatch."}


def signatures():
    refs = {
        "_sparse_base_impl.py": {"DeepseekV2RMSNorm.forward", "DeepseekV2DecoderLayer.__init__",
                                "DeepseekV2DecoderLayer.forward", "DeepseekV2Model.__init__",
                                "DeepseekV2Model.forward", "SlidingWindowLlamaAttention._main_rope_coords"},
        "modeling_deepseekv2.py": {"_patched_forward", "_dash_attn_forward", "_dash_decode_forward",
                                  "_infer_prefill_attend", "_router_qk", "_block_scores_infer",
                                  "_infer_route_select", "configure_dash_inference", "_decode_attend"},
        "modeling_unlimitedocr.py": {"_uocr_dash_decode_allow", "_uocr_no_repeat_ngram", "_uocr_page_count_guard",
                                    "UnlimitedOCRModel.forward", "UnlimitedOCRForCausalLM.__init__",
                                    "UnlimitedOCRForCausalLM.infer", "UnlimitedOCRForCausalLM.infer_multi",
                                    "UnlimitedOCRForCausalLM._uocr_generate"}
    }
    result = {}
    for name, targets in refs.items():
        tree = ast.parse((MODEL / name).read_text(encoding="utf-8"))
        nodes = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                nodes.update({f"{node.name}.{n.name}": n for n in node.body if isinstance(n, ast.FunctionDef)})
        result[name] = {k: {"lines": [nodes[k].lineno, nodes[k].end_lineno],
                            "args": ast.unparse(nodes[k].args)} for k in sorted(targets)}
    return result


def configuration():
    def read(name):
        return json.loads((MODEL / name).read_bytes())
    config = read("config.json")
    assert config["num_hidden_layers"] == config["language_config"]["num_hidden_layers"] == 12
    assert (config["hidden_size"], config["vocab_size"], config["tie_word_embeddings"]) == (1280, 129280, False)
    state_map = read("model.safetensors.index.json")["weight_map"]
    numbered = {int(m.group(1)) for k in state_map if (m := re.match(r"model\.layers\.(\d+)\.", k))}
    assert numbered == set(range(12))
    weights = ["model.norm.weight", "lm_head.weight", "model.embed_tokens.weight",
               "model.layers.11.self_attn.k_proj.weight", "model.layers.11.self_attn.v_proj.weight"]
    assert set(weights) <= state_map.keys()
    sparse = config["sparse_attention_config"]
    assert sparse["sparse_block_size"] == 32 and sparse["sparse_attention_freq"] == [1] * 12
    tokenizer = read("tokenizer.json")
    token_config = read("tokenizer_config.json")
    tokens = {r["id"]: r["content"] for r in tokenizer["added_tokens"]}
    assert tokens[128815] == "<image>" and tokens[128827] == "<PAGE>"
    assert token_config["tokenizer_class"] == "LlamaTokenizerFast"
    assert read("special_tokens_map.json")["eos_token"]["content"] == tokens[1]
    call = git_json("qualification/q0/harness/protocol.json")["call"]
    return {"language_layers": sorted(numbered), "hidden_width": config["hidden_size"],
            "final_rms_eps": config["rms_norm_eps"], "vocabulary_logits": config["vocab_size"],
            "checkpoint_dtype": config["torch_dtype"], "tie_word_embeddings": config["tie_word_embeddings"],
            "index_entries": {k: state_map[k] for k in weights}, "sparse_config": sparse,
            "generation_config": read("generation_config.json"),
            "tokenizer": {"class": token_config["tokenizer_class"], "decoder": tokenizer["decoder"]["type"],
                          "model": tokenizer["model"]["type"], "base_vocab_size": len(tokenizer["model"]["vocab"]),
                          "added_entries": len(tokens), "cleanup_spaces": token_config["clean_up_tokenization_spaces"],
                          "example_pinned_ids": {i: tokens[i] for i in (0, 1, 2, 128815, 128827)}},
            "historical_q0_call": {k: call[k] for k in ("signature_used", "prompt", "fixed_kwargs", "rules")}}


def online():
    commit_url = f"{HF}/commit/{CHILD}"
    def fetch(url):
        with urlopen(url, timeout=25) as response:
            return response.read()
    page = fetch(commit_url).decode()
    parent = re.search(r'(\d+)\s*Parent\(s\):</span>.*?href="/baidu/Unlimited-OCR-2/commit/([0-9a-f]{40})"', page, re.S)
    assert parent and parent.groups() == ("1", PIN)
    diff = fetch(commit_url + ".diff")
    change = re.findall(r"^diff --git a/(\S+) b/(\S+)$", diff.decode(), re.M)
    assert change == [("README.md", "README.md")]
    older, newer = [], []
    for rev, inventory in ((PIN, older), (CHILD, newer)):
        url = f"https://huggingface.co/api/models/baidu/Unlimited-OCR-2/tree/{rev}?recursive=true"
        with urlopen(url, timeout=25) as response:
            assert 'rel="next"' not in response.headers.get("Link", "")
            inventory.extend((r["path"], r["oid"]) for r in json.load(response) if r["type"] == "file")
    a, b = dict(older), dict(newer)
    changed = sorted(k for k in a.keys() | b.keys() if a.get(k) != b.get(k))
    assert changed == ["README.md"]
    remote = subprocess.check_output(["git", "ls-remote", HF + ".git", "refs/heads/main"], text=True).strip()
    return {"parent": PIN, "child": CHILD, "parent_count": 1, "commit_url": commit_url,
            "observed_main": remote.split()[0], "files_in_parent": len(a), "files_in_child": len(b),
            "changed_file_oids": {"README.md": [a["README.md"], b["README.md"]]},
            "diff_sha256": sha(diff), "changed_files": changed}


if __name__ == "__main__":
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument("--online", action="store_true", help="Read public revision metadata and README-only diff.")
    args.add_argument("--out", type=Path, required=True)
    flags = args.parse_args()
    py = sha(Path(sys.executable).read_bytes())
    assert py == "4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a"
    pdf = PDF.read_bytes()
    assert len(pdf) == 215820 and sha(pdf) == "3f4451dd3a1bd2dc37d50c5ddb720dfd37005f62c1da68a6b2958aa86db14264"
    files, cache = verify_files()
    result = {"base": BASE, "model": PIN, "input_pdf_sha256": sha(pdf), "python_sha256": py, "python": sys.version,
              "files": files, "historical_q0_imported_module_receipt_and_disk": cache, "versions": versions(),
              "configuration": configuration(), "source_signatures": signatures()}
    if flags.online:
        result["hf_revision"] = online()
    flags.out.write_text(json.dumps(result, indent=2, ensure_ascii=True) + "\n", encoding="utf-8", newline="\n")
    print(f"Verified {len(files)} pinned files and {len(cache)} historical module copies; wrote {flags.out.name}.")
