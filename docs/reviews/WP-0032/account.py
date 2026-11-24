"""Scalar binary64 accounting, with retained binary32 values widened exactly."""
from math import fsum, isfinite, sqrt
import struct

EPS = 1e-8
NAMES = ("Alder", "Cedar")
CHECKS = []


def dot(x, y):
    return fsum(a * b for a, b in zip(x, y, strict=True))


def norm(x):
    return sqrt(dot(x, x))


def ratio_limit(x, y):
    return 2e-5 * (1 + max(abs(x), abs(y)))


def check(cell, quantity, ref, value, bound=None):
    residual = abs(ref - value)
    limit = ratio_limit(ref, value) if bound is None else bound
    CHECKS.append(dict(cell=cell, quantity=quantity, reference=ref, reconstruction=value,
                       absolute=residual, limit=limit, fraction=residual / limit))
    if not isfinite(residual) or residual > limit:
        raise ArithmeticError(CHECKS[-1])


def check_coordinates(cell, which, ref, value):
    for j, (a,b) in enumerate(zip(ref, value, strict=True)):
        check(cell, f"{which}[{j}]", a, b)


def summarize(read, anchors, h):
    length = norm(read)
    den = length + EPS
    score = {name: dot(anchor, read) / den for name, anchor in zip(NAMES, anchors, strict=True)}
    numerator = dot(h, read)
    return dict(norm=length, denominator=den, numerator=numerator, scores=score, margin=numerator / den)


def f64(x):
    return struct.pack(f"<{len(x)}d", *x).hex()


def one_cell(probe, tag, old, k, v, alpha, beta, query, anchors, native):
    cell = f"{probe}/{tag}"
    query_denominator = norm(query[:32]) + EPS
    u = [q / query_denominator for q in query[:32]]
    z = dot(u, k[:32])
    scale = beta * z
    h = [a - c for a,c in zip(*anchors, strict=True)]
    direct = [scale * vi for vi in v]
    if probe == "M1":
        # Contract the full key for the update prediction before reading 32 columns.
        retained = [alpha * dot(row[:32], u) for row in old]
        erased = [-alpha * scale * dot(row, k) for row in old]
        omitted = [a + b for a,b in zip(retained, direct, strict=True)]
        restored = [x + e for x,e in zip(omitted, erased, strict=True)]
    else:
        assert max(abs(x) for row in old for x in row) == 0.0
        restored = direct
    full = summarize(restored, anchors, h)
    exact = summarize(native["read"], anchors, h)
    cell_data = dict(native=exact, restored=full, alpha=alpha, beta=beta, z=z, scale=scale)
    check_coordinates(cell, "read", native["read"], restored)
    for key in ("norm", "denominator", "numerator", "margin"):
        check(cell, key, exact[key], full[key])
    # Independent references against the original read and rounded native call.
    check(cell, "fp32_norm", native["norm"], full["norm"])
    check(cell, "fp32_denominator", native["denominator"], full["denominator"])
    check(cell, "fp32_numerator", native["numerator"], full["numerator"])
    check(cell, "fp32_margin", native["margin"], full["margin"])
    for name in NAMES:
        check(cell, f"score_{name}", native["scores"][name], full["scores"][name])
    check(cell, "margin_by_scores", full["margin"], full["scores"]["Alder"] - full["scores"]["Cedar"])

    if probe == "M1":
        components = {}
        for name, vec in (("R", retained), ("V", direct), ("E", erased)):
            part = dot(h, vec)
            components[name] = dict(vector_f64le=f64(vec), norm=norm(vec), numerator=part,
                                    common_denominator_contribution=part / exact["denominator"],
                                    fp32_denominator_contribution=part / native["denominator"])
        summed = fsum(p["numerator"] for p in components.values())
        check(cell, "summed_numerator", exact["numerator"], summed)
        check(cell, "common_normalized_sum", native["margin"],
              fsum(p["common_denominator_contribution"] for p in components.values()))
        # Alternative contraction of the retained/direct update; no extra native read.
        alt_omitted = [dot([alpha * x + beta * vi * kj for x,kj in zip(row[:32],k[:32],strict=True)],u)
                       for row,vi in zip(old,v,strict=True)]
        check_coordinates(cell, "omitted64", alt_omitted, omitted)
        short = summarize(omitted, anchors, h)
        alt = summarize(alt_omitted, anchors, h)
        for key in ("norm","denominator","numerator","margin"):
            check(cell, "omitted64_" + key, alt[key], short[key])
        check(cell, "omitted_margin_by_scores", short["margin"],
              short["scores"]["Alder"] - short["scores"]["Cedar"])
        cell_data.update(components=components, omitted=short, omitted_alternative=alt)
    else:
        assert scale > 0
        value_norm = norm(v)
        length = abs(scale) * value_norm
        den = length + EPS
        alignments = {}
        for name, anchor in zip(NAMES, anchors, strict=True):
            raw = dot(anchor, v)
            anchor_norm = norm(anchor)
            value_direction_dot = raw / value_norm
            cosine = value_direction_dot / anchor_norm
            attenuation = length / den
            recovered = scale * raw / den
            check(cell, "factorized_score_" + name, native["scores"][name], recovered)
            check(cell, "attenuated_alignment_" + name, recovered, attenuation * cosine * anchor_norm)
            alignments[name] = dict(raw_dot=raw, anchor_norm=anchor_norm, cosine=cosine,
                                    value_direction_dot=value_direction_dot,
                                    eps_normalized_value_dot=raw/(value_norm+EPS), recovered_score=recovered)
        check(cell, "factorized_norm", native["norm"], length)
        check(cell, "factorized_denominator", native["denominator"], den)
        cell_data.update(value_norm=value_norm, factorized_read_norm=length, factorized_denominator=den,
                         alignments=alignments, finite_epsilon_multiplier=length/den)
    return cell_data


def donor_differences(probe, prefix, alder, cedar, native_a, native_c, justification):
    contrasts = {}
    stages = ("omitted", "restored") if probe == "M1" else ("restored",)
    for stage in stages:
        actual = (alder[stage], cedar[stage])
        reference = ((alder["omitted_alternative"], cedar["omitted_alternative"])
                     if stage == "omitted" else (alder["native"], cedar["native"]))
        delta = {}
        for key in ("numerator", "margin", *NAMES):
            if key in NAMES:
                x, y = (r["scores"][key] for r in actual)
                a, c = (r["scores"][key] for r in reference)
                if stage == "restored":
                    a,c = native_a["scores"][key],native_c["scores"][key]
            else:
                x, y = (r[key] for r in actual)
                a, c = (r[key] for r in reference)
                if stage == "restored" and key == "margin":
                    a,c = native_a["margin"],native_c["margin"]
            limit = ratio_limit(a,x) + ratio_limit(c,y)
            check(f"{probe}/{prefix}", f"{stage}_donor_{key}", a - c, x - y, limit)
            delta[key] = dict(value=x-y, reference=a-c, limit=limit, resolved=abs(x-y)>limit)
        contrasts[stage] = delta
    check(f"{probe}/{prefix}", "WP0031_donor_margin", justification, contrasts["restored"]["margin"]["value"],
          contrasts["restored"]["margin"]["limit"])
    if probe == "M1":
        effects = {}
        for key in ("numerator","margin",*NAMES):
            r,o = (contrasts[s][key] for s in ("restored","omitted"))
            bound = r["limit"] + o["limit"]
            diff = r["value"] - o["value"]
            check(f"{probe}/{prefix}", "donor_change_" + key,r["reference"]-o["reference"],diff,bound)
            effects[key] = dict(value=diff,limit=bound,resolved=abs(diff)>bound)
        contrasts["restored_minus_omitted"] = effects
    return contrasts
