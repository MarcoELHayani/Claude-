"""Security guard. Two jobs:

1. check_outgoing(): every email a bot SENDS goes through this first. If it returns problems, don't send.
   This is the last line of defence against a poisoned email talking a bot into mailing someone else,
   leaking bank details, or slipping in a link.
2. scan_incoming(): flags emails that look like fraud or prompt injection, so bots stop and hand
   them to Marco instead of acting on them.
"""
import re

URL = re.compile(r"https?://|www\.", re.I)
BANK = re.compile(r"\b(iban|swift|bic|sort ?code|account (number|no)|routing|card number|cvv|password|"
                  r"[A-Z]{2}\d{2}[A-Z0-9]{11,30})\b", re.I)
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

SUSPICIOUS = {
    "bank details change": re.compile(r"(new|updated|changed?)\s+(bank|account|payment)\s+(details|information|account)"
                                      r"|nuov[ie]\s+coordinate\s+bancarie|cambio\s+iban", re.I),
    "instructions aimed at the bot": re.compile(r"ignore (all |any )?(previous|prior|above) instructions|"
                                                r"you are (now )?(an? )?(ai|assistant|bot)\b|system prompt|"
                                                r"(assistant|claude|ai)[,:]? (please )?(forward|send|reply|transfer|delete)", re.I),
    "credential or code request": re.compile(r"(verify|confirm|send|share)\s+(your\s+)?(password|login|2fa|otp|"
                                             r"verification code|card details)", re.I),
    "urgent payment pressure": re.compile(r"(urgent|immediately|within 24 hours|final notice).{0,60}"
                                          r"(pay|payment|transfer|wire)", re.I | re.S),
    "gift cards or crypto": re.compile(r"gift ?cards?|bitcoin|usdt|crypto wallet", re.I),
}


def scan_incoming(text: str) -> list[str]:
    return [name for name, rx in SUSPICIOUS.items() if rx.search(text or "")]


def _norm(addr: str) -> str:
    return (addr or "").strip().lower()


def check_outgoing(kind: str, msg: dict, cfg: dict, invoice: dict | None = None) -> list[str]:
    """msg: {to: [..], cc: [..], bcc: [..], body: str, thread_participants: [..]}. Returns problems ([] = safe)."""
    to = [_norm(a) for a in msg.get("to") or []]
    extra = [a for a in (msg.get("cc") or []) + (msg.get("bcc") or []) if a]
    body = msg.get("body") or ""
    owner = _norm(cfg["owner"]["email"])
    problems = []

    if not to or not all(EMAIL.match(a) for a in to):
        problems.append("missing or malformed recipient")
    if extra:
        problems.append("bots never add cc/bcc")

    if kind == "report":
        if to != [owner]:
            problems.append("reports go to the owner only")
    elif kind == "chaser":
        if invoice is None:
            return problems + ["chaser without its invoice row"]
        client = _norm(invoice.get("client_email"))
        participants = {_norm(a) for a in msg.get("thread_participants") or []}
        if to != [client]:
            problems.append("chaser must go to exactly the invoice's client email")
        if client not in participants:
            problems.append("client email is not on the invoice thread")
        if invoice.get("invoice") and invoice["invoice"] not in body:
            problems.append("chaser must name the invoice number")
        if URL.search(body):
            problems.append("chasers carry no links")
        if BANK.search(body):
            problems.append("chasers never contain bank, card or login details")
        if len(body.split()) > 120:
            problems.append("chaser too long (max 120 words)")
    else:
        problems.append(f"bots may only send 'report' or 'chaser', not {kind!r}; everything else is a draft")
    return problems
