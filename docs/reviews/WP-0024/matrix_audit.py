"""Run independent deterministic CPU checks against an exact probe Git object."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import types


def isolated_environment():
    scratch = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0024/review/cpu")
    for key in ("TMP", "TEMP", "TORCH_HOME", "HF_HOME", "TORCHINDUCTOR_CACHE_DIR", "TORCH_EXTENSIONS_DIR",
                "APPDATA", "LOCALAPPDATA", "MPLCONFIGDIR"):
        path = scratch/key.lower()
        path.mkdir(parents=True, exist_ok=True)
        os.environ[key] = str(path)
    os.environ.update(CUDA_VISIBLE_DEVICES="-1", CUDA_CACHE_DISABLE="1", HF_HUB_OFFLINE="1",
                      HF_HUB_DISABLE_TELEMETRY="1", TRANSFORMERS_OFFLINE="1")


def materialize(revision):
    hashes = {}
    for name in ("online","matrix","views"):
        path = f"docs/research/WP-0024/probe/{name}.py"
        spec = f"{revision}:{path}"
        source = subprocess.check_output(["git","show",spec])
        module = types.ModuleType(name)
        module.__file__ = spec
        sys.modules[name] = module
        exec(compile(source, spec, "exec"), module.__dict__)
        hashes[path] = hashlib.sha256(source).hexdigest()
    return hashes


def audit(revision):
    import torch
    from torch.nn import functional as F
    assert re.fullmatch("[0-9a-f]{40}", revision)
    assert subprocess.check_output(["git","rev-parse",revision+"^{commit}"],text=True).strip() == revision
    hashes = materialize(revision)
    from matrix import Memory
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    def seeded(flat):
        torch.manual_seed(9041)
        return Memory(flat).eval()
    flat, strat = seeded(True), seeded(False)
    params = sum(p.numel() for p in flat.parameters())
    assert params == sum(p.numel() for p in strat.parameters()) == 880258
    assert list(flat.state_dict()) == list(strat.state_dict())
    assert all(torch.equal(v, strat.state_dict()[k]) for k,v in flat.state_dict().items())
    assert len(flat.zero()) == 1 and len(strat.zero()) == 8
    out = {"revision": revision, "probe_blobs_sha256": hashes, "device": "cpu", "torch": str(torch.__version__),
           "matched_parameters": params, "same_seed_equal_initial_weights": True}
    rng = torch.Generator(device="cpu").manual_seed(187)
    normal = lambda *size: torch.randn(size, generator=rng, dtype=torch.float32)
    max_error = 0.0
    max_inactive = 0.0
    with torch.no_grad():
        for model, count in ((flat,1),(strat,8)):
            matrices = tuple(normal(128,128) for _ in range(count))
            for i in range(24):
                depth = (i*5) % 8
                active = 0 if model.flat else depth
                # Exercise every lane on a dense Gaussian state, non-unit decay and over-relaxation.
                k, v = F.normalize(normal(128), dim=0), normal(128)
                alpha = torch.tensor(0.65 + (i%7)*0.04)
                beta = torch.tensor(1.02 + (i%5)*0.16)
                new = model.write(matrices,depth,k,v,alpha,beta)
                for d in range(count):
                    prev = matrices[d].double()
                    decay = float(alpha) if d == active else 1.0
                    km = k.double() if d == active else torch.zeros(128,dtype=torch.float64)
                    ref = decay*prev + float(beta)*(v.double() - decay*prev.mv(km)).unsqueeze(1)*km
                    error = (new[d].double()-ref).abs().max().item()
                    if active == d:
                        max_error = max(max_error,error)
                    else:
                        assert torch.equal(matrices[d], new[d])
                        max_inactive = max(max_inactive,error)
                    assert error < 4e-6
                matrices = new
        out.update(write_steps_per_model=24, max_active_vs_fp64=max_error, max_inactive_change=max_inactive)
        # Independent closed-form example: compressed child columns map to four known
        # summary-coordinate axes. This permits testing the rank threshold and override
        # without importing the candidate QR, read, or pop as the expected implementation.
        strat.summary_query.zero_()
        strat.summary_query[:4,:] = torch.eye(4)
        strat.pop_key.weight.zero_()
        strat.pop_key.weight[96:100,:4] = torch.eye(4)
        strat.pop_value.weight.copy_(torch.eye(128))
        pop_cases = []
        for values in ((3.0,2.0,1.0,0.5),(3.0,2.0,5e-7,0.0),(3.0,2.0,2e-6,0.0),(0.,0.,0.,0.)):
            parent = normal(128,128)
            child = torch.zeros(128,128)
            child[:4,:4] = torch.diag(torch.tensor(values))
            before = tuple(normal(128,128) for _ in range(3))+(parent,child)+tuple(normal(128,128) for _ in range(3))
            after, keep = strat.pop(before,4)
            selected = [j for j,val in enumerate(values) if abs(val)>=1e-6]
            assert keep.tolist() == [j in selected for j in range(4)]
            ref = parent.clone()
            for j in selected:
                ref[:,96+j] = child[:,j]
            assert torch.allclose(after[3],ref,rtol=1e-6,atol=1e-6)
            assert torch.equal(after[3][:,:96],parent[:,:96])
            if not selected:
                assert torch.equal(after[3],parent)
            assert after[4].count_nonzero().item() == 0
            assert all(torch.equal(old,new) for d,(old,new) in enumerate(zip(before,after)) if d not in (3,4))
            for field in ("owner","unit","column"):
                query = normal(128)
                r0,r1 = strat.read(before,3,query,field),strat.read(after,3,query,field)
                assert torch.equal(r0,r1)
            query = normal(128)
            delta = (strat.read(before,3,query,"subtotal_status")-strat.read(after,3,query,"subtotal_status")).abs().max().item()
            assert (delta>0) == bool(selected)
            pop_cases.append({"summary_singular_values":values,"rank":len(selected),"protected_fp32_delta":0.,
                              "summary_read_linf_delta":delta,"wiped_child_nonzero":int(after[4].count_nonzero())})
        out["pop_cases"] = pop_cases
    return out


if __name__ == "__main__":
    assert sys.flags.isolated and sys.dont_write_bytecode and len(sys.argv)==2
    isolated_environment()
    print(json.dumps(audit(sys.argv[1]),indent=2))

