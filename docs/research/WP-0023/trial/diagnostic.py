"""Bounded replays of the first differing decision per slot in each observed permutation."""
import hashlib
import json
import time
import traceback

from gates import PAGE, check_probe, decisions, deltas


def history(prefix):
    packed = json.dumps(prefix, separators=(",", ":")).encode()
    markers = prefix.count(PAGE)
    return dict(length=len(prefix), sha256=hashlib.sha256(packed).hexdigest(), page_markers=markers,
                tokens_since_last_page=(prefix[::-1].index(PAGE) if markers else len(prefix)))


def target_probe(trial, order, slot, prefixes, candidates, name, fp32=False):
    spec = dict(lane=slot, prefixes=prefixes, candidates=candidates, fp32=fp32)
    result = trial.measured(name, lambda: trial.wrapped(order, probe=spec))
    return result["probe"]


def guard_summary(prefix, eos, candidates):
    # Independent token-history reconstruction of pinned ngram=35, window=1024 and three-page guard.
    h = history(prefix)
    tail = prefix[-34:]
    banned = {prefix[i+34] for i in range(max(0, len(prefix)-1024), len(prefix)-34) if prefix[i:i+34] == tail}
    mc = h["page_markers"]
    force = eos if mc > 3 else (PAGE if mc < 3 else eos) if h["tokens_since_last_page"] >= 20000 else None
    restricted = {str(i): dict(ngram_banned=i in banned,
                              page_banned=(i != force if force is not None else i == eos and mc < 3))
                  for i in candidates}
    return dict(**h, ngram_banned_count=len(banned), page_force=force, candidate_restrictions=restricted)


def diagnose(trial, batches, checks):
    from run import write
    rows, representatives = [], []
    cache = {}
    for order, original in batches.items():
        for slot, key in enumerate(order):
            check = checks["-".join(order)][key]
            if check["passed"]:
                continue
            first = check["first"]
            base = "diag-" + "-".join(order) + "-" + key
            if first is None or first["native_id"] is None or first["batch_id"] is None:
                limitation = {"name": base, "first": first, "status": "terminal-or-metadata-without-two-competitors"}
                rows.append(limitation)
                write(trial.folder, base + "-compare", limitation)
                continue
            step = first["step_zero_based"]
            candidates = [first["native_id"], first["batch_id"]]
            prefixes = [decisions(row)[:step] for row in original["lanes"]]
            prefix = prefixes[slot]
            if prefix != decisions(trial.control[key])[:step] or len(prefix) != step:
                raise ValueError("Initial mismatch did not produce a shared input history")
            memo = key, step, tuple(candidates)
            if memo not in cache:
                stock_name = base + "-stock"
                stock = trial.measured(stock_name, lambda: trial.single(key, prefix=prefix, candidates=candidates))
                one_name = base + "-wrapper-b1"
                one = target_probe(trial, (key,), 0, [prefix], candidates, one_name)
                cache[memo] = stock, stock_name, one, one_name
            stock, stock_name, one, one_name = cache[memo]
            two_name = base + "-wrapper-b2"
            two = target_probe(trial, order, slot, prefixes, candidates, two_name)
            # Keep raw scores even if a re-run picks a different winner, and disclose that qualification.
            replay = {}
            for label, probe, winner in (("stock", stock, candidates[0]), ("wrapper_b1", one, candidates[0]),
                                         ("wrapper_b2", two, candidates[1])):
                try:
                    check_probe(probe, winner)
                except ValueError as exc:
                    replay[label] = str(exc)
                else:
                    replay[label] = "reproduced"
            other_order = order[::-1]
            other_slot = other_order.index(key)
            other = batches[other_order]["lanes"][other_slot]
            original_decisions = decisions(original["lanes"][slot])
            swapped_decisions = decisions(other)
            swap_first = next((i for i, (a, b) in enumerate(zip(original_decisions, swapped_decisions)) if a != b), None)
            if swap_first is None and len(original_decisions) != len(swapped_decisions):
                swap_first = min(len(original_decisions), len(swapped_decisions))
            other_history = prefixes[1-slot]
            row = dict(name=base, window=key, slot=slot, order=order, first=first, same_window_swapped_slot=other_slot,
                       swapped_first_decision_difference=swap_first,
                       replay=replay, source_files=dict(stock=stock_name, wrapper_b1=one_name, wrapper_b2=two_name),
                       target_history=guard_summary(prefix, trial.control[key]["eos_id"], candidates),
                       peer_history=history(other_history), peer_already_stopped=len(other_history) < step or
                       (bool(other_history) and other_history[-1] == trial.control[key]["eos_id"]),
                       stock_to_b2=deltas(stock, two, candidates), wrapper_b1_to_b2=deltas(one, two, candidates))
            write(trial.folder, base + "-compare", row)
            rows.append(row)
            representatives.append((base, order, slot, key, prefixes, candidates))

    fp = {"status": "no-two-token-decision"}
    if representatives:
        base, order, slot, key, prefixes, candidates = representatives[0]
        fp = {"status": "attempting", "representative": base, "scope": "first comparable mismatch, both batch sizes"}
        try:
            one = target_probe(trial, (key,), 0, [prefixes[slot]], candidates, base + "-fp32-b1", fp32=True)
            two = target_probe(trial, order, slot, prefixes, candidates, base + "-fp32-b2", fp32=True)
            fp.update(status="completed", b1_selected=one["processed"]["argmax"],
                      b2_selected=two["processed"]["argmax"], cross_shape=deltas(one, two, candidates))
        except (RuntimeError, NotImplementedError, MemoryError) as exc:
            # Unsupported precision or insufficient device memory is evidence, never a permission to time.
            if not any(word in str(exc).lower() for word in ("dtype", "type", "out of memory", "not implemented",
                                                              "float", "capacity", "unsupported", "memory")):
                raise
            fp.update(status="could-not-complete", error_type=type(exc).__name__, error=str(exc),
                      trace=traceback.format_exc(), utc_ns=time.time_ns())
    write(trial.folder, "diagnostic-fp32", fp)
    return {"mismatches": rows, "full_precision": fp}
