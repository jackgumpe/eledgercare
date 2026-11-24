"""Independent binary64 reconstruction and signed uncertainty accounting."""
import math
import numpy as np

EPS = 1e-8
LABELS = ("Alder", "Cedar", "margin")


def v64(t):
    return np.asarray(t.detach().contiguous().numpy(), dtype="<f8")


def packed(a):
    return np.asarray(a, dtype="<f8").tobytes().hex()


def scalar(x):
    x = float(x)
    if not math.isfinite(x):
        raise ValueError("nonfinite measurement")
    return x


def limit(a, b):
    return 2e-5 * (1 + max(abs(a), abs(b)))


def compare(observed, predicted, budget=None):
    observed, predicted = scalar(observed), scalar(predicted)
    budget = limit(observed, predicted) if budget is None else scalar(budget)
    residual = observed - predicted
    data = dict(observed=observed, predicted=predicted, residual=residual, budget=budget,
                passed=abs(residual) <= budget)
    if not data["passed"]:
        raise ArithmeticError(data)
    return data


def signed(data):
    value, budget = data["observed"], data["budget"]
    direction = "positive" if value > budget else "negative" if value < -budget else "unresolved"
    # Both observations must clear the same signed threshold to claim a sign.
    other = data["predicted"]
    if (direction == "positive" and other <= budget) or (direction == "negative" and other >= -budget):
        direction = "unresolved"
    return dict(**data, sign=direction)


def combination(terms):
    obs, pred, budget = (math.fsum((abs(k) if key == "budget" else k) * x[key] for k, x in terms)
                         for key in ("observed", "predicted", "budget"))
    return signed(compare(obs, pred, budget))


def vector(obs, pred):
    obs, pred = np.asarray(obs, dtype="<f8"), np.asarray(pred, dtype="<f8")
    assert obs.shape == pred.shape and np.isfinite(obs).all() and np.isfinite(pred).all()
    residual = obs - pred
    budgets = 2e-5 * (1 + np.maximum(np.abs(obs), np.abs(pred)))
    fractions = np.abs(residual) / budgets
    worst = np.unravel_index(np.argmax(fractions), obs.shape)
    check = compare(obs[worst], pred[worst])
    return dict(observed_f64le=packed(obs), predicted_f64le=packed(pred), shape=list(obs.shape),
                maximum_fraction=float(fractions[worst]), worst_index=list(map(int,worst)), worst=check,
                pass_count=obs.size, fail_count=0,
                residuals_and_budgets="elementwise observed-predicted, 2e-5*(1+max(abs(observed),abs(predicted)))")


def directions(query, anchors):
    q = v64(query)[:32]
    u = np.zeros(128)
    u[:32] = q / (np.linalg.norm(q) + EPS)
    a, c = v64(anchors)
    return u, np.stack((a, c, a-c))


def read_checks(native, scores, predicted, axes):
    observed = v64(native)
    norms = [np.linalg.norm(x) for x in (observed,predicted)]
    dots = axes @ predicted
    empirical = [*scores.tolist(), scores[0].item()-scores[1].item()]
    return dict(read=vector(observed, predicted), norm=compare(*norms),
                denominator=compare(*(n+EPS for n in norms)),
                numerator=signed(compare(axes[-1] @ observed, dots[-1])),
                scores={label:signed(compare(actual, num / (norms[1]+EPS)))
                        for label,actual,num in zip(LABELS,empirical,dots,strict=True)})


def m1_components(old, fields, u, axes, archived, scalars):
    k,v,a,b = (v64(x) for x in fields)
    z = k @ u
    oldk = v64(old) @ k
    retained = float(a) * (v64(old) @ u)
    direct = float(b) * z * v
    erased = -float(a*b) * z * oldk
    parts = (retained, direct, erased)
    assert scalars["omitted_numerator"] > 0 and scalars["term_numerators"][2] < 0
    p = axes[-1] @ (retained+direct)
    l = axes[-1] @ erased
    record = dict(z=scalar(z), alpha=scalar(a), beta=scalar(b), recipient_times_full_key=packed(oldk),
                  P=compare(p,scalars["omitted_numerator"]), L=compare(l,scalars["term_numerators"][2]),
                  archived_terms={}, u_f64le=packed(u), margin_axis_f64le=packed(axes[-1]))
    for tag,term in zip(("R","V","E"),parts,strict=True):
        historical = np.frombuffer(bytes.fromhex(archived[tag]["vector_f64le"]),dtype="<f8")
        record["archived_terms"][tag] = vector(term,historical)
    return parts, record


def m1_roots(tables, betas, contract):
    p = {s:x["omitted_numerator"] for s,x in tables.items()}
    l = {s:x["term_numerators"][2] for s,x in tables.items()}
    roots = {s:-p[s]/l[s] for s in tables}
    assert roots == contract["roots"]
    assert contract["relative"]["root_AA"] == roots["AA"] and contract["relative"]["root_CC"] == roots["CC"]
    assert contract["relative"]["midpoint"] == (roots["AA"]+roots["CC"])/2
    absolute = {s:r*betas[s[1]] for s,r in roots.items()}

    def bounds(r):
        return dict(four_cell_open=[max(r["AC"],r["CC"]),min(r["AA"],r["CA"])],
                    original_twins_open=[r["CC"],r["AA"]])

    raw = {i:(p[i+"A"]-p[i+"C"])/(l[i+"C"]-l[i+"A"]) for i in ("A","C")}
    return dict(relative=roots,absolute=absolute,relative_intervals=bounds(roots),absolute_intervals=bounds(absolute),
                raw_donor_contrast_roots_relative=raw)


def m3_account(fields, u, axes, feature, box, weight, native, scores):
    k,v,a,b = map(v64,fields)
    z = k @ u
    t = b*z
    length = np.linalg.norm(v)
    raw_read = t*v
    den = abs(t)*length+EPS
    f = weight[:,:1280] @ feature
    g = weight[:,1280:] @ box
    checks = read_checks(native,scores,raw_read,axes)
    checks["factorized_norm"] = compare(checks["norm"]["observed"],abs(t)*length)
    checks["value"] = vector(v,f+g)
    native_t = b*((k[:32].astype("f4") @ u[:32].astype("f4")).item())
    scale = signed(compare(t,native_t))
    records = {}
    for coord,(label,w) in enumerate(zip(LABELS,axes,strict=True)):
        raw = signed(compare(w@v,w@f+w@g))
        observed = checks["scores"][label]["observed"]
        score = signed(compare(observed,t*raw["observed"]/den))
        attenuation = abs(t)*length/den
        signed_alignment = np.sign(t)*(w@v)/length if length else 0.
        alternate = compare(observed,attenuation*signed_alignment)
        records[label]=dict(raw=raw, feature=scalar(w@f), box=scalar(w@g), normalized=score,
                            attenuation_score=alternate,signed_directional_alignment=scalar(signed_alignment))
    return checks,dict(z=scalar(z),alpha=scalar(a),beta=scalar(b),t=scale,value_norm=scalar(length),
                       denominator=scalar(den),epsilon=EPS,epsilon_over_abs_t=scalar(EPS/abs(t)) if t else None,
                       attenuation=scalar(abs(t)*length/den),signed_scale_factor=scalar(t/den),axes=records,
                       encoded_box_f64le=packed(box),feature_projection_f64le=packed(f),box_projection_f64le=packed(g))


def factorial(rows):
    fields={}
    terms={"pooled_at_A_box":[(1,"AA"),(-1,"CA")], "pooled_at_C_box":[(1,"AC"),(-1,"CC")],
           "box_at_A_pooled":[(1,"AA"),(-1,"AC")], "box_at_C_pooled":[(1,"CA"),(-1,"CC")],
           "diagonal":[(1,"AA"),(-1,"CC")], "interaction":[(1,"AA"),(-1,"CA"),(-1,"AC"),(1,"CC")]}
    for label in LABELS:
        records = {s:row["m3"]["axes"][label] for s,row in rows.items()}
        fields[label] = {}
        for mode in ("raw","normalized"):
            result = {op:combination([(k,records[s][mode]) for k,s in parts]) for op,parts in terms.items()}
            diag = result["diagonal"]
            for tag,f1,f2 in (("via_CA","pooled_at_A_box","box_at_C_pooled"),
                              ("via_AC","pooled_at_C_box","box_at_A_pooled")):
                result[tag] = compare(diag["observed"],result[f1]["predicted"]+result[f2]["predicted"],
                                      diag["budget"] + 2*records["CA" if tag=="via_CA" else "AC"][mode]["budget"])
            if mode == "raw":
                df = records["AA"]["feature"]-records["CC"]["feature"]
                db = records["AA"]["box"]-records["CC"]["box"]
                result["feature_plus_box"]=compare(diag["observed"],df+db,diag["budget"])
                result["zero_interaction"]=compare(result["interaction"]["observed"],0,result["interaction"]["budget"])
                for name,expected in (("pooled_at_A_box",df),("pooled_at_C_box",df),("box_at_A_pooled",db),("box_at_C_pooled",db)):
                    result[name+"_split"]=signed(compare(result[name]["observed"],expected,result[name]["budget"]))
            fields[label][mode]=result
    return fields
