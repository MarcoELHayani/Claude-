"""Friday report: cancelled, paid, filed. Numbers come from here, words come from the bot."""
from .money import fmt, fmt_totals, monthly_cost, money, totals_by_currency


def build(data: dict) -> dict:
    cancelled = data.get("cancelled", [])
    for row in cancelled:
        row["monthly"] = monthly_cost(row["amount"], row.get("cycle", "Monthly"))
    saved = totals_by_currency([r for r in cancelled if r["monthly"] is not None], amount_key="monthly")
    paid = totals_by_currency(data.get("paid", []))
    filed = totals_by_currency(data.get("filed", []))
    outstanding = totals_by_currency(data.get("outstanding", []))
    active = data.get("subscriptions_active", [])
    for row in active:
        row["monthly"] = monthly_cost(row["amount"], row.get("cycle", "Monthly"))
    burn = totals_by_currency([r for r in active if r["monthly"] is not None], amount_key="monthly")

    lines = [f"Money Desk, week of {data['week_start']} to {data['week_end']}", ""]

    lines.append(f"Axel cancelled {len(cancelled)}: saves {fmt_totals(saved)} a month")
    lines += [f"  - {r['service']}: {fmt(r['amount'], r['currency'])} {r.get('cycle', 'Monthly').lower()}"
              for r in cancelled]
    lines.append(f"  Subscriptions still running: {len(active)}, {fmt_totals(burn)} a month")

    lines += ["", f"Bill collected {len(data.get('paid', []))}: {fmt_totals(paid)}"]
    lines += [f"  - {r['client']} {r['invoice']}: {fmt(r['amount'], r['currency'])}" for r in data.get("paid", [])]
    lines.append(f"  Still owed: {fmt_totals(outstanding)} across {len(data.get('outstanding', []))} invoices")
    lines += [f"  - chased {c['invoice']} (stage {c['stage']}, {c['days_overdue']} days late)"
              for c in data.get("chasers", [])]

    lines += ["", f"Bob filed {len(data.get('filed', []))} receipts: {fmt_totals(filed)}"]

    needs = data.get("needs_marco", [])
    if needs:
        lines += ["", f"Needs you ({len(needs)}):"]
        lines += [f"  - {n}" for n in needs]

    text = "\n".join(lines)
    return {"text": text, "saved_monthly": {k: str(v) for k, v in saved.items()},
            "paid": {k: str(v) for k, v in paid.items()},
            "filed": {k: str(v) for k, v in filed.items()},
            "outstanding": {k: str(v) for k, v in outstanding.items()},
            "burn_monthly": {k: str(v) for k, v in burn.items()}}
