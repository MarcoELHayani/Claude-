"""Config loading. Real IDs live in config/money-desk.json, which is gitignored and never committed.

Scheduled runs rebuild it from the "Money Desk config" block on Marco's private Notion page.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REAL = ROOT / "config" / "money-desk.json"
EXAMPLE = ROOT / "config" / "money-desk.example.json"


class ConfigError(RuntimeError):
    pass


def load(require_real: bool = True) -> dict:
    if REAL.exists():
        cfg = json.loads(REAL.read_text())
    elif require_real:
        raise ConfigError(f"{REAL} missing: copy the 'Money Desk config' JSON from Notion into it "
                          f"(template: {EXAMPLE.name})")
    else:
        cfg = json.loads(EXAMPLE.read_text())
    if require_real and "<" in json.dumps({k: cfg[k] for k in ("owner", "notion", "gmail", "drive")}):
        raise ConfigError("config still has <placeholders>; fill it from the Notion config block")
    return cfg
