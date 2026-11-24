"""Declaration-local erasure in its relative and absolute units."""
import torch

from bindings import opened
from metrics import CELLS, EPS, compare_read, effect, limit, observe, pack, parity, raw, sign

def unpack_archived(obj):
    return torch.frombuffer(bytearray.fromhex(obj["bytes_le"]), dtype=torch.float64).reshape(obj["shape"])


def terms(src, donor, anchors):
    k, v, alpha, beta = (x.double() for x in donor["tensors"])
    old = src["state"].matrices[0].double()
    q = src["query"][:32].double()
    u = q/(q.norm()+EPS)
    z = k[:32] @ u
    old_k = old @ k
    r = alpha*(old[:,:32] @ u)
    direct = beta*z*v
    erasure = -alpha*beta*z*old_k
    h = anchors[0].double()-anchors[1].double()
    return (r,direct,erasure), dict(u=pack(u), h=pack(h), old_k=pack(old_k), z=float(z), alpha=float(alpha), beta=float(beta),
                                    R=pack(r), V=pack(direct), E=pack(erasure), P=float(h@(r+direct)), L=float(h@erasure))


def analyze(contract, model, sources, anchors, cuts, controls, prior, table, checks, out, parity_rows):
    vectors, operands, roots, etas = {}, {}, {}, {}
    for cell in CELLS:
        p,d = cell
        vectors[cell], args = terms(sources[p],sources[d],anchors)
        historical = table["M1"][cell]
        P, L = historical["omitted_numerator"], historical["term_numerators"][2]
        checks.scalar(cell+"/P",args["P"],P)
        checks.scalar(cell+"/L",args["L"],L)
        assert sign(P)["sign"] == "positive" and sign(L)["sign"] == "negative"
        root = -P/L
        assert root == contract["roots"][cell]
        for n, vec in zip(("R","V","E"),vectors[cell],strict=True):
            checks.vector(cell+"/archived_"+n,vec,unpack_archived(prior["cells"][cell]["terms"][n]["vector"]))
        roots[cell], etas[cell] = root, root*args["beta"]
        args.update(published_P=P, published_L=L, relative_root=root, absolute_root=etas[cell])
        operands[cell]=args
    assert contract["relative"]["root_AA"] == roots["AA"] and contract["relative"]["root_CC"] == roots["CC"]
    assert contract["relative"]["midpoint"] == (roots["AA"]+roots["CC"])/2
    def intervals(x):
        return {"all_four_open":[max(x["AC"],x["CC"]),min(x["AA"],x["CA"])],"original_twins_open":[x["CC"],x["AA"]]}
    raw_roots = {}
    for prefix in "AC":
        a,c = (operands[prefix+j] for j in "AC")
        raw_roots[prefix] = (a["published_P"]-c["published_P"])/(c["published_L"]-a["published_L"])
    out.update(operands=operands,relative_intervals=intervals(roots),absolute_intervals=intervals(etas),raw_donor_relative_roots=raw_roots,
               normalized_contrast_rule="subtract empirical margins after per-cell normalization",rows=[],summary=[])
    for mode in ("relative","absolute"):
        for point,requested in contract[mode].items():
            point_rows = {}
            for cell in CELLS:
                prefix,donor = cell
                state, binding = opened(sources[prefix],sources[donor]["events"],False)
                k,v,a,b = sources[donor]["tensors"]
                old = state.matrices[0]
                gain = torch.tensor(requested,dtype=torch.float32)
                # The relative residual matches the native primitive's operation order at one.
                if mode == "relative":
                    rho = float(gain)
                    eta = rho*float(b)
                    residual = v - gain * (a * (old @ k))
                    updated = a * old + b * torch.outer(residual,k)
                else:
                    eta = float(gain)
                    rho = eta/float(b)
                    updated = (a * old + b * torch.outer(v,k)) - gain * torch.outer(a * (old @ k),k)
                state.matrices = (updated,)
                assert torch.isfinite(updated).all()
                native,vec,obs = observe(model,state,sources[prefix]["query"],anchors,cuts)
                r,direct,e = vectors[cell]
                y = r+direct+rho*e
                tag = f"{mode}/{point}/{cell}"
                pred = compare_read(tag,native,vec,obs,y,anchors,checks)
                args = operands[cell]
                req_rho = requested if mode=="relative" else requested/float(b)
                pred_req = args["published_P"]+req_rho*args["published_L"]
                pred_exec = args["published_P"]+rho*args["published_L"]
                checks.scalar(tag+"/affine_executed_numerator",obs["numerator"],pred_exec)
                if point == "0" and mode == "relative":
                    omitted = prior["cells"][cell]["omitted"]
                    checks.vector(tag+"/archived_omitted_vector",vec,unpack_archived(omitted["read"]))
                    for field in ("numerator","denominator","margin"):
                        val = native["margin"] if field=="margin" else obs[field]
                        checks.scalar(tag+"/omitted_"+field,val,omitted["metrics"][field])
                if point == "1" and mode == "relative":
                    ref = controls[cell]["native"]
                    assert all(native[k] == ref[k] for k in ("read_f32le","score_f32le","matrix_sha256","owner_columns_sha256"))
                signed = sign(obs["numerator"])
                expected_sign = "positive" if donor=="A" else "negative"
                row = dict(arm="M1",mode=mode,point=point,cell=cell,status="observed",gain_requested_f64=requested,
                           gain_executed_f32=pack(gain),gain_executed=float(gain),realized_relative=rho,realized_absolute=eta,
                           realized_absolute_f32=pack(torch.tensor(eta)),absolute_times_alpha=eta*float(a),
                           donor_truth="Alder" if donor=="A" else "Cedar",discrete=binding,native=native,observed_fp64=obs,
                           prediction=pred,requested_affine_numerator=pred_req,executed_affine_numerator=pred_exec,
                           sign=signed,correct_resolved_rank=signed["sign"]==expected_sign, predicted_vector=pack(y))
                out["rows"].append(row)
                point_rows[cell]=row
                parity_rows.append(parity("M1",mode,point,cell,native,obs))
            contrasts = {}
            for prefix in "AC":
                coefs=((prefix+"A",1),(prefix+"C",-1))
                measures = {}
                for field in ("numerator","margin"):
                    observed={c:(row["native"]["margin"] if field=="margin" else row["observed_fp64"][field]) for c,row in point_rows.items()}
                    predicted={c:row["prediction"][field] for c,row in point_rows.items()}
                    delta=effect(observed,coefs,predicted)
                    checks.scalar(f"{mode}/{point}/{prefix}/donor_{field}",delta["value"],delta["predicted"],delta["budget"])
                    if mode=="relative" and point in ("0","1"):
                        ref=table["M1_donor_contrasts"][prefix]
                        name="omitted_"+field if point=="0" else "native_margin" if field=="margin" else "restored_numerator"
                        checks.scalar(f"endpoint/{point}/{prefix}/{field}",delta["value"],ref[name],delta["budget"])
                    measures[field]=delta
                contrasts[prefix]=measures
            correct=[c for c,row in point_rows.items() if row["correct_resolved_rank"]]
            out["summary"].append(dict(mode=mode,point=point,contrasts=contrasts,resolved_correct=correct,
                                       four_donor_ranks=all(c in correct for c in CELLS),
                                       both_original_twins=all(c in correct for c in ("AA","CC"))))
