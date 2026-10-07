"""CLI the bots call so every number and every chase decision is computed, not guessed.

  python -m moneydesk chase    invoices.json [--today 2026-10-07]   -> JSON decisions
  python -m moneydesk invoice  spec.json out.pdf                    -> validates, renders, prints totals
  python -m moneydesk monthly  subs.json                            -> adds monthly cost, totals per currency
  python -m moneydesk report   week.json                            -> Friday report text + totals
  python -m moneydesk guard    outgoing.json                        -> {"safe": bool, "problems": [...]}; exit 2 if unsafe
  python -m moneydesk scan     email.txt                            -> fraud / prompt-injection flags for an incoming email
"""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

from . import chase, guard, invoice, report
from .config import load as load_config
from .money import monthly_cost, totals_by_currency


def load(path):
    return json.loads(Path(path).read_text())


def main(argv=None):
    p = argparse.ArgumentParser(prog="moneydesk")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("chase"); c.add_argument("file"); c.add_argument("--today")
    i = sub.add_parser("invoice"); i.add_argument("file"); i.add_argument("out")
    m = sub.add_parser("monthly"); m.add_argument("file")
    r = sub.add_parser("report"); r.add_argument("file")
    g = sub.add_parser("guard"); g.add_argument("file")
    s = sub.add_parser("scan"); s.add_argument("file")
    args = p.parse_args(argv)
    cfg = load_config(require_real=args.cmd in ("guard", "invoice"))

    if args.cmd == "chase":
        today = date.fromisoformat(args.today) if args.today else date.today()
        out = chase.plan(load(args.file), today, cfg["bill"])
    elif args.cmd == "invoice":
        spec = load(args.file)
        try:
            totals = invoice.validate(spec, cfg)
        except invoice.InvoiceError as e:
            print(json.dumps({"ok": False, "error": str(e)}, indent=2))
            return 1
        invoice.render_pdf(spec, totals, cfg, args.out)
        out = {"ok": True, "pdf": args.out, "subtotal": str(totals["subtotal"]), "vat": str(totals["vat"]),
               "total": str(totals["total"]), "note": invoice.covering_note_numbers(spec, totals)}
    elif args.cmd == "monthly":
        subs = load(args.file)
        for s in subs:
            mc = monthly_cost(s["amount"], s.get("cycle", "Monthly"))
            s["monthly"] = None if mc is None else str(mc)
        fixed = [s for s in subs if s["monthly"] is not None]
        out = {"subscriptions": subs,
               "monthly_total": {k: str(v) for k, v in totals_by_currency(fixed, amount_key="monthly").items()}}
    elif args.cmd == "guard":
        req = load(args.file)
        problems = guard.check_outgoing(req["kind"], req["message"], cfg, req.get("invoice"))
        problems += [f"incoming thread flagged: {f}" for f in guard.scan_incoming(req.get("thread_text", ""))]
        print(json.dumps({"safe": not problems, "problems": problems}, indent=2))
        return 0 if not problems else 2
    elif args.cmd == "scan":
        flags = guard.scan_incoming(Path(args.file).read_text())
        out = {"suspicious": bool(flags), "flags": flags}
    else:
        out = report.build(load(args.file))

    print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
