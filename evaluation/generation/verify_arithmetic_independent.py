"""Independent stdlib arithmetic and referential-integrity author checker (Gate A).

IMPORTANT GOVERNANCE DISCLOSURE:
This script is authored by eld-rd-carbon as an automated author sanity check. It imports
ZERO helpers from generate_corpus.py or pdf_writer.py and recomputes every monetary value
from displayed printed strings using Python's decimal module. However, per AGENTS.md and
WP-0004-eld-rd-carbon-reconciliation.md, a second script by the same author is NOT
non-author ground-truth verification; admission requires independent verification by
eld-rd-reviewer (uninvolved Opus) in WP-0004 / 005.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
from decimal import Decimal, ROUND_HALF_UP

CENT = Decimal("0.01")


def parse_printed_usd(text: str) -> Decimal:
    m = re.fullmatch(r"(-?)\$([0-9]{1,3}(?:,[0-9]{3})*\.[0-9]{2})", text.strip())
    if not m:
        raise ValueError(f"Malformed printed USD string: {text!r}")
    sign = -1 if m.group(1) == "-" else 1
    digits = m.group(2).replace(",", "")
    return Decimal(digits) * sign


def parse_printed_pct(text: str) -> Decimal:
    m = re.fullmatch(r"([0-9]+\.[0-9]{2})%", text.strip())
    if not m:
        raise ValueError(f"Malformed printed percentage string: {text!r}")
    return (Decimal(m.group(1)) / Decimal("100")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def parse_printed_qty(text: str) -> Decimal:
    parts = text.strip().split(" ")
    if len(parts) != 2 or not re.fullmatch(r"[0-9]+\.[0-9]{2}", parts[0]):
        raise ValueError(f"Malformed printed quantity+unit string: {text!r}")
    return Decimal(parts[0])


def rhu_cents(val: Decimal) -> Decimal:
    return val.quantize(CENT, rounding=ROUND_HALF_UP)


def check_expected_file(exp_path: pathlib.Path) -> dict[str, object]:
    payload = json.loads(exp_path.read_text(encoding="utf-8"))
    fid = payload["fixture_id"]
    doc_kind = payload["doc_kind"]

    # Check cross-page serial referential integrity on work_order_packet (F08)
    for link in payload.get("cross_page_links", []):
        if link["link_type"] == "cross_table_serial_referential_integrity":
            tables_by_id = {t["table_id"]: t for t in payload["expected_tables"]}
            dep_rows = tables_by_id[link["source_table"]]["rows"]
            ret_rows = tables_by_id[link["target_table"]]["rows"]
            dep_serials = [r["cells"]["serial_no"]["printed_text"] for r in dep_rows]
            ret_serials = [r["cells"]["serial_no"]["printed_text"] for r in ret_rows]
            if dep_serials != link["serial_numbers"] or ret_serials != link["serial_numbers"]:
                raise AssertionError(f"{fid}: cross-page serial mismatch dep={dep_serials} ret={ret_serials}")

    if doc_kind != "invoice":
        return {"fixture_id": fid, "doc_kind": doc_kind, "invoice_checked": False}

    tables = payload["expected_tables"]
    if len(tables) != 1 or tables[0]["table_id"] != "line_items":
        raise AssertionError(f"{fid}: expected single line_items table")

    rows = tables[0]["rows"]
    sum_net = Decimal("0.00")
    sum_taxable_net = Decimal("0.00")

    for r in rows:
        cells = r["cells"]
        qty = parse_printed_qty(cells["qty_unit"]["printed_text"])
        uprice = parse_printed_usd(cells["unit_price"]["printed_text"])
        drate = parse_printed_pct(cells["discount_rate"]["printed_text"])
        printed_disc = parse_printed_usd(cells["line_discount"]["printed_text"])
        printed_net = parse_printed_usd(cells["net_line"]["printed_text"])
        tax_flag = cells["tax_flag"]["printed_text"]

        gross = rhu_cents(qty * uprice)
        recomp_disc = rhu_cents(gross * drate)
        recomp_net = gross - recomp_disc

        if recomp_disc != printed_disc:
            raise AssertionError(f"{fid} {r['row_id']}: discount {recomp_disc} != printed {printed_disc}")
        if recomp_net != printed_net:
            raise AssertionError(f"{fid} {r['row_id']}: net {recomp_net} != printed {printed_net}")
        if f"{recomp_net:.2f}" != cells["net_line"]["normalized_value"]:
            raise AssertionError(f"{fid} {r['row_id']}: normalized net mismatch")

        sum_net += printed_net
        if tax_flag == "T":
            sum_taxable_net += printed_net
        elif tax_flag != "N":
            raise AssertionError(f"{fid} {r['row_id']}: unexpected tax_flag {tax_flag!r}")

    if sum_taxable_net < Decimal("0.00"):
        raise AssertionError(f"{fid}: negative taxable base {sum_taxable_net}")

    acct_summ = payload["invoice_accounting"]["summary"]
    tax_rate = parse_printed_pct(acct_summ["tax_rate"]["printed_text"])
    recomp_tax = rhu_cents(sum_taxable_net * tax_rate)

    fee_sum = sum(
        (parse_printed_usd(f["amount_printed"]) for f in payload["invoice_accounting"]["fees"]),
        Decimal("0.00"),
    )
    recomp_inv_total = sum_net + recomp_tax + fee_sum
    prev_bal = parse_printed_usd(acct_summ["previous_balance"]["printed_text"])
    payments = parse_printed_usd(acct_summ["payments_credits_applied"]["printed_text"])
    recomp_due = recomp_inv_total + prev_bal - payments

    checks = {
        "subtotal": (sum_net, parse_printed_usd(acct_summ["subtotal"]["printed_text"])),
        "taxable_subtotal": (sum_taxable_net, parse_printed_usd(acct_summ["taxable_subtotal"]["printed_text"])),
        "tax_amount": (recomp_tax, parse_printed_usd(acct_summ["tax_amount"]["printed_text"])),
        "non_taxable_fees": (fee_sum, parse_printed_usd(acct_summ["non_taxable_fees"]["printed_text"])),
        "invoice_total": (recomp_inv_total, parse_printed_usd(acct_summ["invoice_total"]["printed_text"])),
        "amount_due": (recomp_due, parse_printed_usd(acct_summ["amount_due"]["printed_text"])),
    }
    for k, (got, exp_v) in checks.items():
        if got != exp_v or f"{got:.2f}" != acct_summ[k]["normalized_value"]:
            raise AssertionError(f"{fid}: {k} mismatch got={got} expected={exp_v}")

    # Also confirm final-page expected_fields carry exact matching currency strings
    fields_by_id = {f["field_id"]: f for f in payload["expected_fields"]}
    for k in ("subtotal", "taxable_subtotal", "tax_amount", "invoice_total", "previous_balance", "payments_credits_applied", "amount_due"):
        if parse_printed_usd(fields_by_id[k]["printed_text"]) != checks.get(k, (parse_printed_usd(acct_summ[k]["printed_text"]),))[0]:
            raise AssertionError(f"{fid}: expected_fields[{k}] out of sync with accounting summary")

    return {
        "fixture_id": fid,
        "doc_kind": doc_kind,
        "invoice_checked": True,
        "row_count": len(rows),
        "subtotal": f"{sum_net:.2f}",
        "taxable_subtotal": f"{sum_taxable_net:.2f}",
        "tax_amount": f"{recomp_tax:.2f}",
        "non_taxable_fees": f"{fee_sum:.2f}",
        "invoice_total": f"{recomp_inv_total:.2f}",
        "amount_due": f"{recomp_due:.2f}",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Independent stdlib Decimal author arithmetic verifier.")
    parser.add_argument(
        "--expected-dir",
        type=pathlib.Path,
        default=pathlib.Path(__file__).resolve().parent.parent / "synthetic" / "expected",
    )
    args = parser.parse_args()
    exp_files = sorted(args.expected_dir.glob("*_expected.json"))
    if len(exp_files) != 26:
        raise SystemExit(f"Expected 26 expected JSON files in {args.expected_dir}, found {len(exp_files)}")

    inv_checked = 0
    for ef in exp_files:
        res = check_expected_file(ef)
        if res["invoice_checked"]:
            inv_checked += 1

    print(
        f"AUTHOR_ARITHMETIC_CHECK_PASS: verified_expected_files={len(exp_files)} "
        f"invoice_fixtures_recomputed={inv_checked} (Note: author check only; Opus /005 review required for admission)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
