"""Deterministic synthetic CPU invariants. Never reads released feature or custody data."""
import json
import os
from pathlib import Path
import sys

if os.environ.get("CUDA_VISIBLE_DEVICES") not in ("", "-1"):
    raise RuntimeError("preflight requires hidden CUDA")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import torch
from matrix import Memory, NeuralState, advance, direction, masked_basis
from online import Span, Window
from run import classification, setup
from views import predict_pair


def construct(records):
    spans = []
    for i, item in enumerate(records):
        cells = tuple(item) if isinstance(item, list) else ()
        literal = " | ".join(item) if cells else item
        spans.append(Span(i, 1, "row" if cells else "block", "table" if cells else "text",
                          literal, cells, (10, i * 15, 900, i * 15 + 10)))
    return Window(tuple(spans), torch.randn(len(spans), 1280))


def histories():
    portfolio = ["Owners: Oak / Palm", "Units: U4 / U7",
                 "Schema: Item / Amount / Ref", "Schema: Item / Ref / Amount"]
    wa = construct(portfolio + ["Ledger: Oak", "Unit: U4", ["Item", "Amount", "Ref"]])
    wb = construct(portfolio + ["Ledger: Palm", "Unit: U7", ["Item", "Ref", "Amount"]])
    ca = construct(["Unit amendment: U7", "Supporting schedule", ["Item", "Ref", "Amount"],
                    "Schedule detail", "Schedule subtotal: 44"])
    cb = construct(["Unit amendment: U4", "Supporting schedule", ["Item", "Ref", "Amount"],
                    "Schedule detail", "Schedule subtotal: 44"])
    closed = construct(["Schedule closed"])
    target = construct([["MAINT-SUMMARY", "44", "44"]])
    return [wa, ca, closed, target], [wb, cb, closed, target]


def calibration_semantics():
    truth = dict(ambiguous=False, owner="Birch", unit="U4", column="Amount", subtotal_status=None)
    p = dict(type="Posting", owner="BIRCH", unit="U4", column="Amount", subtotal_status=None)

    cases = {
        "reviewer_case": (p, truth, (True, False, True)),
        "space_and_entity": ({**p, "owner": " Birch   &amp;    Pine\n"},
                             {**truth, "owner": "birch & Pine"}, (True, False, True)),
        "literal_tag_preserved": ({**p, "owner": "<b>Birch</b>"}, truth, (False, True, True)),
        "escaped_tag_literal": ({**p, "owner": "&lt;Birch&gt;"}, {**truth, "owner": "<birch>"},
                                (True, False, True)),
        "non_null_extra_status": ({**p, "subtotal_status": ""}, truth, (False, True, True)),
        "required_status_missing": (p, {**truth, "subtotal_status": "BALANCED"}, (False, True, True)),
        "summary_casefold": ({**p, "subtotal_status": " Balanced "},
                             {**truth, "subtotal_status": "BALANCED"}, (True, False, True)),
        "answerable_abstention": ({"type": "ABSTAIN"}, truth, (False, False, False)),
        "ambiguous_posting": (p, {**truth, "ambiguous": True}, (False, True, True)),
        "ambiguous_abstention": ({"type": "ABSTAIN"}, {**truth, "ambiguous": True},
                                 (True, False, False))}
    for name, (record, label, expected) in cases.items():
        assert classification(record, label) == expected, name
    try:
        classification({**p, "type": "STATUS"}, truth)
    except ValueError:
        pass
    else:
        raise AssertionError("a subtotal diagnostic is not a typed posting")
    return list(cases) + ["invalid_type_rejected"]


def preflight():
    setup()
    assert not torch.cuda.is_available()
    torch.manual_seed(2401)
    pds = Memory(False)
    torch.manual_seed(2401)
    flat = Memory(True)
    counts = [sum(p.numel() for p in m.parameters()) for m in (pds, flat)]
    assert counts == [880258, 880258]
    assert all(torch.equal(a, b) for a, b in zip(flat.parameters(), pds.parameters()))
    prior = tuple(torch.randn(128, 128) for _ in range(8))
    k = torch.nn.functional.pad(direction(torch.randn(96)), (0, 32))
    updated = pds.write(prior, 4, k, torch.randn(128), torch.tensor(.66), torch.tensor(1.2))
    assert all(torch.equal(prior[j], updated[j]) for j in range(8) if j != 4)
    assert (prior[4] - updated[4]).abs().max().item() > 0
    # Independent dense implementation of the depth-masked recurrence.
    for d in range(8):
        a = .66 if d == 4 else 1.
        key_d = k if d == 4 else torch.zeros_like(k)
        if d == 4:
            v = torch.randn(128)
            test = pds.write(prior, 4, k, v, torch.tensor(a), torch.tensor(1.2))[d]
        else:
            v, test = torch.zeros(128), updated[d]
        expected = a * prior[d] + 1.2 * torch.outer(v - a * (prior[d] @ key_d), key_d)
        assert torch.allclose(test, expected, rtol=1e-6, atol=1e-6)

    test_spans = construct(["child one", "child two", "child three", "child four", "child five"])
    built = list(pds.zero())
    built[2] = prior[2]
    built = tuple(built)
    keys, values, _, a, b = pds.project(test_spans)
    assert torch.count_nonzero(keys[:, 96:]) == 0
    for i in range(len(test_spans.spans)):
        built = pds.write(built, 3, keys[i], values[i], a[i], b[i])
    final, rank = pds.pop(built, 3)
    # Test all 96 coordinate directions, random mixed protected directions and both field partitions.
    queries = torch.nn.functional.pad(torch.randn(16, 96), (0, 32)).T
    protected = (built[2] @ queries - final[2] @ queries).abs().max().item()
    delta = (final[2][:, 96:] - built[2][:, 96:]).abs().max().item()
    assert rank.sum().item() == 4 and delta > 1e-4
    assert torch.equal(final[2][:, :96], built[2][:, :96]) and protected == 0.
    assert not torch.count_nonzero(final[3])
    assert all(torch.equal(final[i], built[i]) for i in (0, 1, 4, 5, 6, 7))
    # Independently check the matrix quotient in full coordinates.
    vals = built[3] @ pds.summary_query
    basis, _ = masked_basis(pds.pop_key(vals.T).T[96:])
    K = torch.nn.functional.pad(basis, (0, 0, 96, 0))
    reference = built[2] @ (torch.eye(128) - K @ K.T) + pds.pop_value(vals.T).T @ K.T
    assert torch.allclose(final[2], reference, rtol=3e-5, atol=3e-6)
    empty, flags = pds.pop(final, 3)
    assert flags.sum() == 0 and torch.equal(final[2], empty[2]) and torch.equal(final[3], empty[3])
    against = torch.zeros(32, 4)
    against[0, 0], against[1, 1], against[2, 2], against[3, 3] = 1., 1e-7, 2e-6, 0.
    basis2, keep = masked_basis(against)
    assert keep.tolist() == [True, False, True, False] and not torch.count_nonzero(basis2[:, ~keep])

    rank_one = pds.write(pds.zero(), 1, keys[0], values[0], a[0], b[0])
    reduced, one_kept = pds.pop(rank_one, 1)
    assert one_kept.sum().item() == 1
    reduced[0].square().sum().backward()
    assert all(p.grad is None or torch.isfinite(p.grad).all() for p in pds.parameters())
    pds.zero_grad(set_to_none=True)

    a, b = histories()
    thresholds = {"M1": [-1., 0.], "M3": [-1., 0.]}
    results = predict_pair(flat, pds, thresholds, a, b)
    for side, expected in enumerate([("Oak", "U7", "Amount"), ("Palm", "U4", "Ref")]):
        r = results[side]
        assert set(r) == {"M0", "M1", "M2", "M3-Zero", "M3", "M3-Swap"}
        expected_result = dict(type="Posting", owner=expected[0], unit=expected[1], column=expected[2],
                               subtotal_status="BALANCED")
        assert r["M2"]["decision"] == expected_result
        assert r["M2"]["subtotal_diagnostic"]["subtotal_status"] == "BALANCED"
        assert r["M3-Zero"]["decision"] == {"type": "ABSTAIN", "reason": "zero_state_tie"}
        assert r["M0"]["decision"]["type"] == "ABSTAIN"
        assert r["M3"]["candidate_receipt"]["pair_equal"]
        assert all("window1_audit" in arm for arm in r.values())
        assert r["M1"]["window1_audit"]["observed"] == r["M3"]["window1_audit"]["observed"]
        assert r["M3-Zero"]["window1_audit"]["decoded_binding"] is None
        assert r["M0"]["window1_audit"]["source"] == "suffix_only"
        assert r["M3-Swap"]["window1_audit"]["decoded_binding"] == r["M3"]["window1_audit"]["decoded_binding"]
        own = r["M3"]["final_entry"]
        swapped = r["M3-Swap"]["final_entry"]
        donor = results[1 - side]["M3"]["final_entry"]
        assert swapped["nonmatrix_sha256"] == own["nonmatrix_sha256"]
        assert swapped["matrix_sha256"] == donor["matrix_sha256"] != own["matrix_sha256"]
        # Different complete donor tensors must affect measured scores, even for untrained probes.
        assert r["M3"]["target_scores"] != r["M3-Swap"]["target_scores"]

    a2, b2 = a.copy(), b.copy()
    a2[2] = b2[2] = construct(["Schedule detail"])
    ambiguous = predict_pair(flat, pds, thresholds, a2, b2)
    for output in ambiguous:
        for r in output.values():
            assert r["decision"]["type"] == "ABSTAIN"
        assert output["M2"]["decision"]["reason"] == "shadow_hold"
    new_target = construct([["MAINT-SUMMARY", "45", "45"]])
    a3, b3 = a[:-1] + [new_target], b[:-1] + [new_target]
    assert predict_pair(flat, pds, thresholds, a3, b3)[0]["M2"]["decision"]["subtotal_status"] == "UNBALANCED"

    # A shared nonconstant training loss exercises every optimizer parameter tensor.
    # No optimizer, checkpoint, released feature, calibration or truth is used here.
    gradients = {}
    for name, model in (("M1", flat), ("M3", pds)):
        state = NeuralState(model.zero())
        for ordinal, w in enumerate(a, 1):
            advance(model, state, w, ordinal)
        loss = sum(scores[0] - scores[-1] for scores in state.attempts[0].scores.values())
        loss.backward()
        gradients[name] = {n: p.grad is not None and bool(torch.isfinite(p.grad).all())
                           and p.grad.abs().max().item() > 0 for n, p in model.named_parameters()}
        assert all(gradients[name].values())
    return {"calibration_semantics": calibration_semantics(), "torch": str(torch.__version__), "cuda_visible": False,
            "fp32_protected_Linf": protected, "summary_Linf": delta, "pop_rank": int(rank.sum()),
            "rank_one_backward_finite": True, "empty_rank": int(flags.sum()), "partial_rank_mask": keep.tolist(),
            "parameter_counts": counts, "nonzero_finite_gradients": gradients,
            "symmetric_matrix_transplant": True, "causal_views": 6,
            "positive_m2_amendment_and_summary": True, "open_child_shadow_hold": True,
            "disjoint_slot_freeze_and_child_wipe": True}


if __name__ == "__main__":
    print(json.dumps(preflight(), indent=2))
