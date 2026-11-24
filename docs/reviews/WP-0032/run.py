"""Run exactly four M1 populated and two M3 zero-memory reads on frozen development inputs."""
import dataclasses
import datetime as dt
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import traceback

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BASE = "537ab866bb5803328d378bc00f11f5782bb5ef00"
DATA = "8f31cc66c4878ca086fa5da1498c4a73ed6a6306"
REVIEW = "6ee777088c7d6121611091556246bb964c5a4227"
CLOSE = "8962868f6476ce26b4c108daa960a13265db10cc"
SOURCE = "7db67283a4ffd3e7a20bb8d80499572cc7118c71"
FIT = "6d79c24364ba10a1d9bfa4c72c837e2f216cf4bc"
PREVIOUS = "5e1a464a38ad4213b94b3b25695bd70d9054a6a3"
PYTHON = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0030/runtime/venv/Scripts/python.exe")
SCRATCH = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0032/review")
PYHASH = "0b471133e110cfb53a061cad528ce8e517d7b9ac41a0a396c39ad795a487fc14"
EVIDENCE = "docs/research/WP-0031/evidence/"
INPUTS = {}
NAMES = ["Alder", "Cedar"]
TAGS = {"M1": ("AA", "AC", "CA", "CC"), "M3": ("0A", "0C")}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(*cmd):
    return subprocess.check_output(["git", *cmd], cwd=ROOT)


def blob(rev, path, expected=None):
    ref = f"{rev}:{path}"
    data = git("cat-file", "blob", ref)
    INPUTS[ref] = sha(data)
    assert expected is None or sha(data) == expected, ref
    return data


def canonical_hash(x):
    return sha((json.dumps(x, sort_keys=True, ensure_ascii=False, separators=(",", ":"))+"\n").encode())


def write_json(path, value):
    path.write_bytes((json.dumps(value, indent=2, allow_nan=False)+"\n").encode())


def bits(t):
    assert t.dtype == torch.float32 and t.device.type == "cpu"
    return t.contiguous().numpy().tobytes()


def tensor(raw, shape):
    t = torch.frombuffer(bytearray(raw), dtype=torch.float32).reshape(shape)
    assert t.isfinite().all() and bits(t) == raw
    return t


def bind_work(candidate):
    assert not sys.flags.optimize and sys.flags.isolated and sys.flags.dont_write_bytecode
    assert Path.cwd().resolve() == ROOT and ROOT.name == "w032-review"
    assert git("branch","--show-current").decode().strip() == "review/wp-0032-accounting"
    assert git("rev-parse","HEAD").decode().strip() == candidate
    assert git("merge-base",candidate,BASE).decode().strip() == BASE
    assert git("status","--porcelain") == b""
    assert Path(sys.executable).resolve() == PYTHON.resolve() and sha(PYTHON.read_bytes()) == PYHASH
    assert sys.byteorder == "little" and platform.python_version() == "3.12.10"
    for name in ("run.py","account.py"):
        path = HERE / name
        assert path.read_bytes().replace(b"\r\n",b"\n") == blob(candidate,path.relative_to(ROOT).as_posix())
    work = SCRATCH / candidate
    work.mkdir(parents=True, exist_ok=False)
    for key in ("TEMP","TMP","TORCH_HOME","HF_HOME","TORCHINDUCTOR_CACHE_DIR","XDG_CACHE_HOME"):
        dst = work / key
        dst.mkdir()
        os.environ[key] = str(dst)
    os.environ.update(CUDA_VISIBLE_DEVICES="-1",OMP_NUM_THREADS="1",MKL_NUM_THREADS="1",
                      OPENBLAS_NUM_THREADS="1",HF_HUB_OFFLINE="1",PIP_NO_INDEX="1")
    return work


def frozen_state(document, name, shape, empty, independent, manifest):
    item = document["sources"][name]["snapshot"]
    assert item["shape"] == shape and item["dtype"] == "float32-le"
    assert item["matrices_file"] in manifest
    raw = blob(DATA,EVIDENCE+item["matrices_file"],manifest[item["matrices_file"]])
    assert sha(raw) == item["matrix_sha256"] == independent["write7"][name]["matrix_sha256"]
    mat = tensor(raw,shape)
    if empty:
        mat = torch.zeros_like(mat)
        assert mat.shape[0] == 8 and bits(mat) == bytes(len(raw))
    discrete = item["discrete"]
    assert canonical_hash(discrete) == item["discrete_sha256"]
    assert discrete == document["sources"]["Cedar"]["snapshot"]["discrete"]
    assert discrete["registry"] == independent["write7"][name]["full_registry"]
    ctrl = online.Controller(**discrete["controller"])
    reg = online.Registry(owners=set(discrete["registry"]["owners"]),units=set(discrete["registry"]["units"]),
                          schemas=set(map(tuple,discrete["registry"]["schemas"])))
    assert ctrl.depth == 0 and ctrl.ambiguous() == "" and list(reg.choices()["owner"]) == NAMES
    return mat, discrete, ctrl, reg


def run_cell(arm, tag, document, independent, closure, manifest, model):
    empty = arm == "M3"
    shape = [8 if empty else 1, 128, 128]
    owner = "Cedar" if tag[0] == "C" else "Alder"
    name = "Cedar" if tag[1] == "C" else "Alder"
    old, discrete, ctrl, reg = frozen_state(document,owner,shape,empty,independent,manifest)
    archive = document["empty_cells" if empty else "cells"][tag]
    assert archive["control_registry_from"] == owner and archive["donor"] == name
    assert archive["recipient"] == ("zero" if empty else owner)
    independent_cell = independent["cells"][tag]
    prev = archive["read"]
    alt = independent_cell["post"]
    assert archive["recipient_before_event"]["matrix_sha256"] == sha(bits(old)) == independent_cell["recipient_matrix_sha256"]
    assert archive["recipient_before_event"]["discrete_sha256"] == canonical_hash(discrete)
    assert archive["recipient_before_event"] == archive["after_donor_hook"]

    source = document["sources"][name]
    donor = source["donor"]
    assert source["donor_input_sha256"] == canonical_hash(donor) == archive["donor_input_sha256"]
    assert donor["pointer"] == [1,1,7] and donor["literal"] == "Ledger: "+name
    assert donor["owner"] == name and donor["full_window_shape"] == [16,1280]
    assert donor["feature_sha256"] == independent["donor"][name]["feature_sha256"]
    event, = donor["events"]
    assert event["kind"] == "OPEN_LEDGER" and event["ptr"] == [1,1,7] and event["value"] == name
    assert event["literal"] == independent_cell["event_literal"] == donor["literal"]
    ctrl.apply(online.Event(**event))
    reg.update(online.Event(**event))
    assert dataclasses.asdict(ctrl) == discrete["controller"]
    choices = {k:list(v) for k,v in reg.choices().items()}
    assert choices == prev["registry"] == alt["registry"] and ctrl.depth == 0
    assert canonical_hash(discrete) == prev["discrete_sha256"]
    assert prev["owner_eligible"] and prev["native_scope_clear"]
    projected = [bytes.fromhex(donor["projected_f32le"][s]) for s in ("key","value","alpha","beta")]
    independent_donor = independent["donor"][name]
    assert [v.hex() for v in projected] == [independent_donor["fields_f32le"][s] for s in ("k","v","a","b")]
    assert sha(b"".join(projected)) == donor["projection_sha256"] == independent_cell["donor_k_v_a_b_sha256"]
    k,v,a,b = (tensor(raw,dims) for raw,dims in zip(projected,[(128,),(128,),(),()],strict=True))
    src = document["sources"][owner]
    for field in ("frozen_query_f32le","ordered_anchors_f32le"):
        assert document["sources"]["Alder"][field] == document["sources"]["Cedar"][field]
    query = tensor(bytes.fromhex(src["frozen_query_f32le"]),(128,))
    anchors = tensor(bytes.fromhex(src["ordered_anchors_f32le"]),(2,128))
    assert sha(bits(query)) == prev["query_sha256"] == alt["query_sha256"]
    assert sha(bits(anchors)) == prev["ordered_anchor_sha256"] == alt["anchor_sha256"]
    assert bits(anchors) == bits(model.anchors("owner",NAMES))

    updated = model.write(tuple(old.unbind(0)),ctrl.depth,k,v,a,b)
    read = model.read(updated,ctrl.depth,query,"owner")
    logits = anchors @ matrix.direction(read)
    matrix_hash = sha(bits(torch.stack(updated)))
    assert matrix_hash == prev["matrix_sha256"] == alt["matrix_sha256"]
    assert bits(read).hex() == prev["read_f32le"] == alt["read_f32le"]
    assert sha(bits(read)) == prev["read_sha256"] == alt["read_sha256"]
    scores8 = bits(logits)
    assert len(scores8) == 8 and scores8.hex() == prev["score_f32le"] == alt["score_f32le"] == closure["score_f32le"]
    scores = dict(zip(NAMES,logits.tolist(),strict=True))
    margin = scores["Alder"] - scores["Cedar"]
    assert scores == closure["scores"] == prev["scores"] == alt["scores"]
    assert margin == closure["margin"] == prev["margin"] == alt["margin"]
    native = dict(norm=read.norm().item(),denominator=(read.norm()+matrix.EPS).item(),
                  numerator=torch.dot(anchors[0]-anchors[1],read).item(), scores=scores,
                  margin=margin,read=read.tolist())
    row = account.one_cell(arm,tag,old[0].tolist(),k.tolist(),v.tolist(),a.item(),b.item(),query.tolist(),
                           anchors.tolist(),native)
    row["binding"] = dict(recipient=owner if not empty else "zero",donor=name,control_from=owner,
                          shape=shape,query_sha256=sha(bits(query)),anchor_sha256=sha(bits(anchors)),
                          recipient_sha256=sha(bits(old)),donor_bundle_sha256=canonical_hash(donor),
                          donor_projection_sha256=sha(b"".join(projected)),updated_sha256=matrix_hash,
                          discrete_sha256=canonical_hash(discrete),score_f32le=scores8.hex(),
                          native_read_sha256=sha(bits(read)),native_read_f32le=bits(read).hex())
    row["native32"] = {k:v for k,v in native.items() if k != "read"}
    return row


def run(candidate, work):
    global torch,matrix,online,account
    historical = json.loads(blob(DATA,EVIDENCE+"runtime.json"))
    manifest = historical["evidence_sha256"]
    assert historical["candidate"] == PREVIOUS
    inputlog = json.loads(blob(DATA,EVIDENCE+"inputs.json",manifest["inputs.json"]))["blobs_sha256"]
    for module in ("matrix","online"):
        path = f"docs/research/WP-0024/probe/{module}.py"
        (work / (module+".py")).write_bytes(blob(SOURCE,path,inputlog[SOURCE+":"+path]))
    sys.path[:0] = [str(work),str(HERE)]
    import torch, numpy, matrix, online, account
    for module in (matrix,online):
        file = Path(module.__file__)
        assert file.parent == work and sha(file.read_bytes()) == inputlog[SOURCE+":docs/research/WP-0024/probe/"+file.name]
    assert Path(account.__file__).resolve() == HERE / "account.py"
    assert str(torch.__version__) == "2.13.0+cpu" and numpy.__version__ == "2.2.6"
    assert torch.version.cuda is None and torch.get_default_dtype() == torch.float32 and matrix.EPS == account.EPS
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.default_generator.manual_seed(32)
    assert torch.get_num_threads() == torch.get_num_interop_threads() == 1
    archived_review = json.loads(blob(REVIEW,"docs/reviews/WP-0031/evidence/replay.json"))["probes"]
    close = json.loads(blob(CLOSE,"docs/coordination/WP-0031/reconciliation.json"))
    assert close["author_revision"] == DATA and close["review_revision"] == REVIEW
    cells, differences = {}, {}
    with torch.inference_mode():
        for arm,tags in TAGS.items():
            document = json.loads(blob(DATA,EVIDENCE+arm+".json",manifest[arm+".json"]))
            assert document["status"] == "completed" and document["thresholds"] == [1.,.1]
            assert document["owner_order"] == NAMES and archived_review[arm]["native_gate"]
            weightp = f"docs/research/WP-0026/fit/{arm}.pt"
            weights = blob(FIT,weightp,inputlog[FIT+":"+weightp])
            model = matrix.Memory(flat=arm=="M1").eval()
            model.load_state_dict(torch.load(io.BytesIO(weights),map_location="cpu",weights_only=True),strict=True)
            data = close["probes"][arm]
            cells[arm] = {tag:run_cell(arm,tag,document,archived_review[arm],data["cells"][tag],manifest,model)
                          for tag in tags}
            for prefix in (("A","C") if arm == "M1" else ("0",)):
                a,c = (cells[arm][prefix+d] for d in ("A","C"))
                original = data["D0"] if arm == "M3" else data["contrasts"]["D"+prefix]
                differences[arm+"/"+prefix] = account.donor_differences(arm,prefix,a,c,a["native32"],c["native32"],original)
    write_json(work/"tables.json", {"cells": cells,"donor_Alder_minus_Cedar": differences})
    # Full coordinatewise audit is recoverable from the frozen code and linked raw vectors.
    groups = {}
    for item in account.CHECKS:
        quantity = item["quantity"].split("[",1)[0]
        group = groups.setdefault(quantity,{"checks":0,"largest_absolute":item,"largest_limit_fraction":item})
        group["checks"] += 1
        for key,field in (("largest_absolute","absolute"),("largest_limit_fraction","fraction")):
            if item[field] > group[key][field]:
                group[key] = item
    write_json(work/"gates.json",dict(all_pass=True,total=len(account.CHECKS),groups=groups,
               residual_definition="absolute difference in the named quantity's native units",
               limit="2e-5*(1+max(abs(reference),abs(reconstruction))); paired sums for differences"))
    write_json(work/"run.json",dict(candidate=candidate,base=BASE,argv=sys.orig_argv,executable=str(sys.executable),
               executable_sha256=PYHASH,python=platform.python_version(),numpy=numpy.__version__,torch=str(torch.__version__),
               intra_threads=torch.get_num_threads(),inter_threads=torch.get_num_interop_threads(),cuda=torch.version.cuda,
               deterministic=torch.are_deterministic_algorithms_enabled(),platform=platform.platform(),blob_sha256=INPUTS,
               utc=dt.datetime.now(dt.UTC).isoformat(),evidence_sha256={name:sha((work/name).read_bytes())
                                                                        for name in ("tables.json","gates.json")}))
    print(f"Native score bytes equal in six cells; {len(account.CHECKS)} numerical checks passed.")


if __name__ == "__main__":
    candidate, = sys.argv[1:]
    work = bind_work(candidate)
    try:
        run(candidate,work)
    except Exception:
        (work/"failure.txt").write_text(traceback.format_exc(),encoding="utf-8")
        raise
