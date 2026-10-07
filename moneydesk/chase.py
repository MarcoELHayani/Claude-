"""Bill's chase rules, as code so the decision never depends on a model's mood.

Input: invoice rows (from the Notion Invoices database) as dicts.
Output: one decision per invoice that needs something today.

Rules:
- Only Sent/Overdue invoices with a due date and a client email are chased.
- Stages follow days overdue: 7 -> 1 (polite nudge), 14 -> 2 (firmer), 21 -> 3 (flag Marco to call).
- Stages escalate one step at a time, even if the invoice is already very late.
- Never two chasers less than `min_days_between_chasers` apart.
- If the client replied after our last touch, hold and hand it to Marco: a human answer is needed.
- Stage 3 never emails the client; it flags Marco for a call.
"""
from datetime import date

CHASEABLE = {"Sent", "Overdue"}


def _d(value):
    if not value:
        return None
    return value if isinstance(value, date) else date.fromisoformat(str(value)[:10])


def decide(invoice: dict, today: date, cfg: dict) -> dict | None:
    if invoice.get("status") not in CHASEABLE:
        return None
    due = _d(invoice.get("due"))
    if due is None:
        return {"invoice": invoice["invoice"], "action": "fix", "reason": "no due date"}
    if not invoice.get("client_email"):
        return {"invoice": invoice["invoice"], "action": "fix", "reason": "no client email"}

    overdue = (today - due).days
    thresholds = cfg["chase_days_overdue"]
    target = sum(1 for t in thresholds if overdue >= t)
    stage = int(invoice.get("chase_stage") or 0)
    if target <= stage:
        return None

    last_chased = _d(invoice.get("last_chased"))
    last_touch = last_chased or _d(invoice.get("issued")) or due
    reply = _d(invoice.get("last_client_reply"))
    if reply and reply >= last_touch:
        return {"invoice": invoice["invoice"], "action": "hold", "stage": stage,
                "days_overdue": overdue, "reason": f"client replied on {reply}, Marco to read"}

    if last_chased and (today - last_chased).days < cfg["min_days_between_chasers"]:
        return None

    next_stage = stage + 1
    if next_stage >= 3:
        action = "flag_call"
    elif cfg.get("autosend_chasers"):
        action = "send"
    else:
        action = "draft"
    return {"invoice": invoice["invoice"], "action": action, "stage": next_stage,
            "days_overdue": overdue, "reason": f"{overdue} days overdue"}


def plan(invoices: list, today: date, cfg: dict) -> list:
    """Decisions for today, capped so a bad data import can't fire off a wall of emails."""
    decisions = [d for d in (decide(i, today, cfg) for i in invoices) if d]
    sends = 0
    for d in decisions:
        if d["action"] == "send":
            sends += 1
            if sends > cfg["max_autosends_per_run"]:
                d["action"] = "draft"
                d["reason"] += " (over the per-run send cap, drafted instead)"
    return decisions
