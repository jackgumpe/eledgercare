"""FP64 accounting from frozen FP32 operands, with explicit native reconstruction gates."""
import math

import torch
from restore import NAMES, raw, sha

EPS = 1e-8
RULE = {"residual": "reconstructed minus reference", "gate": "abs(residual) <= 2e-5 * (1 + max(abs(reference), abs(reconstructed)))",
        "donor_difference": "Alder donor minus Cedar donor; add the two per-cell budgets",
        "sign": "resolved only when absolute value exceeds its comparison budget",
        "units": {"read_coordinate": "read units", "norm": "read units", "denominator": "read units",
                  "numerator": "anchor dot read", "score": "normalized anchor score", "margin": "Alder score minus Cedar score"}}


def budget(reference, reconstruction):
    return 2e-5 * (1 + max(abs(reference), abs(reconstruction)))


def check(gates, group, location, reference, reconstruction, limit=None):
    assert math.isfinite(reference) and math.isfinite(reconstruction)
    if limit is None:
        limit = budget(reference, reconstruction)
    residual = reconstruction - reference
    gates.setdefault(group, []).append({"at": location, "reference": reference, "reconstructed": reconstruction,
        "residual": residual, "limit": limit, "fraction_of_limit": abs(residual) / limit, "pass": abs(residual) <= limit})


def summaries(gates):
    return {group: {"scalars": len(rows), "failed": sum(not row["pass"] for row in rows),
                    "max_absolute_residual": max(rows, key=lambda r: abs(r["residual"])),
                    "max_fraction_of_limit": max(rows, key=lambda r: r["fraction_of_limit"])}
            for group, rows in gates.items()}


def signed(value, uncertainty):
    direction = "unresolved"
    if abs(value) > uncertainty:
        direction = "positive" if value > 0 else "negative"
    return {"value": value, "uncertainty": uncertainty, "sign": direction}


def pack(vector):
    data = raw(vector)
    return {"shape": list(vector.shape), "dtype_le": str(vector.dtype), "bytes_le": data.hex(), "sha256": sha(data)}


def read_metrics(vector, anchors, scores=None):
    # In the native row all products/norms are FP32 and the original candidate scores are supplied.
    # Native margin is the difference of the two already-rounded FP32 scores promoted to FP64.
    # In each FP64 analytic row the summed read is normalized once with its own denominator.
    norm = vector.norm()
    denominator = norm + EPS
    numerators = anchors @ vector
    if scores is None:
        scores = anchors @ (vector / denominator)
    return {"norm": norm.item(), "denominator": denominator.item(), "alder_numerator": numerators[0].item(),
            "cedar_numerator": numerators[1].item(), "numerator": ((anchors[0] - anchors[1]) @ vector).item(),
            "alder_score": scores[0].item(), "cedar_score": scores[1].item(), "margin": scores[0].item() - scores[1].item()}


def components(old, key, value, alpha, beta, u, z):
    # old @ key uses all 128 coordinates, whereas the query projection uses only 32 owner columns.
    return {"R": alpha * (old[:, :32] @ u), "V": (beta * z) * value, "E": (-alpha * beta * z) * (old @ key)}


def cell(arm, label, native, gates):
    old, tensors, query, anchor32, vector32, scores32, bindings = native
    where = f"{arm}/{label}"
    key, value, alpha, beta = (x.double() for x in tensors)
    anchors = anchor32.double()
    h = anchors[0] - anchors[1]
    q = query[:32].double()
    u = q / (q.norm() + EPS)
    z = key[:32] @ u
    original = read_metrics(vector32, anchor32, scores32)
    native_read64 = vector32.double()
    native64 = read_metrics(native_read64, anchors)
    result = {"binding": bindings, "native_read": pack(vector32), "native_fp32": original,
              "fp64_on_promoted_native_read": native64, "u": pack(u), "owner_key_dot": z.item(), "alpha": alpha.item(),
              "beta": beta.item(), "beta_times_owner_key_dot": (beta * z).item()}

    if arm == "M1":
        terms = components(old.double(), key, value, alpha, beta, u, z)
        omitted = terms["R"] + terms["V"]
        restored = omitted + terms["E"]
        common = native64["denominator"]
        result["common_native_read_denominator_fp64"] = common
        result["terms"] = {}
        for name, term in terms.items():
            numerator = (h @ term).item()
            result["terms"][name] = {"vector": pack(term), "norm": term.norm().item(), "numerator": numerator,
               "numerator_over_common_native_denominator": numerator / common,
               "numerator_over_native_fp32_denominator": numerator / original["denominator"]}
        metrics = read_metrics(omitted, anchors)
        result["omitted"] = {"read": pack(omitted), "metrics": metrics}
        for field in ("numerator", "margin"):
            result["omitted"].setdefault("signs", {})[field] = signed(metrics[field], budget(metrics[field], metrics[field]))
    else:
        assert int(torch.count_nonzero(old)) == 0
        gain = beta * z
        restored = gain * value
        value_norm = value.norm()
        read_norm = restored.norm()
        shrink = (read_norm / (read_norm + EPS)).item()
        result["value"] = {"norm": value_norm.item(), "vector": pack(value), "finite_epsilon_factor": shrink,
                           "alignment": {}}
        for name, anchor in zip(NAMES, anchors, strict=True):
            anchor_norm = anchor.norm().item()
            dot = (anchor @ value).item()
            normalized = dot / value_norm.item()
            # Preserve the actual anchor, including the effect of its original FP32 normalization.
            recovered = gain.item() * dot / (abs(gain.item()) * value_norm.item() + EPS)
            result["value"]["alignment"][name] = {"anchor_norm": anchor_norm, "raw_dot": dot,
               "dot_with_unit_value": normalized, "cosine": normalized / anchor_norm,
               "dot_with_epsilon_normalized_value": dot / (value_norm.item() + EPS),
               "recovered_score_via_value": recovered, "finite_epsilon_score_change": recovered - math.copysign(1., gain.item()) * normalized}
            check(gates, "native_vs_value_score", where + "/" + name, original[name.lower() + "_score"], recovered)
        result["gain_sign"] = signed(gain.item(), budget(gain.item(), gain.item()))

    analytic = read_metrics(restored, anchors)
    result["restored"] = {"read": pack(restored), "metrics": analytic}
    for idx, (actual, rebuilt) in enumerate(zip(native_read64.tolist(), restored.tolist(), strict=True)):
        check(gates, "native_vs_rearranged_read_coordinate", f"{where}[{idx}]", actual, rebuilt)
    for field in original:
        check(gates, "native_vs_rearranged_" + field, where, original[field], analytic[field])
        check(gates, "promoted_native_vs_rearranged_" + field, where, native64[field], analytic[field])
    h_margin = analytic["numerator"] / analytic["denominator"]
    result["restored"]["h_margin"] = h_margin
    check(gates, "native_vs_rearranged_h_margin", where, original["margin"], h_margin)
    for field in ("numerator", "margin"):
        result["restored"].setdefault("signs", {})[field] = signed(analytic[field], budget(original[field], analytic[field]))
    if arm == "M1":
        omitted = result["omitted"]["metrics"]
        result["omitted"]["h_margin"] = omitted["numerator"] / omitted["denominator"]
        result["restored_minus_omitted"] = {field: analytic[field] - omitted[field] for field in ("numerator", "margin")}
        term_sum = sum(term["numerator"] for term in result["terms"].values())
        check(gates, "native_vs_term_sum_numerator", where, original["numerator"], term_sum)
        check(gates, "native_vs_common_denominator_term_sum_margin", where, original["margin"], term_sum / common)
    return result


def donor_contrasts(arm, rows, gates):
    contrasts = {}
    prefixes = ("A", "C") if arm == "M1" else ("0",)
    for prefix in prefixes:
        first, second = (rows[prefix + donor] for donor in ("A", "C"))
        native_a, native_c = first["native_fp32"], second["native_fp32"]
        analytic_a, analytic_c = first["restored"]["metrics"], second["restored"]["metrics"]
        changes = {}
        for field in ("alder_score", "cedar_score", "margin", "numerator", "alder_numerator", "cedar_numerator"):
            reference = native_a[field] - native_c[field]
            rebuilt = analytic_a[field] - analytic_c[field]
            limit = budget(native_a[field], analytic_a[field]) + budget(native_c[field], analytic_c[field])
            check(gates, "native_vs_rearranged_donor_" + field, f"{arm}/{prefix}A-{prefix}C", reference, rebuilt, limit)
            changes[field] = {"native": reference, "restored": signed(rebuilt, limit)}
            if arm == "M1" and field in ("numerator", "margin"):
                oa, oc = first["omitted"]["metrics"][field], second["omitted"]["metrics"][field]
                omitted = oa - oc
                omitted_limit = budget(oa, oa) + budget(oc, oc)
                changes[field]["omitted"] = signed(omitted, omitted_limit)
                changes[field]["restored_minus_omitted"] = signed(rebuilt - omitted, limit + omitted_limit)
        contrasts[prefix] = changes
    return contrasts
