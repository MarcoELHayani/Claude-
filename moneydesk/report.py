"""Friday report: cancelled, paid, filed. Numbers come from here, words come from the bot."""
from .money import fmt, fmt_totals, monthly_cost, money, totals_by_currency


def build(data: dict) -> dict:
    # A failed/missing source read is unknown, never a verified empty ledger.
    required = ('cancelled', 'paid', 'filed', 'outstanding', 'subscriptions_active')
    missing = [key for key in required if not isinstance(data.get(key), list)]
    if missing:
        raise ValueError('report source coverage missing: ' + ', '.join(missing))
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

    lines.append(f"Confirmed cancellations: {len(cancelled)}; estimated monthly equivalent {fmt_totals(saved)} (not cash saved)")
    lines += [f"  - {r['service']}: {fmt(r['amount'], r['currency'])} {r.get('cycle', 'Monthly').lower()}"
              for r in cancelled]
    lines.append(f"  Subscriptions still running: {len(active)}, {fmt_totals(burn)} a month")

    lines += ["", f"Payments recorded: {len(data.get('paid', []))}: {fmt_totals(paid)} (actor and receipt evidence in source records)"]
    lines += [f"  - {r['client']} {r['invoice']}: {fmt(r['amount'], r['currency'])}" for r in data.get("paid", [])]
    lines.append(f"  Still owed: {fmt_totals(outstanding)} across {len(data.get('outstanding', []))} invoices")
    lines += [f"  - chased {c['invoice']} (stage {c['stage']}, {c['days_overdue']} days late)"
              for c in data.get("chasers", [])]

    lines += ["", f"Receipt ledger entries: {len(data.get('filed', []))}: {fmt_totals(filed)} (not proof of Drive archiving)"]

    needs = data.get("needs_marco", [])
    if needs:
        lines += ["", f"Needs you ({len(needs)}):"]
        lines += [f"  - {n}" for n in needs[:2]]
        if len(needs) > 2:
            lines.append(f"  {len(needs) - 2} further items remain in the existing register.")

    text = "\n".join(lines)
    return {"text": text, "saved_monthly": {k: str(v) for k, v in saved.items()},
            "paid": {k: str(v) for k, v in paid.items()},
            "filed": {k: str(v) for k, v in filed.items()},
            "outstanding": {k: str(v) for k, v in outstanding.items()},
            "burn_monthly": {k: str(v) for k, v in burn.items()}}
