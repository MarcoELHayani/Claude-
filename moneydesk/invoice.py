"""Bill's invoice builder: validates against the fav-invoicing rules, then renders a PDF.

Spec (JSON):
{
  "entity": "FAV Studios" | "Fav Production",
  "number": "FAV-2026-031", "rev": 1,
  "issued": "2026-10-07", "due": "2026-11-06",
  "client": {"name": "...", "email": "...", "address": "..."},
  "po_code": "..." | null,
  "currency": "GBP",
  "lines": [{"description": "...", "kind": "equipment"|"service", "qty": 1, "unit_price": "180.00", "vat_rate": "0"}],
  "stated_total": "2369.29",          # optional cross-check against what was agreed
  "previous_total": "2549.29"         # optional, for the rev covering note
}
"""
from datetime import date
from decimal import Decimal
from xml.sax.saxutils import escape

from .money import dec, money, fmt

ENTITY_KIND = {"FAV Studios": "equipment", "Fav Production": "service"}


class InvoiceError(ValueError):
    pass


def compute(spec: dict) -> dict:
    lines = []
    subtotal = vat_total = Decimal(0)
    for line in spec["lines"]:
        net = money(dec(line["qty"]) * dec(line["unit_price"]))
        vat = money(net * dec(line.get("vat_rate") or 0) / 100)
        lines.append({**line, "net": net, "vat": vat})
        subtotal += net
        vat_total += vat
    return {"lines": lines, "subtotal": money(subtotal), "vat": money(vat_total),
            "total": money(subtotal + vat_total)}


def validate(spec: dict, cfg: dict) -> dict:
    """Returns computed totals or raises InvoiceError listing every problem at once."""
    problems = []
    entity = spec.get("entity")
    if entity not in ENTITY_KIND:
        problems.append(f"entity must be one of {list(ENTITY_KIND)}")
    else:
        wrong = [l["description"] for l in spec["lines"] if l.get("kind") != ENTITY_KIND[entity]]
        if wrong:
            problems.append(f"two-entity rule: {entity} invoices only carry {ENTITY_KIND[entity]} lines; "
                            f"move these to a separate invoice: {wrong}")
        if entity == "FAV Studios" and any(dec(l.get("vat_rate") or 0) != 0 for l in spec["lines"]):
            problems.append("FAV Studios equipment hire is invoiced with no VAT")
        details = cfg["entities"].get(entity, {})
        for field in ("address", "bank"):
            if not details.get(field):
                problems.append(f"config entities.{entity}.{field} is empty; fill it once in config/money-desk.json")

    client_email = (spec.get("client") or {}).get("email", "")
    domain = client_email.rsplit("@", 1)[-1].lower()
    if domain in cfg["bill"]["po_required_clients"] and not spec.get("po_code"):
        problems.append(f"{domain} issues one PO per invoice; do not invoice until the PO code arrives")

    if not spec.get("lines"):
        problems.append("no lines")
    if int(spec.get("rev") or 0) < 1:
        problems.append("rev must start at 1 and go up on every correction")

    if problems:
        raise InvoiceError("; ".join(problems))

    totals = compute(spec)
    if spec.get("stated_total") is not None and money(spec["stated_total"]) != totals["total"]:
        raise InvoiceError(f"lines add up to {totals['total']} but stated total is {money(spec['stated_total'])}")
    return totals


def covering_note_numbers(spec: dict, totals: dict) -> str:
    """The rev rule: say the old and new total out loud."""
    cur = spec["currency"]
    if spec.get("previous_total") is None:
        return f"Total {fmt(totals['total'], cur)}"
    return f"rev{spec['rev']}: total moves from {fmt(spec['previous_total'], cur)} to {fmt(totals['total'], cur)}"


def render_pdf(spec: dict, totals: dict, cfg: dict, out_path: str) -> str:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    # Every piece of text from a spec or config is escaped: reportlab Paragraphs parse markup,
    # so a client name like '<link href=...>' must render as text, not as a live link.
    seller = {k: escape(str(v)) for k, v in cfg["entities"][spec["entity"]].items()}
    spec = {**spec, "number": escape(str(spec["number"])), "po_code": escape(str(spec["po_code"])) if spec.get("po_code") else None,
            "issued": escape(str(spec.get("issued", ""))), "due": escape(str(spec.get("due", "")))}
    cur = spec["currency"]
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(out_path, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=18 * mm, bottomMargin=18 * mm,
                            title=f"Invoice {spec['number']} rev{spec['rev']}")
    head = [
        Paragraph(f"<b>{seller['legal_name']}</b><br/>{seller['address']}", styles["Normal"]),
        Paragraph(f"<b>INVOICE {spec['number']}</b> (rev{spec['rev']})<br/>Issued {spec['issued']}<br/>"
                  f"Due {spec['due']}" + (f"<br/>PO {spec['po_code']}" if spec.get("po_code") else ""),
                  styles["Normal"]),
    ]
    client = {k: escape(str(v)) for k, v in spec["client"].items()}
    rows = [["Description", "Qty", "Unit", "Net", "VAT"]]
    for l in totals["lines"]:
        rows.append([Paragraph(escape(str(l["description"])), styles["Normal"]), str(l["qty"]),
                     fmt(l["unit_price"], cur), fmt(l["net"], cur), fmt(l["vat"], cur)])
    rows += [["", "", "", "Subtotal", fmt(totals["subtotal"], cur)],
             ["", "", "", "VAT", fmt(totals["vat"], cur)],
             ["", "", "", "TOTAL", fmt(totals["total"], cur)]]
    table = Table(rows, colWidths=[85 * mm, 15 * mm, 25 * mm, 25 * mm, 24 * mm])
    table.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, colors.black),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("LINEABOVE", (3, -3), (-1, -3), 0.5, colors.grey),
        ("FONTNAME", (3, -1), (-1, -1), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story = [Table([head], colWidths=[100 * mm, 74 * mm]), Spacer(1, 10 * mm),
             Paragraph(f"<b>Bill to</b><br/>{client['name']}<br/>{client.get('address', '')}", styles["Normal"]),
             Spacer(1, 8 * mm), table, Spacer(1, 10 * mm),
             Paragraph(f"<b>Payment</b><br/>{seller['bank']}", styles["Normal"])]
    if spec["entity"] == "FAV Studios":
        story += [Spacer(1, 4 * mm), Paragraph("Equipment hire. No VAT charged.", styles["Italic"])]
    doc.build(story)
    return out_path


def default_due(issued: str, cfg: dict) -> str:
    from datetime import timedelta
    return (date.fromisoformat(issued) + timedelta(days=cfg["bill"]["default_payment_terms_days"])).isoformat()
